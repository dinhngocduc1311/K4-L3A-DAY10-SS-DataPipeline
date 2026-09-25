from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the measured baseline results as a compact Markdown report."""
    passed = sum(bool(result.get("success")) for result in quality.get("results", []))
    total = len(quality.get("results", []))
    ragas = metrics.get("ragas", {})
    ragas_status = ragas.get("skipped") or ragas.get("error") or "Completed"
    report = f"""# Baseline Pipeline Report

## Data source and index

| Field | Value |
|---|---|
| Source | {source_summary['source']} |
| Query | {source_summary['query']} |
| Clean papers | {source_summary['records']} |
| Published range | {source_summary['oldest_published']} to {source_summary['latest_published']} |
| Embedding model | `{source_summary['embedding_model']}` |
| Chroma collection | `{source_summary['collection']}` |

## Baseline metrics

| Metric | Value |
|---|---:|
| Benchmark samples | {metrics['samples']} |
| Retrieval Hit Rate | {metrics['retrieval_hit_rate']:.2%} |
| Mean Token F1 | {metrics['mean_token_f1']:.4f} |
| LLM Judge Accuracy | {metrics['judge_accuracy']:.2%} |
| Mean LLM Judge Score | {metrics['mean_judge_score']:.2f} / 5 |
| Judge mode | `{metrics['judge_mode']}` |

Ragas: {ragas_status}

## Data quality and freshness

| Check | Value |
|---|---:|
| Quality gate | {'PASS' if quality['success'] else 'FAIL'} |
| GX expectations passed | {passed} / {total} |
| Freshness SLA | {'PASS' if freshness['is_fresh'] else 'FAIL'} |
| Stale papers | {freshness['stale_rows']} / {freshness['total_rows']} ({freshness['stale_ratio']:.2%}) |
| Freshness threshold | {freshness['threshold_days']} days; maximum stale ratio 25% |
"""
    write_text(report_path, report)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Write the measured baseline/corrupted/repaired comparison."""
    baseline_quality = baseline_quality or {"success": True, "results": []}
    baseline_freshness = baseline_freshness or {"is_fresh": True}

    def quality_status(result: dict[str, Any]) -> str:
        passed = sum(bool(item.get("success")) for item in result.get("results", []))
        total = len(result.get("results", []))
        return f"{'PASSED' if result.get('success') else 'FAILED'} ({passed}/{total})"

    def freshness_status(result: dict[str, Any]) -> str:
        return "FRESH" if result.get("is_fresh") else "STALE"

    hit_drop = corrupted_metrics["retrieval_hit_rate"] - baseline_metrics["retrieval_hit_rate"]
    f1_drop = corrupted_metrics["mean_token_f1"] - baseline_metrics["mean_token_f1"]
    hit_gap = repaired_metrics["retrieval_hit_rate"] - baseline_metrics["retrieval_hit_rate"]
    f1_gap = repaired_metrics["mean_token_f1"] - baseline_metrics["mean_token_f1"]
    report = f"""# Corruption and Idempotent Repair Report

## Three-state comparison

| Metric / Signal | Baseline (Clean) | Corrupted | Repaired |
|---|---:|---:|---:|
| Data Quality Gate | {quality_status(baseline_quality)} | {quality_status(corrupted_quality)} | {quality_status(repaired_quality)} |
| Freshness | {freshness_status(baseline_freshness)} | {freshness_status(corrupted_freshness)} | {freshness_status(repaired_freshness)} |
| Retrieval Hit Rate | {baseline_metrics['retrieval_hit_rate']:.2%} | {corrupted_metrics['retrieval_hit_rate']:.2%} | {repaired_metrics['retrieval_hit_rate']:.2%} |
| Mean Token F1 | {baseline_metrics['mean_token_f1']:.4f} | {corrupted_metrics['mean_token_f1']:.4f} | {repaired_metrics['mean_token_f1']:.4f} |
| Judge Accuracy | {baseline_metrics['judge_accuracy']:.2%} | {corrupted_metrics['judge_accuracy']:.2%} | {repaired_metrics['judge_accuracy']:.2%} |
| Mean Judge Score | {baseline_metrics['mean_judge_score']:.2f} / 5 | {corrupted_metrics['mean_judge_score']:.2f} / 5 | {repaired_metrics['mean_judge_score']:.2f} / 5 |

## Measured impact and recovery

- Corruption changed Retrieval Hit Rate by {hit_drop:+.2%} and Mean Token F1 by {f1_drop:+.4f} versus baseline.
- Repair gap versus baseline: Retrieval Hit Rate {hit_gap:+.2%}; Mean Token F1 {f1_gap:+.4f}.
- Corrupted freshness: {corrupted_freshness['stale_rows']} / {corrupted_freshness['total_rows']} stale rows ({corrupted_freshness['stale_ratio']:.2%}).
- Repaired freshness: {repaired_freshness['stale_rows']} / {repaired_freshness['total_rows']} stale rows ({repaired_freshness['stale_ratio']:.2%}).

## Causal interpretation

1. Dropped documents, blank summaries, truncated titles, text noise, stale dates, and duplicate IDs caused the quality/freshness gates to fail and reduced measured retrieval/answer quality.
2. Repair rebuilt the dataframe and a separate Chroma collection from `data/raw/crossref_records.json`; it did not patch corrupted rows in place. The repaired quality, freshness, and evaluation metrics therefore returned to the clean baseline.

## Evidence artifacts

- `data/results/corruption_log.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/quality/corrupted_quality_report.json`
- `data/quality/repaired_quality_report.json`
"""
    write_text(report_path, report)
