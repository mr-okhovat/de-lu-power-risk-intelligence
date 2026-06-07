from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StagingQualityResult:
    row_count: int
    duplicate_timestamp_count: int
    missing_by_column: dict[str, int]
    negative_by_column: dict[str, int]
    min_timestamp_utc: str | None
    max_timestamp_utc: str | None
    status: str
    notes: list[str]


def validate_staging_frame(
    df: pd.DataFrame,
    *,
    value_columns: list[str],
    positive_only_columns: list[str],
    provisional_columns: list[str],
) -> StagingQualityResult:
    notes: list[str] = []

    if df.empty:
        return StagingQualityResult(
            row_count=0,
            duplicate_timestamp_count=0,
            missing_by_column={},
            negative_by_column={},
            min_timestamp_utc=None,
            max_timestamp_utc=None,
            status="STOP",
            notes=["Staging dataframe is empty."],
        )

    if "timestamp_utc" not in df.columns:
        raise ValueError("Staging dataframe must contain timestamp_utc.")

    duplicate_timestamp_count = int(df["timestamp_utc"].duplicated().sum())

    missing_by_column = {
        column: int(df[column].isna().sum())
        for column in value_columns
        if column in df.columns
    }

    negative_by_column = {
        column: int((df[column] < 0).sum())
        for column in positive_only_columns
        if column in df.columns
    }

    if duplicate_timestamp_count > 0:
        notes.append(f"Duplicate timestamps found: {duplicate_timestamp_count}")

    missing_total = sum(missing_by_column.values())
    if missing_total > 0:
        notes.append(f"Missing values found across value columns: {missing_total}")

    negative_total = sum(negative_by_column.values())
    if negative_total > 0:
        notes.append(f"Negative values found in positive-only columns: {negative_total}")

    if provisional_columns:
        notes.append(
            "Some columns are based on provisional semantic status and must not be used "
            "for final feature claims without validation."
        )

    status = "PASS"

    if duplicate_timestamp_count > 0 or missing_total > 0 or negative_total > 0:
        status = "PASS WITH LIMITATION"

    if provisional_columns and status == "PASS":
        status = "PASS WITH LIMITATION"

    return StagingQualityResult(
        row_count=int(len(df)),
        duplicate_timestamp_count=duplicate_timestamp_count,
        missing_by_column=missing_by_column,
        negative_by_column=negative_by_column,
        min_timestamp_utc=str(df["timestamp_utc"].min()),
        max_timestamp_utc=str(df["timestamp_utc"].max()),
        status=status,
        notes=notes,
    )


def render_quality_report(
    *,
    result: StagingQualityResult,
    market_label: str,
    smard_region: str,
    start: str,
    end: str,
    value_columns: list[str],
    provisional_columns: list[str],
) -> str:
    lines: list[str] = [
        "# Data Quality Report — Clean Hourly Staging",
        "",
        f"- Market label: `{market_label}`",
        f"- SMARD region: `{smard_region}`",
        f"- Requested start: `{start}`",
        f"- Requested end: `{end}`",
        f"- Status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Min timestamp UTC: `{result.min_timestamp_utc}`",
        f"- Max timestamp UTC: `{result.max_timestamp_utc}`",
        f"- Duplicate timestamps: `{result.duplicate_timestamp_count}`",
        "",
        "## Value Columns",
        "",
    ]

    for column in value_columns:
        lines.append(f"- `{column}`")

    lines.extend(["", "## Missing Values", ""])

    for column, count in result.missing_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Negative Values in Positive-Only Columns", ""])

    for column, count in result.negative_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Provisional Semantic Columns", ""])

    if provisional_columns:
        for column in provisional_columns:
            lines.append(f"- `{column}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Notes", ""])

    if result.notes:
        for note in result.notes:
            lines.append(f"- {note}")
    else:
        lines.append("- No material quality notes.")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report validates the staging layer only. It does not yet validate final "
            "feature correctness, risk-signal usefulness, or backtest performance.",
            "",
        ]
    )

    return "\n".join(lines)
