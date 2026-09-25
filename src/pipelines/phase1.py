from __future__ import annotations

from core.config import load_settings
from core.utils import ensure_parent, now_utc, write_csv
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set, load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the clean baseline pipeline and persist every checkpoint artifact."""
    settings = load_settings()
    records = (
        fetch_source_records(settings)
        if settings.refresh_source or not settings.paths.raw_records_json.exists()
        else load_raw_records(settings.paths.raw_records_json)
    )
    df = build_clean_dataframe(records, now_utc())
    write_csv(df, settings.paths.clean_csv)
    ensure_parent(settings.paths.clean_json)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=True)

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality gate; vector indexing stopped.")

    if settings.refresh_test_set:
        build_test_set(df, settings.paths.eval_testset)
    else:
        load_or_create_test_set(df, settings.paths.eval_testset)
    index = LocalEmbeddingIndex.build(df, settings)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "records": len(df),
        "oldest_published": df["published"].min(),
        "latest_published": df["published"].max(),
        "embedding_model": settings.embedding_model,
        "collection": settings.baseline_collection_name,
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary,
        evaluation.summary,
        quality,
        freshness,
    )
    print(
        f"Baseline complete: {len(df)} papers, "
        f"hit rate={evaluation.summary['retrieval_hit_rate']:.2%}, "
        f"token F1={evaluation.summary['mean_token_f1']:.3f}"
    )
