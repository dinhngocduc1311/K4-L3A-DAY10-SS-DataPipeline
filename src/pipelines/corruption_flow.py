from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import ensure_parent, now_utc, read_json, write_csv
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Measure corruption impact, rebuild from raw truth, and compare all states."""
    settings = load_settings()
    required = (
        settings.paths.raw_records_json,
        settings.paths.clean_json,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_quality_report,
        settings.paths.freshness_report,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Run script/run_phase1.py first; missing: {', '.join(missing)}")

    baseline_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(settings.paths.baseline_quality_report)
    baseline_freshness = read_json(settings.paths.freshness_report)

    corrupted = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted, settings.paths.corrupted_clean_csv)
    ensure_parent(settings.paths.corrupted_clean_json)
    corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=True)
    corrupted_quality = run_data_quality_checks(corrupted, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted,
        settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )
    corrupted_index = LocalEmbeddingIndex.build(corrupted, settings, settings.paths.corrupted_embeddings_json)
    corrupted_metrics = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    ).summary

    repaired = build_clean_dataframe(load_raw_records(settings.paths.raw_records_json), now_utc())
    comparison_columns = ["paper_id", "title", "summary", "published", "text_for_embedding"]
    expected = baseline_df[comparison_columns].sort_values("paper_id").reset_index(drop=True)
    actual = repaired[comparison_columns].sort_values("paper_id").reset_index(drop=True)
    if not actual.equals(expected):
        raise RuntimeError("Repair output does not match the clean baseline source of truth.")
    write_csv(repaired, settings.paths.repaired_clean_csv)
    ensure_parent(settings.paths.repaired_clean_json)
    repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=True)
    repaired_quality = run_data_quality_checks(repaired, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired,
        settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    if not repaired_quality["success"]:
        raise RuntimeError("Repaired data failed the quality gate.")
    repaired_index = LocalEmbeddingIndex.build(repaired, settings, settings.paths.repaired_embeddings_json)
    repaired_metrics = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    ).summary

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        baseline_quality,
        baseline_freshness,
    )
    print("Metric                 Baseline   Corrupted   Repaired")
    print(
        f"Retrieval Hit Rate      {baseline_metrics['retrieval_hit_rate']:.2%}     "
        f"{corrupted_metrics['retrieval_hit_rate']:.2%}       {repaired_metrics['retrieval_hit_rate']:.2%}"
    )
    print(
        f"Mean Token F1           {baseline_metrics['mean_token_f1']:.3f}       "
        f"{corrupted_metrics['mean_token_f1']:.3f}        {repaired_metrics['mean_token_f1']:.3f}"
    )
    print("Repair complete: raw source restored, quality and freshness passed.")
