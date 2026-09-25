from __future__ import annotations

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six deterministic corruption scenarios into a clean dataframe."""
    required = {
        "paper_id", "title", "summary", "published", "authors_joined",
        "categories_joined", "text_for_embedding",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(sorted(missing))}")
    if len(df) < 6:
        raise ValueError("At least 6 clean rows are required for corruption testing.")

    corrupted = df.copy(deep=True)
    published = pd.to_datetime(corrupted["published"], utc=True, errors="coerce")
    if published.isna().any():
        raise ValueError("All published values must be valid dates.")

    drop_count = max(1, round(len(corrupted) * 0.2))
    dropped_index = published.nlargest(drop_count).index
    dropped_ids = corrupted.loc[dropped_index, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(dropped_index).sort_values("paper_id").reset_index(drop=True)

    blank_index = corrupted.index[:3]
    blank_ids = corrupted.loc[blank_index, "paper_id"].astype(str).tolist()
    corrupted.loc[blank_index, "summary"] = ""
    if "summary_chars" in corrupted:
        corrupted.loc[blank_index, "summary_chars"] = 0

    truncate_index = corrupted.index[:3]
    truncate_ids = corrupted.loc[truncate_index, "paper_id"].astype(str).tolist()
    corrupted.loc[truncate_index, "title"] = corrupted.loc[truncate_index, "title"].str[:7].str.rstrip()

    stale_index = corrupted.index[:8]
    stale_dates = pd.to_datetime(corrupted.loc[stale_index, "published"], utc=True) - pd.DateOffset(years=5)
    corrupted.loc[stale_index, "published"] = stale_dates.dt.strftime("%Y-%m-%d")
    if "age_days" in corrupted:
        today = pd.Timestamp.now(tz="UTC").normalize()
        corrupted.loc[stale_index, "age_days"] = (today - stale_dates.dt.normalize()).dt.days.to_numpy()
    stale_ids = corrupted.loc[stale_index, "paper_id"].astype(str).tolist()

    noise_index = corrupted.index[3:8]
    noise_ids = corrupted.loc[noise_index, "paper_id"].astype(str).tolist()
    corrupted.loc[noise_index, "summary"] += " zxqv_9f3a !!!" * 20
    if "summary_chars" in corrupted:
        corrupted.loc[noise_index, "summary_chars"] = corrupted.loc[noise_index, "summary"].str.len()

    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: (
            f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nPublished: {row['published']}\n"
            f"Categories: {row['categories_joined']}\nSummary: {row['summary']}"
        ),
        axis=1,
    )
    duplicate_source = corrupted.iloc[:drop_count].copy()
    duplicate_ids = duplicate_source["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_source], ignore_index=True)

    scenarios = [
        {"name": "drop_latest_records", "affected_rows": drop_count, "paper_ids": dropped_ids},
        {"name": "blank_summary", "affected_rows": len(blank_ids), "paper_ids": blank_ids},
        {"name": "inject_text_noise", "affected_rows": len(noise_ids), "paper_ids": noise_ids},
        {"name": "truncate_title", "affected_rows": len(truncate_ids), "paper_ids": truncate_ids, "max_length": 7},
        {"name": "stale_date", "affected_rows": len(stale_ids), "paper_ids": stale_ids, "years_shifted": 5},
        {"name": "duplicate_rows", "affected_rows": len(duplicate_ids), "paper_ids": duplicate_ids},
    ]
    write_json(output_log_path, {"input_rows": len(df), "output_rows": len(corrupted), "scenarios": scenarios})
    return corrupted.reset_index(drop=True)
