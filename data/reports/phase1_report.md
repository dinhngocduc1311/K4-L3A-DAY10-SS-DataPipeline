# Baseline Pipeline Report

## Data source and index

| Field | Value |
|---|---|
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Clean papers | 24 |
| Published range | 2026-03-28 to 2026-07-22 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Chroma collection | `papers-baseline` |

## Baseline metrics

| Metric | Value |
|---|---:|
| Benchmark samples | 10 |
| Retrieval Hit Rate | 100.00% |
| Mean Token F1 | 1.0000 |
| LLM Judge Accuracy | 100.00% |
| Mean LLM Judge Score | 5.00 / 5 |
| Judge mode | `heuristic_fallback` |

Ragas: Set RUN_RAGAS=1 to enable the slower Ragas pass.

## Data quality and freshness

| Check | Value |
|---|---:|
| Quality gate | PASS |
| GX expectations passed | 6 / 6 |
| Freshness SLA | PASS |
| Stale papers | 1 / 24 (4.17%) |
| Freshness threshold | 180 days; maximum stale ratio 25% |
