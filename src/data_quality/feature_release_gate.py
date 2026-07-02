from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


REQUIRED_FEATURE_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "total_load_mw",
    "residual_load_official_mw",
    "wind_onshore_validated_mw",
    "solar_validated_mw",
    "wind_offshore_validated_mw",
    "missing_any_flag",
    "wind_total_mw",
    "renewable_generation_mw",
    "residual_load_calculated_mw",
    "residual_gap_mw",
    "residual_gap_abs_mw",
    "renewable_share",
    "wind_share",
    "solar_share",
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
    "local_date",
    "local_hour",
    "local_weekday",
    "is_weekend",
    "feature_schema_version",
]

CORE_VALUE_COLUMNS = [
    "total_load_mw",
    "residual_load_official_mw",
    "wind_onshore_validated_mw",
    "solar_validated_mw",
    "wind_offshore_validated_mw",
    "wind_total_mw",
    "renewable_generation_mw",
    "residual_load_calculated_mw",
    "residual_gap_mw",
    "residual_gap_abs_mw",
    "renewable_share",
    "wind_share",
    "solar_share",
]

IDENTITY_COLUMNS = [
    "timestamp_local",
    "market_label",
    "smard_region",
    "missing_any_flag",
    "local_date",
    "local_hour",
    "local_weekday",
    "is_weekend",
    "feature_schema_version",
]

RAMP_COLUMNS = [
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
]

SHARE_COLUMNS = [
    "renewable_share",
    "wind_share",
    "solar_share",
]


@dataclass(frozen=True)
class FeatureReleaseGateResult:
    status: str
    row_count: int
    expected_hour_count: int
    required_columns_missing: list[str]
    invalid_timestamp_count: int
    duplicate_timestamp_count: int
    hourly_continuity_breaks: int
    core_missing_by_column: dict[str, int]
    identity_missing_by_column: dict[str, int]
    missing_any_flag_true_count: int
    ramp_missing_outside_first_by_column: dict[str, int]
    residual_gap_max_abs_mw: float | None
    residual_gap_tolerance_mw: float
    residual_gap_pass: bool
    share_range_violations: dict[str, int]
    market_label_values: list[str]
    smard_region_values: list[str]
    metadata_checks: dict[str, bool]
    blocking_reasons: list[str]
    notes: list[str]


def _unique_text_values(series: pd.Series) -> list[str]:
    return sorted(series.dropna().astype(str).unique().tolist())


def _expected_hour_count(timestamps: pd.Series) -> int:
    valid = timestamps.dropna()

    if valid.empty:
        return 0

    return int(((valid.max() - valid.min()).total_seconds() / 3600) + 1)


def _count_hourly_continuity_breaks(timestamps: pd.Series) -> int:
    valid = timestamps.dropna().sort_values()

    if len(valid) <= 1:
        return 0

    return int((valid.diff().dropna() != pd.Timedelta(hours=1)).sum())


def _validate_metadata(
    *,
    feature_path: Path,
    metadata_path: Path,
    df: pd.DataFrame,
    feature_schema_values: list[str],
) -> tuple[dict[str, bool], list[str]]:
    checks = {
        "metadata_file_exists": False,
        "metadata_is_valid_json_object": False,
        "feature_output_matches": False,
        "metadata_row_count_matches": False,
        "metadata_quality_status_pass": False,
        "feature_schema_version_matches": False,
    }
    blocking_reasons: list[str] = []

    if not metadata_path.exists():
        blocking_reasons.append(f"Metadata file not found: {metadata_path}")
        return checks, blocking_reasons

    checks["metadata_file_exists"] = True

    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        blocking_reasons.append(f"Metadata is not valid JSON: {error}")
        return checks, blocking_reasons

    if not isinstance(payload, dict):
        blocking_reasons.append("Metadata payload must be a JSON object.")
        return checks, blocking_reasons

    checks["metadata_is_valid_json_object"] = True

    feature_output = payload.get("feature_output")
    if isinstance(feature_output, str) and Path(feature_output).name == feature_path.name:
        checks["feature_output_matches"] = True
    else:
        blocking_reasons.append("Metadata feature_output does not match the dataset filename.")

    quality_result = payload.get("quality_result")
    if isinstance(quality_result, dict):
        if quality_result.get("row_count") == len(df):
            checks["metadata_row_count_matches"] = True
        else:
            blocking_reasons.append(
                "Metadata quality_result.row_count does not match the dataset row count."
            )

        if quality_result.get("status") == "PASS":
            checks["metadata_quality_status_pass"] = True
        else:
            blocking_reasons.append("Metadata quality_result.status is not PASS.")
    else:
        blocking_reasons.append("Metadata quality_result is missing or invalid.")

    metadata_schema_version = payload.get("feature_schema_version")
    if (
        len(feature_schema_values) == 1
        and metadata_schema_version == feature_schema_values[0]
    ):
        checks["feature_schema_version_matches"] = True
    else:
        blocking_reasons.append(
            "Metadata feature_schema_version does not match the dataset schema version."
        )

    return checks, blocking_reasons


