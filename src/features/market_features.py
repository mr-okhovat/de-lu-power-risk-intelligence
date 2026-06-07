from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


FEATURE_SCHEMA_VERSION = "3A.1"


REQUIRED_STAGING_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "total_load_mw",
    "residual_load_official_mw",
    "wind_onshore_validated_mw",
    "solar_validated_mw",
    "wind_offshore_validated_mw",
]


CORE_FEATURE_COLUMNS = [
    "wind_total_mw",
    "renewable_generation_mw",
    "residual_load_calculated_mw",
    "residual_gap_mw",
    "residual_gap_abs_mw",
    "renewable_share",
    "wind_share",
    "solar_share",
]


RAMP_COLUMNS = [
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
]


@dataclass(frozen=True)
class FeatureQualityResult:
    status: str
    row_count: int
    required_columns_missing: list[str]
    core_missing_by_column: dict[str, int]
    ramp_missing_by_column: dict[str, int]
    max_abs_residual_gap_mw: float
    mean_abs_residual_gap_mw: float
    residual_gap_tolerance_mw: float
    residual_gap_pass: bool
    share_range_violations: dict[str, int]
    notes: list[str]


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator_clean = denominator.replace({0: np.nan})
    return numerator / denominator_clean


def load_staging_frame(path: str | Path) -> pd.DataFrame:
    staging_path = Path(path)

    if not staging_path.exists():
        raise FileNotFoundError(f"Staging file not found: {staging_path}")

    df = pd.read_csv(staging_path)

    missing = [column for column in REQUIRED_STAGING_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Staging file is missing required columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], utc=True).dt.tz_convert(
        "Europe/Berlin"
    )

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def engineer_market_features(staging: pd.DataFrame) -> pd.DataFrame:
    df = staging.copy()

    df["wind_total_mw"] = (
        df["wind_onshore_validated_mw"] + df["wind_offshore_validated_mw"]
    )

    df["renewable_generation_mw"] = (
        df["wind_total_mw"] + df["solar_validated_mw"]
    )

    df["residual_load_calculated_mw"] = (
        df["total_load_mw"] - df["renewable_generation_mw"]
    )

    df["residual_gap_mw"] = (
        df["residual_load_calculated_mw"] - df["residual_load_official_mw"]
    )

    df["residual_gap_abs_mw"] = df["residual_gap_mw"].abs()

    df["renewable_share"] = safe_divide(
        df["renewable_generation_mw"],
        df["total_load_mw"],
    )

    df["wind_share"] = safe_divide(
        df["wind_total_mw"],
        df["total_load_mw"],
    )

    df["solar_share"] = safe_divide(
        df["solar_validated_mw"],
        df["total_load_mw"],
    )

    df["load_ramp_mw"] = df["total_load_mw"].diff()
    df["residual_load_ramp_mw"] = df["residual_load_official_mw"].diff()
    df["renewable_generation_ramp_mw"] = df["renewable_generation_mw"].diff()

    df["local_date"] = df["timestamp_local"].dt.date.astype(str)
    df["local_hour"] = df["timestamp_local"].dt.hour
    df["local_weekday"] = df["timestamp_local"].dt.day_name()
    df["is_weekend"] = df["timestamp_local"].dt.weekday >= 5

    df["feature_schema_version"] = FEATURE_SCHEMA_VERSION

    return df


def validate_feature_frame(
    df: pd.DataFrame,
    *,
    residual_gap_tolerance_mw: float = 1.0,
) -> FeatureQualityResult:
    required_output_columns = REQUIRED_STAGING_COLUMNS + CORE_FEATURE_COLUMNS + RAMP_COLUMNS

    required_columns_missing = [
        column for column in required_output_columns if column not in df.columns
    ]

    core_missing_by_column = {
        column: int(df[column].isna().sum())
        for column in CORE_FEATURE_COLUMNS
        if column in df.columns
    }

    ramp_missing_by_column = {
        column: int(df[column].isna().sum())
        for column in RAMP_COLUMNS
        if column in df.columns
    }

    max_abs_residual_gap_mw = (
        float(df["residual_gap_abs_mw"].max())
        if "residual_gap_abs_mw" in df.columns and not df.empty
        else float("inf")
    )

    mean_abs_residual_gap_mw = (
        float(df["residual_gap_abs_mw"].mean())
        if "residual_gap_abs_mw" in df.columns and not df.empty
        else float("inf")
    )

    residual_gap_pass = max_abs_residual_gap_mw <= residual_gap_tolerance_mw

    share_columns = ["renewable_share", "wind_share", "solar_share"]

    share_range_violations = {
        column: int(((df[column] < 0) | (df[column] > 2.0)).sum())
        for column in share_columns
        if column in df.columns
    }

    notes: list[str] = []

    if required_columns_missing:
        notes.append(f"Missing required feature columns: {required_columns_missing}")

    if sum(core_missing_by_column.values()) > 0:
        notes.append("Missing values found in core feature columns.")

    for column, missing_count in ramp_missing_by_column.items():
        if missing_count != 1:
            notes.append(
                f"Ramp column {column} has {missing_count} missing values; expected exactly 1 for first row."
            )

    if not residual_gap_pass:
        notes.append("Residual gap tolerance failed.")

    if sum(share_range_violations.values()) > 0:
        notes.append("Share range violations found.")

    if not notes:
        notes.append("Feature table passed all Phase 3A checks.")

    blocking_issue = (
        bool(required_columns_missing)
        or sum(core_missing_by_column.values()) > 0
        or any(count != 1 for count in ramp_missing_by_column.values())
        or not residual_gap_pass
        or sum(share_range_violations.values()) > 0
    )

    status = "STOP — NEEDS VERIFICATION" if blocking_issue else "PASS"

    return FeatureQualityResult(
        status=status,
        row_count=int(len(df)),
        required_columns_missing=required_columns_missing,
        core_missing_by_column=core_missing_by_column,
        ramp_missing_by_column=ramp_missing_by_column,
        max_abs_residual_gap_mw=max_abs_residual_gap_mw,
        mean_abs_residual_gap_mw=mean_abs_residual_gap_mw,
        residual_gap_tolerance_mw=residual_gap_tolerance_mw,
        residual_gap_pass=residual_gap_pass,
        share_range_violations=share_range_violations,
        notes=notes,
    )


