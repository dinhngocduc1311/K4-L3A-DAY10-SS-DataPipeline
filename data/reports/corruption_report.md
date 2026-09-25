# Corruption and Idempotent Repair Report

## Three-state comparison

| Metric / Signal | Baseline (Clean) | Corrupted | Repaired |
|---|---:|---:|---:|
| Data Quality Gate | PASSED (6/6) | FAILED (4/6) | PASSED (6/6) |
| Freshness | FRESH | STALE | FRESH |
| Retrieval Hit Rate | 100.00% | 20.00% | 100.00% |
| Mean Token F1 | 1.0000 | 0.7329 | 1.0000 |
| Judge Accuracy | 100.00% | 80.00% | 100.00% |
| Mean Judge Score | 5.00 / 5 | 3.80 / 5 | 5.00 / 5 |

## Measured impact and recovery

- Corruption changed Retrieval Hit Rate by -80.00% and Mean Token F1 by -0.2671 versus baseline.
- Repair gap versus baseline: Retrieval Hit Rate +0.00%; Mean Token F1 +0.0000.
- Corrupted freshness: 13 / 24 stale rows (54.17%).
- Repaired freshness: 1 / 24 stale rows (4.17%).

## Causal interpretation

1. Dropped documents, blank summaries, truncated titles, text noise, stale dates, and duplicate IDs caused the quality/freshness gates to fail and reduced measured retrieval/answer quality.
2. Repair rebuilt the dataframe and a separate Chroma collection from `data/raw/crossref_records.json`; it did not patch corrupted rows in place. The repaired quality, freshness, and evaluation metrics therefore returned to the clean baseline.

## Evidence artifacts

- `data/results/corruption_log.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- `data/quality/corrupted_quality_report.json`
- `data/quality/repaired_quality_report.json`
