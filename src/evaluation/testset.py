from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


QUESTION_COUNTS = {"summary": 3, "authors": 2, "date": 2, "categories": 3}


@dataclass(frozen=True)
class BenchmarkTestSet:
    samples: list[dict[str, Any]]


def _sample(sample_id: int, question_type: str, question: str, answer: str, doc_ids: list[str]) -> dict[str, Any]:
    return {
        "id": f"eval_{sample_id:03d}",
        "type": question_type,
        "question_type": question_type,
        "question": question,
        "ground_truth": answer,
        "ground_truth_doc_ids": doc_ids,
    }


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build the 10-question, four-task benchmark required by the original rubric."""
    required = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(sorted(missing))}")
    if len(df) < 10:
        raise ValueError("At least 10 clean papers are required to build the benchmark.")

    rows = df.sort_values("paper_id").iloc[:7].to_dict(orient="records")
    latest = df.sort_values("published", ascending=False).iloc[:3].to_dict(orient="records")
    samples = [
        *[
            _sample(i + 1, "summary", f"What is the summary of the paper '{row['title']}'?",
                    first_sentence(row["summary"]), [row["paper_id"]])
            for i, row in enumerate(rows[:3])
        ],
        *[
            _sample(i + 4, "authors", f"Who authored the research '{row['title']}'?",
                    row["authors_joined"], [row["paper_id"]])
            for i, row in enumerate(rows[3:5])
        ],
        *[
            _sample(i + 6, "date", f"When was '{row['title']}' published?",
                    str(row["published"]), [row["paper_id"]])
            for i, row in enumerate(rows[5:7])
        ],
        *[
            _sample(i + 8, "categories", f"What categories does the paper '{row['title']}' belong to?",
                    row["categories_joined"], [row["paper_id"]])
            for i, row in enumerate(latest)
        ],
    ]
    write_json(Path(output_path), samples)
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path) -> BenchmarkTestSet:
    """Load a compatible benchmark or rebuild it from the current corpus."""
    path = Path(output_path)
    if path.exists():
        samples = read_json(path)
        doc_ids = set(df["paper_id"].astype(str))
        valid = (
            isinstance(samples, list)
            and len(samples) == sum(QUESTION_COUNTS.values())
            and {
                question_type: sum(sample.get("type") == question_type for sample in samples)
                for question_type in QUESTION_COUNTS
            } == QUESTION_COUNTS
            and all(
                {"id", "type", "question_type", "question", "ground_truth", "ground_truth_doc_ids"}
                <= sample.keys()
                and set(sample["ground_truth_doc_ids"]) <= doc_ids
                for sample in samples
            )
        )
        if valid:
            return BenchmarkTestSet(samples)
    return BenchmarkTestSet(build_test_set(df, path))
