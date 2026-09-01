from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.risk.operational_event_intelligence import (
    OPERATIONAL_EVENT_SCHEMA_VERSION,
    OperationalEventSummary,
    summarize_operational_events,
)


OPERATIONAL_EVENT_DIAGNOSTIC_SCHEMA_VERSION = "1.0"

REQUIRED_COLUMNS = [
    "event_id",
    "duration_hours",
    "peak_risk_score",
    "mean_risk_score",
    "maximum_driver_count",
    "dominant_driver",
    "peak_operational_state",
    "severity",
    "escalation_required",
    "multi_driver_event",
    "contains_constrained",
    "contains_critical",
    "operational_event_schema_version",
]


def validate_operational_events(events: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in events.columns]

    if missing:
        raise ValueError(
            f"Operational-event frame is missing required columns: {missing}"
        )


def build_severity_distribution(events: pd.DataFrame) -> pd.DataFrame:
    validate_operational_events(events)

    severity_order = ["LOW", "MEDIUM", "HIGH", "EXTREME"]
    counts = (
        events["severity"]
        .value_counts()
        .reindex(severity_order, fill_value=0)
    )

    total = int(len(events))

    return pd.DataFrame(
        {
            "severity": severity_order,
            "count": counts.values,
            "share": [
                float(count / total) if total else 0.0
                for count in counts.values
            ],
            "operational_event_diagnostic_schema_version": (
                OPERATIONAL_EVENT_DIAGNOSTIC_SCHEMA_VERSION
            ),
        }
    )


def build_duration_distribution(events: pd.DataFrame) -> pd.DataFrame:
    validate_operational_events(events)

    if events.empty:
        return pd.DataFrame(
            columns=[
                "duration_hours",
                "count",
                "share",
                "operational_event_diagnostic_schema_version",
            ]
        )

    counts = events["duration_hours"].value_counts().sort_index()
    total = int(len(events))

    return pd.DataFrame(
        {
            "duration_hours": counts.index.astype(int),
            "count": counts.values.astype(int),
            "share": counts.values / total,
            "operational_event_diagnostic_schema_version": (
                OPERATIONAL_EVENT_DIAGNOSTIC_SCHEMA_VERSION
            ),
        }
    )


def build_event_driver_summary(events: pd.DataFrame) -> pd.DataFrame:
    validate_operational_events(events)

    if events.empty:
        return pd.DataFrame(
            columns=[
                "dominant_driver",
                "count",
                "share",
                "mean_peak_risk_score",
                "mean_duration_hours",
                "operational_event_diagnostic_schema_version",
            ]
        )

    grouped = (
        events.groupby("dominant_driver", dropna=False)
        .agg(
            count=("event_id", "count"),
            mean_peak_risk_score=("peak_risk_score", "mean"),
            mean_duration_hours=("duration_hours", "mean"),
        )
        .reset_index()
    )

    grouped["share"] = grouped["count"] / len(events)
    grouped["operational_event_diagnostic_schema_version"] = (
        OPERATIONAL_EVENT_DIAGNOSTIC_SCHEMA_VERSION
    )

    return grouped[
        [
            "dominant_driver",
            "count",
            "share",
            "mean_peak_risk_score",
            "mean_duration_hours",
            "operational_event_diagnostic_schema_version",
        ]
    ].sort_values(
        ["count", "mean_peak_risk_score"],
        ascending=[False, False],
    ).reset_index(drop=True)


def diagnose_operational_events(events: pd.DataFrame) -> dict[str, object]:
    validate_operational_events(events)

    summary: OperationalEventSummary = summarize_operational_events(events)

    duplicate_event_id_count = int(events["event_id"].duplicated().sum())
    escalation_count = int(events["escalation_required"].sum())
    constrained_event_count = int(events["contains_constrained"].sum())
    critical_event_count = int(events["contains_critical"].sum())

    status = "PASS" if duplicate_event_id_count == 0 else "FAIL"

    return {
        "status": status,
        "schema_version": OPERATIONAL_EVENT_DIAGNOSTIC_SCHEMA_VERSION,
        "source_schema_version": OPERATIONAL_EVENT_SCHEMA_VERSION,
        **asdict(summary),
        "duplicate_event_id_count": duplicate_event_id_count,
        "escalation_required_count": escalation_count,
        "constrained_event_count": constrained_event_count,
        "critical_event_count": critical_event_count,
        "mean_event_duration_hours": (
            float(events["duration_hours"].mean())
            if not events.empty
            else 0.0
        ),
        "mean_peak_risk_score": (
            float(events["peak_risk_score"].mean())
            if not events.empty
            else 0.0
        ),
    }


def render_operational_event_report(
    diagnostics: dict[str, object],
) -> str:
    lines = [
        "# Operational Event Diagnostics",
        "",
        f"- Status: {diagnostics['status']}",
        f"- Event count: {diagnostics['event_count']}",
        f"- Total event hours: {diagnostics['total_event_hours']}",
        f"- Longest event: {diagnostics['longest_event_hours']} hours",
        (
            "- Highest peak risk score: "
            f"{diagnostics['highest_peak_risk_score']}"
        ),
        (
            "- High or extreme events: "
            f"{diagnostics['high_or_extreme_event_count']}"
        ),
        (
            "- Multi-driver events: "
            f"{diagnostics['multi_driver_event_count']}"
        ),
        (
            "- Escalation-required events: "
            f"{diagnostics['escalation_required_count']}"
        ),
        (
            "- Constrained events: "
            f"{diagnostics['constrained_event_count']}"
        ),
        (
            "- Critical events: "
            f"{diagnostics['critical_event_count']}"
        ),
        (
            "- Duplicate event IDs: "
            f"{diagnostics['duplicate_event_id_count']}"
        ),
        "",
        "## Interpretation boundary",
        "",
        (
            "Event severity is a deterministic decision-support classification "
            "derived from persistence, operational state and risk intensity. "
            "It is not a probability estimate, market forecast or dispatch instruction."
        ),
        "",
    ]

    return "\n".join(lines)


def build_operational_event_diagnostics(
    input_path: str,
    report_output_path: str,
    json_output_path: str,
    severity_output_path: str,
    duration_output_path: str,
    driver_output_path: str,
) -> dict[str, object]:
    events = pd.read_csv(input_path)

    diagnostics = diagnose_operational_events(events)
    report = render_operational_event_report(diagnostics)

    outputs = [
        report_output_path,
        json_output_path,
        severity_output_path,
        duration_output_path,
        driver_output_path,
    ]

    for output in outputs:
        Path(output).parent.mkdir(parents=True, exist_ok=True)

    Path(report_output_path).write_text(report)
    Path(json_output_path).write_text(
        json.dumps(diagnostics, indent=2)
    )

    build_severity_distribution(events).to_csv(
        severity_output_path,
        index=False,
    )
    build_duration_distribution(events).to_csv(
        duration_output_path,
        index=False,
    )
    build_event_driver_summary(events).to_csv(
        driver_output_path,
        index=False,
    )

    return diagnostics
