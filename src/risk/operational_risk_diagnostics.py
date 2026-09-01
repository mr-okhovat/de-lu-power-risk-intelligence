from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


OPERATIONAL_DIAGNOSTIC_SCHEMA_VERSION = "1.0"

REQUIRED_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "risk_score",
    "regime_label",
    "operational_state",
    "attention_level",
    "recommended_action",
    "risk_driver_count",
    "dominant_driver",
    "reason_codes",
    "risk_schema_version",
    "operational_risk_schema_version",
]

STATE_ORDER = ["STABLE", "HEIGHTENED", "CONSTRAINED", "CRITICAL"]
ATTENTION_ORDER = ["ROUTINE", "MONITOR", "ACTIVE", "IMMEDIATE"]


@dataclass(frozen=True)
class OperationalRiskDiagnosticResult:
    status: str
    row_count: int
    required_columns_missing: list[str]
    duplicate_timestamp_count: int
    critical_row_count: int
    immediate_attention_count: int
    multi_driver_row_count: int
    no_driver_row_count: int
    unique_states: list[str]
    unique_attention_levels: list[str]
    unique_dominant_drivers: list[str]
    notes: list[str]


def load_operational_risk(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)

    if not input_path.exists():
        raise FileNotFoundError(f"Operational-risk file not found: {input_path}")

    frame = pd.read_csv(input_path)

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"Operational-risk file is missing required columns: {missing}"
        )

    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp_utc"], utc=True)
    frame["timestamp_local"] = pd.to_datetime(
        frame["timestamp_local"], utc=True
    ).dt.tz_convert("Europe/Berlin")

    return frame.sort_values("timestamp_utc").reset_index(drop=True)


def ordered_distribution(
    frame: pd.DataFrame,
    *,
    column: str,
    ordered_values: list[str],
) -> pd.DataFrame:
    counts = frame[column].value_counts().to_dict()
    total = len(frame)

    return pd.DataFrame(
        [
            {
                column: value,
                "count": int(counts.get(value, 0)),
                "share": float(counts.get(value, 0) / total) if total else 0.0,
                "operational_diagnostic_schema_version": (
                    OPERATIONAL_DIAGNOSTIC_SCHEMA_VERSION
                ),
            }
            for value in ordered_values
        ]
    )


def build_state_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    return ordered_distribution(
        frame,
        column="operational_state",
        ordered_values=STATE_ORDER,
    )


def build_attention_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    return ordered_distribution(
        frame,
        column="attention_level",
        ordered_values=ATTENTION_ORDER,
    )


def build_dominant_driver_summary(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame["dominant_driver"].value_counts()
    total = len(frame)

    rows = [
        {
            "dominant_driver": str(driver),
            "count": int(count),
            "share": float(count / total) if total else 0.0,
            "mean_risk_score": float(
                frame.loc[frame["dominant_driver"] == driver, "risk_score"].mean()
            ),
            "operational_diagnostic_schema_version": (
                OPERATIONAL_DIAGNOSTIC_SCHEMA_VERSION
            ),
        }
        for driver, count in counts.items()
    ]

    return pd.DataFrame(rows).sort_values(
        ["count", "dominant_driver"],
        ascending=[False, True],
    ).reset_index(drop=True)


def build_driver_count_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame["risk_driver_count"].value_counts().sort_index()
    total = len(frame)

    return pd.DataFrame(
        [
            {
                "risk_driver_count": int(driver_count),
                "count": int(count),
                "share": float(count / total) if total else 0.0,
                "operational_diagnostic_schema_version": (
                    OPERATIONAL_DIAGNOSTIC_SCHEMA_VERSION
                ),
            }
            for driver_count, count in counts.items()
        ]
    )


def diagnose_operational_risk(
    frame: pd.DataFrame,
) -> OperationalRiskDiagnosticResult:
    required_columns_missing = [
        column for column in REQUIRED_COLUMNS if column not in frame.columns
    ]

    duplicate_timestamp_count = (
        int(frame["timestamp_utc"].duplicated().sum())
        if "timestamp_utc" in frame.columns
        else 0
    )

    critical_row_count = (
        int((frame["operational_state"] == "CRITICAL").sum())
        if "operational_state" in frame.columns
        else 0
    )

    immediate_attention_count = (
        int((frame["attention_level"] == "IMMEDIATE").sum())
        if "attention_level" in frame.columns
        else 0
    )

    multi_driver_row_count = (
        int((frame["risk_driver_count"] >= 2).sum())
        if "risk_driver_count" in frame.columns
        else 0
    )

    no_driver_row_count = (
        int((frame["risk_driver_count"] == 0).sum())
        if "risk_driver_count" in frame.columns
        else 0
    )

    unique_states = (
        sorted(str(value) for value in frame["operational_state"].dropna().unique())
        if "operational_state" in frame.columns
        else []
    )

    unique_attention_levels = (
        sorted(str(value) for value in frame["attention_level"].dropna().unique())
        if "attention_level" in frame.columns
        else []
    )

    unique_dominant_drivers = (
        sorted(str(value) for value in frame["dominant_driver"].dropna().unique())
        if "dominant_driver" in frame.columns
        else []
    )

    notes: list[str] = []

    if required_columns_missing:
        notes.append(
            f"Missing operational-risk columns: {required_columns_missing}"
        )

    if duplicate_timestamp_count:
        notes.append(
            f"Duplicate operational-risk timestamps found: "
            f"{duplicate_timestamp_count}"
        )

    if critical_row_count == 0:
        notes.append(
            "No CRITICAL operational states were observed in this window."
        )

    if multi_driver_row_count == 0:
        notes.append(
            "No compound operational-risk rows with two or more drivers were observed."
        )

    if no_driver_row_count == len(frame):
        notes.append(
            "Every row has zero active risk drivers; operational differentiation is limited."
        )

    if not notes:
        notes.append("Operational-risk diagnostics passed all checks.")

    blocking_issue = bool(required_columns_missing) or duplicate_timestamp_count > 0

    status = "STOP — NEEDS VERIFICATION" if blocking_issue else "PASS"

    return OperationalRiskDiagnosticResult(
        status=status,
        row_count=int(len(frame)),
        required_columns_missing=required_columns_missing,
        duplicate_timestamp_count=duplicate_timestamp_count,
        critical_row_count=critical_row_count,
        immediate_attention_count=immediate_attention_count,
        multi_driver_row_count=multi_driver_row_count,
        no_driver_row_count=no_driver_row_count,
        unique_states=unique_states,
        unique_attention_levels=unique_attention_levels,
        unique_dominant_drivers=unique_dominant_drivers,
        notes=notes,
    )


def render_operational_risk_report(
    *,
    result: OperationalRiskDiagnosticResult,
    input_file: str | Path,
    state_distribution_output: str | Path,
    attention_distribution_output: str | Path,
    dominant_driver_output: str | Path,
    driver_count_output: str | Path,
) -> str:
    lines = [
        "# Operational Risk Diagnostic Report",
        "",
        f"- Input: `{input_file}`",
        f"- Status: `{result.status}`",
        f"- Rows: `{result.row_count}`",
        f"- Schema version: `{OPERATIONAL_DIAGNOSTIC_SCHEMA_VERSION}`",
        "",
        "## Operational Readout",
        "",
        f"- Critical rows: `{result.critical_row_count}`",
        f"- Immediate-attention rows: `{result.immediate_attention_count}`",
        f"- Multi-driver rows: `{result.multi_driver_row_count}`",
        f"- Zero-driver rows: `{result.no_driver_row_count}`",
        f"- Duplicate timestamps: `{result.duplicate_timestamp_count}`",
        "",
        "## Coverage",
        "",
        f"- Operational states: `{result.unique_states}`",
        f"- Attention levels: `{result.unique_attention_levels}`",
        f"- Dominant drivers: `{result.unique_dominant_drivers}`",
        "",
        "## Output Tables",
        "",
        f"- State distribution: `{state_distribution_output}`",
        f"- Attention distribution: `{attention_distribution_output}`",
        f"- Dominant-driver summary: `{dominant_driver_output}`",
        f"- Driver-count distribution: `{driver_count_output}`",
        "",
        "## Notes",
        "",
    ]

    lines.extend(f"- {note}" for note in result.notes)

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This layer translates existing rule-based risk signals into operational categories and diagnostic summaries.",
            "",
            "Recommended actions are controlled decision-support labels. They do not represent automated trading instructions, dispatch commands, or validated financial recommendations.",
            "",
        ]
    )

    return "\n".join(lines)


