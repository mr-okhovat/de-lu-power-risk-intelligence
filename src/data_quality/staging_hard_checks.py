from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class ResidualReconciliationResult:
    checked: bool
    max_abs_error_mw: float | None
    mean_abs_error_mw: float | None
    tolerance_mw: float
    pass_check: bool
    note: str


@dataclass(frozen=True)
class StagingHardCheckResult:
    status: str
    row_count: int
    expected_hour_count: int
    required_columns_missing: list[str]
    duplicate_timestamp_count: int
    hourly_continuity_breaks: int
    missing_by_column: dict[str, int]
    range_violations: dict[str, int]
    residual_reconciliation: ResidualReconciliationResult
    notes: list[str]


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
    "missing_any_flag",
]


RANGE_RULES = {
    "total_load_mw": {"min": 0.0, "max": 120000.0},
    "residual_load_official_mw": {"min": -20000.0, "max": 120000.0},
    "wind_onshore_validated_mw": {"min": 0.0, "max": 80000.0},
    "solar_validated_mw": {"min": 0.0, "max": 80000.0},
    "wind_offshore_validated_mw": {"min": 0.0, "max": 40000.0},
}


def expected_hour_count_from_staging(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    timestamps = pd.to_datetime(df["timestamp_utc"], utc=True)
    start = timestamps.min()
    end = timestamps.max()

    return int(((end - start).total_seconds() / 3600) + 1)


def count_hourly_continuity_breaks(df: pd.DataFrame) -> int:
    if df.empty or len(df) == 1:
        return 0

    timestamps = pd.to_datetime(df["timestamp_utc"], utc=True).sort_values()
    diffs = timestamps.diff().dropna()

    return int((diffs != pd.Timedelta(hours=1)).sum())


def count_range_violations(df: pd.DataFrame) -> dict[str, int]:
    violations: dict[str, int] = {}

    for column, rule in RANGE_RULES.items():
        if column not in df.columns:
            continue

        lower = float(rule["min"])
        upper = float(rule["max"])

        count = int(((df[column] < lower) | (df[column] > upper)).sum())
        violations[column] = count

    return violations


def reconcile_residual_load(
    df: pd.DataFrame,
    *,
    tolerance_mw: float = 1.0,
) -> ResidualReconciliationResult:
    required = [
        "total_load_mw",
        "residual_load_official_mw",
        "wind_onshore_validated_mw",
        "solar_validated_mw",
        "wind_offshore_validated_mw",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        return ResidualReconciliationResult(
            checked=False,
            max_abs_error_mw=None,
            mean_abs_error_mw=None,
            tolerance_mw=tolerance_mw,
            pass_check=False,
            note=f"Residual reconciliation skipped. Missing columns: {missing}",
        )

    derived_residual = (
        df["total_load_mw"]
        - df["wind_onshore_validated_mw"]
        - df["solar_validated_mw"]
        - df["wind_offshore_validated_mw"]
    )

    error = (derived_residual - df["residual_load_official_mw"]).abs()

    max_abs_error = float(error.max())
    mean_abs_error = float(error.mean())
    pass_check = bool(max_abs_error <= tolerance_mw)

    if pass_check:
        note = (
            "Residual reconciliation passed. Candidate renewable columns reconcile "
            "against official residual load within tolerance."
        )
    else:
        note = (
            "Residual reconciliation failed. Candidate renewable columns do not "
            "reconcile against official residual load within tolerance."
        )

    return ResidualReconciliationResult(
        checked=True,
        max_abs_error_mw=max_abs_error,
        mean_abs_error_mw=mean_abs_error,
        tolerance_mw=tolerance_mw,
        pass_check=pass_check,
        note=note,
    )


def run_staging_hard_checks(
    staging_path: str | Path,
    *,
    residual_tolerance_mw: float = 1.0,
) -> StagingHardCheckResult:
    path = Path(staging_path)

    if not path.exists():
        raise FileNotFoundError(f"Staging file not found: {path}")

    df = pd.read_csv(path)

    required_columns_missing = [
        column for column in REQUIRED_STAGING_COLUMNS
        if column not in df.columns
    ]

    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    duplicate_timestamp_count = (
        int(df["timestamp_utc"].duplicated().sum())
        if "timestamp_utc" in df.columns
        else 0
    )

    expected_hour_count = expected_hour_count_from_staging(df) if "timestamp_utc" in df.columns else 0

    hourly_continuity_breaks = (
        count_hourly_continuity_breaks(df)
        if "timestamp_utc" in df.columns
        else 0
    )

    value_columns = [
        column for column in REQUIRED_STAGING_COLUMNS
        if column.endswith("_mw") and column in df.columns
    ]

    missing_by_column = {
        column: int(df[column].isna().sum())
        for column in value_columns
    }

    range_violations = count_range_violations(df)

    residual_result = reconcile_residual_load(
        df,
        tolerance_mw=residual_tolerance_mw,
    )

    notes: list[str] = []

    if required_columns_missing:
        notes.append(f"Missing required columns: {required_columns_missing}")

    if duplicate_timestamp_count:
        notes.append(f"Duplicate timestamps found: {duplicate_timestamp_count}")

    if hourly_continuity_breaks:
        notes.append(f"Hourly continuity breaks found: {hourly_continuity_breaks}")

    if sum(missing_by_column.values()) > 0:
        notes.append("Missing values found in value columns.")

    if sum(range_violations.values()) > 0:
        notes.append("Value range violations found.")

    notes.append(residual_result.note)

    notes.append(
        "Renewable component series have been promoted based on exact residual-load "
        "reconciliation evidence. This validates staging coherence, not predictive value."
    )

    blocking_issue = (
        bool(required_columns_missing)
        or duplicate_timestamp_count > 0
        or hourly_continuity_breaks > 0
        or sum(missing_by_column.values()) > 0
        or sum(range_violations.values()) > 0
        or not residual_result.pass_check
    )

    if blocking_issue:
        status = "STOP — NEEDS VERIFICATION"
    else:
        status = "PASS"

    return StagingHardCheckResult(
        status=status,
        row_count=int(len(df)),
        expected_hour_count=int(expected_hour_count),
        required_columns_missing=required_columns_missing,
        duplicate_timestamp_count=duplicate_timestamp_count,
        hourly_continuity_breaks=hourly_continuity_breaks,
        missing_by_column=missing_by_column,
        range_violations=range_violations,
        residual_reconciliation=residual_result,
        notes=notes,
    )


def render_hard_check_report(
    result: StagingHardCheckResult,
    *,
    staging_path: str | Path,
) -> str:
    lines: list[str] = [
        "# Staging Validation Hardening Report",
        "",
        f"- Staging file: `{staging_path}`",
        f"- Status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Expected hour count from timestamp span: `{result.expected_hour_count}`",
        f"- Duplicate timestamps: `{result.duplicate_timestamp_count}`",
        f"- Hourly continuity breaks: `{result.hourly_continuity_breaks}`",
        "",
        "## Required Columns Missing",
        "",
    ]

    if result.required_columns_missing:
        for column in result.required_columns_missing:
            lines.append(f"- `{column}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Missing Values", ""])

    for column, count in result.missing_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Range Violations", ""])

    for column, count in result.range_violations.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(
        [
            "",
            "## Residual Load Reconciliation",
            "",
            f"- Checked: `{result.residual_reconciliation.checked}`",
            f"- Tolerance MW: `{result.residual_reconciliation.tolerance_mw}`",
            f"- Pass: `{result.residual_reconciliation.pass_check}`",
            f"- Max absolute error MW: `{result.residual_reconciliation.max_abs_error_mw}`",
            f"- Mean absolute error MW: `{result.residual_reconciliation.mean_abs_error_mw}`",
            f"- Note: {result.residual_reconciliation.note}",
            "",
            "## Notes",
            "",
        ]
    )

    for note in result.notes:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This hardening report checks whether the staging table is structurally reliable "
            "enough for feature engineering. It does not yet claim predictive value or "
            "trading usefulness.",
            "",
        ]
    )

    return "\n".join(lines)


def write_hard_check_outputs(
    *,
    result: StagingHardCheckResult,
    staging_path: str | Path,
    report_path: str | Path,
    json_path: str | Path,
) -> None:
    report_path = Path(report_path)
    json_path = Path(json_path)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(
        render_hard_check_report(result, staging_path=staging_path),
        encoding="utf-8",
    )

    json_path.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hard validation checks on staging data.")

    parser.add_argument("--staging-file", required=True)
    parser.add_argument("--report-output", default="reports/staging_hard_checks.md")
    parser.add_argument("--json-output", default="reports/staging_hard_checks.json")
    parser.add_argument("--residual-tolerance-mw", type=float, default=1.0)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = run_staging_hard_checks(
        args.staging_file,
        residual_tolerance_mw=args.residual_tolerance_mw,
    )

    write_hard_check_outputs(
        result=result,
        staging_path=args.staging_file,
        report_path=args.report_output,
        json_path=args.json_output,
    )

    print(f"OK | hard-check status={result.status}")
    print(f"OK | report={args.report_output}")
    print(f"OK | json={args.json_output}")

    if result.status == "STOP — NEEDS VERIFICATION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