def render_feature_quality_report(
    result: FeatureQualityResult,
    *,
    staging_path: str | Path,
    output_path: str | Path,
) -> str:
    lines: list[str] = [
        "# Feature Quality Report — Phase 3A",
        "",
        f"- Staging input: `{staging_path}`",
        f"- Feature output: `{output_path}`",
        f"- Status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Feature schema version: `{FEATURE_SCHEMA_VERSION}`",
        "",
        "## Required Columns Missing",
        "",
    ]

    if result.required_columns_missing:
        for column in result.required_columns_missing:
            lines.append(f"- `{column}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Core Missing Values", ""])

    for column, count in result.core_missing_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Ramp Missing Values", ""])

    for column, count in result.ramp_missing_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(
        [
            "",
            "## Residual Gap Check",
            "",
            f"- Tolerance MW: `{result.residual_gap_tolerance_mw}`",
            f"- Pass: `{result.residual_gap_pass}`",
            f"- Max absolute residual gap MW: `{result.max_abs_residual_gap_mw}`",
            f"- Mean absolute residual gap MW: `{result.mean_abs_residual_gap_mw}`",
            "",
            "## Share Range Violations",
            "",
        ]
    )

    for column, count in result.share_range_violations.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Notes", ""])

    for note in result.notes:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This phase creates a feature table from validated staging data. It does not yet create risk scores, trading signals, backtests, SQL schemas, or Power BI dashboards.",
            "",
            "Ramp features use current hour minus previous hour. The first row is expected to contain missing ramp values because no previous observation exists inside the selected window.",
            "",
        ]
    )

    return "\n".join(lines)


def build_market_features(
    *,
    staging_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    metadata_path: str | Path | None = None,
    residual_gap_tolerance_mw: float = 1.0,
) -> pd.DataFrame:
    staging = load_staging_frame(staging_path)
    features = engineer_market_features(staging)

    quality_result = validate_feature_frame(
        features,
        residual_gap_tolerance_mw=residual_gap_tolerance_mw,
    )

    output_path = Path(output_path)
    report_path = Path(report_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    features.to_csv(output_path, index=False)

    report_path.write_text(
        render_feature_quality_report(
            quality_result,
            staging_path=staging_path,
            output_path=output_path,
        ),
        encoding="utf-8",
    )

    if metadata_path is None:
        metadata_path = output_path.with_suffix(".metadata.json")

    metadata_path = Path(metadata_path)

    metadata_payload = {
        "stage": "features",
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "staging_input": str(Path(staging_path).as_posix()),
        "feature_output": str(output_path.as_posix()),
        "quality_report": str(report_path.as_posix()),
        "quality_result": asdict(quality_result),
        "feature_columns": list(features.columns),
        "notes": [
            "No price features are included in Phase 3A.",
            "No risk scores are created in Phase 3A.",
            "No backtest is created in Phase 3A.",
        ],
    }

    metadata_path.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | features rows={len(features)} | output={output_path}")
    print(f"OK | feature quality status={quality_result.status} | report={report_path}")

    if quality_result.status == "STOP — NEEDS VERIFICATION":
        raise SystemExit(1)

    return features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Phase 3A market features.")

    parser.add_argument("--staging-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--metadata-output", default=None)
    parser.add_argument("--residual-gap-tolerance-mw", type=float, default=1.0)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_market_features(
        staging_path=args.staging_file,
        output_path=args.output,
        report_path=args.report_output,
        metadata_path=args.metadata_output,
        residual_gap_tolerance_mw=args.residual_gap_tolerance_mw,
    )


if __name__ == "__main__":
    main()
