from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records and produce the dataframe used for embeddings."""
    df = pd.DataFrame((asdict(record) for record in records), columns=PaperRecord.__dataclass_fields__)
    if df.empty:
        return df.assign(
            authors_joined="",
            categories_joined="",
            summary_chars=pd.Series(dtype="int64"),
            age_days=pd.Series(dtype="int64"),
            text_for_embedding="",
        )

    for column in ("paper_id", "title", "summary", "primary_category", "abs_url", "pdf_url", "comment"):
        df[column] = df[column].fillna("").astype(str).map(normalize_whitespace)
    for column in ("authors", "categories"):
        df[column] = df[column].map(
            lambda values: [
                normalized
                for value in (values or [])
                if (normalized := normalize_whitespace(str(value)))
            ]
        )

    df = df[df["paper_id"].ne("") & df["title"].ne("") & df["summary"].ne("")]
    df = df.drop_duplicates(subset="paper_id", keep="first").copy()
    published = pd.to_datetime(df["published"], utc=True, errors="coerce")
    updated = pd.to_datetime(df["updated"], utc=True, errors="coerce")
    df = df[published.notna()].copy()
    published = published.loc[df.index]
    updated = updated.loc[df.index]
    run_timestamp = pd.Timestamp(run_date)
    run_timestamp = (
        run_timestamp.tz_localize("UTC")
        if run_timestamp.tzinfo is None
        else run_timestamp.tz_convert("UTC")
    )

    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d").fillna(df["published"])
    df["age_days"] = (run_timestamp.normalize() - published.dt.normalize()).dt.days.astype(int)
    df["authors_joined"] = df["authors"].str.join(", ")
    df["categories_joined"] = df["categories"].str.join(", ")
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nPublished: {row['published']}\n"
            f"Categories: {row['categories_joined']}\nSummary: {row['summary']}"
        ),
        axis=1,
    )
    return df.sort_values("paper_id").reset_index(drop=True)