def run_feature_release_gate(
    feature_path: str | Path,
    *,
    metadata_path: str | Path,
    residual_gap_tolerance_mw: float = 1.0,
    expected_market_label: str = "DE-LU",
    expected_smard_region: str = "DE",
) -> FeatureReleaseGateResult:
    path = Path(feature_path)
    metadata = Path(metadata_path)

    if not path.exists():
        raise FileNotFoundError(f"Feature dataset not found: {path}")

    df = pd.read_csv(path)

    required_columns_missing = [
        column for column in REQUIRED_FEATURE_COLUMNS
        if column not in df.columns
    ]

    timestamps = (
        pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
        if "timestamp_utc" in df.columns
        else pd.Series(dtype="datetime64[ns, UTC]")
    )

    invalid_timestamp_count = (
        int(timestamps.isna().sum())
        if "timestamp_utc" in df.columns
        else 0
    )

    duplicate_timestamp_count = (
        int(timestamps.duplicated().sum())
        if not timestamps.empty
        else 0
    )

    expected_hour_count = _expected_hour_count(timestamps)
    hourly_continuity_breaks = _count_hourly_continuity_breaks(timestamps)

    core_missing_by_column = {
        column: int(df[column].isna().sum())
        for column in CORE_VALUE_COLUMNS
        if column in df.columns
    }

    identity_missing_by_column = {
        column: int(df[column].isna().sum())
        for column in IDENTITY_COLUMNS
        if column in df.columns
    }

    missing_any_flag_true_count = 0
    if "missing_any_flag" in df.columns:
        flag = df["missing_any_flag"].astype(str).str.strip().str.lower()
        missing_any_flag_true_count = int(
            df["missing_any_flag"].isna().sum()
            + flag.isin(["true", "1", "yes"]).sum()
        )

    ramp_missing_outside_first_by_column = {
        column: int(df[column].iloc[1:].isna().sum())
        for column in RAMP_COLUMNS
        if column in df.columns
    }

    residual_gap_max_abs_mw: float | None = None
    residual_gap_pass = False

    if "residual_gap_abs_mw" in df.columns:
        non_null_gap = df["residual_gap_abs_mw"].dropna()

        if not non_null_gap.empty:
            residual_gap_max_abs_mw = float(non_null_gap.abs().max())
            residual_gap_pass = bool(
                residual_gap_max_abs_mw <= residual_gap_tolerance_mw
            )

    share_range_violations = {
        column: int(((df[column] < 0.0) | (df[column] > 1.0)).sum())
        for column in SHARE_COLUMNS
        if column in df.columns
    }

    market_label_values = (
        _unique_text_values(df["market_label"])
        if "market_label" in df.columns
        else []
    )

    smard_region_values = (
        _unique_text_values(df["smard_region"])
        if "smard_region" in df.columns
        else []
    )

    feature_schema_values = (
        _unique_text_values(df["feature_schema_version"])
        if "feature_schema_version" in df.columns
        else []
    )

    metadata_checks, metadata_blocking_reasons = _validate_metadata(
        feature_path=path,
        metadata_path=metadata,
        df=df,
        feature_schema_values=feature_schema_values,
    )

    blocking_reasons: list[str] = []

    if df.empty:
        blocking_reasons.append("Feature dataset is empty.")

    if required_columns_missing:
        blocking_reasons.append(
            f"Missing required feature columns: {required_columns_missing}"
        )

    if invalid_timestamp_count:
        blocking_reasons.append(
            f"Invalid timestamp_utc values: {invalid_timestamp_count}"
        )

    if duplicate_timestamp_count:
        blocking_reasons.append(
            f"Duplicate timestamp_utc values: {duplicate_timestamp_count}"
        )

    if hourly_continuity_breaks:
        blocking_reasons.append(
            f"Hourly continuity breaks: {hourly_continuity_breaks}"
        )

    if sum(core_missing_by_column.values()) > 0:
        blocking_reasons.append("Missing values found in core analytical columns.")

    if sum(identity_missing_by_column.values()) > 0:
        blocking_reasons.append("Missing values found in dataset identity columns.")

    if missing_any_flag_true_count:
        blocking_reasons.append(
            f"missing_any_flag is true or missing for {missing_any_flag_true_count} rows."
        )

    if sum(ramp_missing_outside_first_by_column.values()) > 0:
        blocking_reasons.append(
            "Missing ramp values found outside the first observation."
        )

    if not residual_gap_pass:
        blocking_reasons.append(
            "Residual-gap check failed or could not run within configured tolerance."
        )

    if sum(share_range_violations.values()) > 0:
        blocking_reasons.append(
            "Share values outside the inclusive [0, 1] range."
        )

    if market_label_values != [expected_market_label]:
        blocking_reasons.append(
            f"Expected market_label [{expected_market_label}], "
            f"observed {market_label_values}."
        )

    if smard_region_values != [expected_smard_region]:
        blocking_reasons.append(
            f"Expected smard_region [{expected_smard_region}], "
            f"observed {smard_region_values}."
        )

    blocking_reasons.extend(metadata_blocking_reasons)

    return FeatureReleaseGateResult(
        status="READY" if not blocking_reasons else "BLOCKED",
        row_count=int(len(df)),
        expected_hour_count=expected_hour_count,
        required_columns_missing=required_columns_missing,
        invalid_timestamp_count=invalid_timestamp_count,
        duplicate_timestamp_count=duplicate_timestamp_count,
        hourly_continuity_breaks=hourly_continuity_breaks,
        core_missing_by_column=core_missing_by_column,
        identity_missing_by_column=identity_missing_by_column,
        missing_any_flag_true_count=missing_any_flag_true_count,
        ramp_missing_outside_first_by_column=ramp_missing_outside_first_by_column,
        residual_gap_max_abs_mw=residual_gap_max_abs_mw,
        residual_gap_tolerance_mw=residual_gap_tolerance_mw,
        residual_gap_pass=residual_gap_pass,
        share_range_violations=share_range_violations,
        market_label_values=market_label_values,
        smard_region_values=smard_region_values,
        metadata_checks=metadata_checks,
        blocking_reasons=blocking_reasons,
        notes=[
            "This gate validates release readiness, not predictive value or trading performance.",
            "Null ramp values are accepted only for the first observation.",
        ],
    )