def build_operational_risk_diagnostics(
    *,
    input_file: str | Path,
    output_report: str | Path,
    output_json: str | Path,
    state_distribution_output: str | Path,
    attention_distribution_output: str | Path,
    dominant_driver_output: str | Path,
    driver_count_output: str | Path,
) -> OperationalRiskDiagnosticResult:
    frame = load_operational_risk(input_file)
    result = diagnose_operational_risk(frame)

    outputs = [
        output_report,
        output_json,
        state_distribution_output,
        attention_distribution_output,
        dominant_driver_output,
        driver_count_output,
    ]

    for output in outputs:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    build_state_distribution(frame).to_csv(
        state_distribution_output,
        index=False,
    )
    build_attention_distribution(frame).to_csv(
        attention_distribution_output,
        index=False,
    )
    build_dominant_driver_summary(frame).to_csv(
        dominant_driver_output,
        index=False,
    )
    build_driver_count_distribution(frame).to_csv(
        driver_count_output,
        index=False,
    )

    Path(output_report).write_text(
        render_operational_risk_report(
            result=result,
            input_file=input_file,
            state_distribution_output=state_distribution_output,
            attention_distribution_output=attention_distribution_output,
            dominant_driver_output=dominant_driver_output,
            driver_count_output=driver_count_output,
        ),
        encoding="utf-8",
    )

    Path(output_json).write_text(
        json.dumps(
            {
                **asdict(result),
                "operational_diagnostic_schema_version": (
                    OPERATIONAL_DIAGNOSTIC_SCHEMA_VERSION
                ),
                "outputs": {
                    "state_distribution": str(state_distribution_output),
                    "attention_distribution": str(attention_distribution_output),
                    "dominant_driver_summary": str(dominant_driver_output),
                    "driver_count_distribution": str(driver_count_output),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build operational-risk diagnostics."
    )
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--state-distribution-output", required=True)
    parser.add_argument("--attention-distribution-output", required=True)
    parser.add_argument("--dominant-driver-output", required=True)
    parser.add_argument("--driver-count-output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    result = build_operational_risk_diagnostics(
        input_file=args.input_file,
        output_report=args.output_report,
        output_json=args.output_json,
        state_distribution_output=args.state_distribution_output,
        attention_distribution_output=args.attention_distribution_output,
        dominant_driver_output=args.dominant_driver_output,
        driver_count_output=args.driver_count_output,
    )

    print(
        f"OK | operational-risk diagnostics status={result.status} "
        f"| rows={result.row_count}"
    )


if __name__ == "__main__":
    main()
