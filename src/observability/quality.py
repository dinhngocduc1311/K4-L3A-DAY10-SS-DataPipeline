from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations import expectations as gxe

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the GX 1.x quality gate and persist its JSON result."""
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        *(gxe.ExpectColumnValuesToNotBeNull(column=column) for column in ("paper_id", "title", "text_for_embedding")),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results = [batch.validate(expectation).to_json_dict() for expectation in expectations]
    freshness = _freshness_summary(df, settings.freshness_threshold_days)
    report = {
        "success": all(result["success"] for result in results) and freshness["is_fresh"],
        "report_name": report_name,
        "results": results,
        "freshness": freshness,
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist the freshness SLA summary."""
    report = _freshness_summary(df, settings.freshness_threshold_days)
    write_json(Path(report_path), report)
    return report


def _freshness_summary(df: pd.DataFrame, threshold_days: int) -> dict[str, Any]:
    published = pd.to_datetime(df.get("published", pd.Series(index=df.index, dtype="object")), utc=True, errors="coerce")
    ages = pd.to_numeric(df.get("age_days", pd.Series(index=df.index, dtype="float64")), errors="coerce")
    total_rows = len(df)
    stale_rows = int(ages.gt(threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    valid_dates = published.dropna()
    return {
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": threshold_days,
        "is_fresh": stale_ratio <= 0.25,
    }