def render_feature_release_report(
    result: FeatureReleaseGateResult,
    *,
    feature_path: str | Path,
    metadata_path: str | Path,
) -> str:
    lines = [
        "# Analytical Dataset Release Gate",
        "",
        f"- Feature dataset: `{feature_path}`",
        f"- Metadata file: `{metadata_path}`",
        f"- Release status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Expected hour count: `{result.expected_hour_count}`",
        f"- Invalid timestamps: `{result.invalid_timestamp_count}`",
        f"- Duplicate timestamps: `{result.duplicate_timestamp_count}`",
        f"- Hourly continuity breaks: `{result.hourly_continuity_breaks}`",
        f"- Residual-gap tolerance MW: `{result.residual_gap_tolerance_mw}`",
        f"- Residual-gap max absolute MW: `{result.residual_gap_max_abs_mw}`",
        f"- Residual-gap pass: `{result.residual_gap_pass}`",
        "",
        "## Metadata Checks",
        "",
    ]

    lines.extend(
        f"- `{name}`: `{passed}`"
        for name, passed in result.metadata_checks.items()
    )

    lines.extend(["", "## Blocking Reasons", ""])

    if result.blocking_reasons:
        lines.extend(f"- {reason}" for reason in result.blocking_reasons)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Release Policy",
            "",
            "Only datasets with `READY` status may feed downstream risk signals, dashboards, or reviewer-facing reports.",
            "",
        ]
    )

    return "\n".join(lines)


def write_feature_release_artifacts(
    result: FeatureReleaseGateResult,
    *,
    feature_path: str | Path,
    metadata_path: str | Path,
    report_output: str | Path,
    json_output: str | Path,
) -> None:
    report_path = Path(report_output)
    json_path = Path(json_output)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(
        render_feature_release_report(
            result,
            feature_path=feature_path,
            metadata_path=metadata_path,
        ),
        encoding="utf-8",
    )

    json_path.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
