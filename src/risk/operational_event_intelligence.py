from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd


OPERATIONAL_EVENT_SCHEMA_VERSION = "1.0"

REQUIRED_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "risk_score",
    "operational_state",
    "attention_level",
    "recommended_action",
    "risk_driver_count",
    "dominant_driver",
    "reason_codes",
    "operational_risk_schema_version",
]

DRIVER_PRIORITY = [
    "HIGH_RESIDUAL_LOAD",
    "LOW_RENEWABLE_SHARE",
    "HIGH_RESIDUAL_LOAD_RAMP",
    "HIGH_LOAD_RAMP",
    "HIGH_RENEWABLE_GENERATION_RAMP",
]

STATE_RANK = {
    "STABLE": 0,
    "HEIGHTENED": 1,
    "CONSTRAINED": 2,
    "CRITICAL": 3,
}


@dataclass(frozen=True)
class OperationalEventSummary:
    event_count: int
    total_event_hours: int
    longest_event_hours: int
    highest_peak_risk_score: float
    high_or_extreme_event_count: int
    multi_driver_event_count: int


def validate_operational_risk_frame(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]

    if missing:
        raise ValueError(
            f"Operational-risk frame is missing required columns: {missing}"
        )


def prepare_operational_risk_frame(frame: pd.DataFrame) -> pd.DataFrame:
    validate_operational_risk_frame(frame)

    prepared = frame.copy()
    prepared["timestamp_utc"] = pd.to_datetime(
        prepared["timestamp_utc"],
        utc=True,
    )
    prepared["timestamp_local"] = pd.to_datetime(
        prepared["timestamp_local"],
        utc=True,
    ).dt.tz_convert("Europe/Berlin")

    return prepared.sort_values("timestamp_utc").reset_index(drop=True)


def select_event_dominant_driver(values: pd.Series) -> str:
    drivers = [
        str(value)
        for value in values.dropna()
        if str(value) not in {"", "NONE", "nan"}
    ]

    if not drivers:
        return "NONE"

    counts = Counter(drivers)
    highest_count = max(counts.values())
    candidates = {
        driver
        for driver, count in counts.items()
        if count == highest_count
    }

    for driver in DRIVER_PRIORITY:
        if driver in candidates:
            return driver

    return sorted(candidates)[0]


def classify_event_severity(event: pd.DataFrame) -> str:
    states = set(event["operational_state"].astype(str))
    duration_hours = len(event)
    peak_risk_score = float(event["risk_score"].max())
    max_driver_count = int(event["risk_driver_count"].max())

    if "CRITICAL" in states:
        return "EXTREME"

    if (
        "CONSTRAINED" in states
        or duration_hours >= 6
        or (
            duration_hours >= 4
            and peak_risk_score >= 50
        )
    ):
        return "HIGH"

    if duration_hours >= 2 or max_driver_count >= 2:
        return "MEDIUM"

    return "LOW"


def detect_event_groups(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = prepare_operational_risk_frame(frame)
    active = prepared.loc[
        prepared["operational_state"] != "STABLE"
    ].copy()

    if active.empty:
        active["event_group"] = pd.Series(dtype="int64")
        return active

    previous_timestamp = active["timestamp_utc"].shift()
    previous_index = active.index.to_series().shift()

    starts_new_event = (
        previous_timestamp.isna()
        | active["timestamp_utc"].sub(previous_timestamp).ne(
            pd.Timedelta(hours=1)
        )
        | active.index.to_series().sub(previous_index).ne(1)
    )

    active["event_group"] = starts_new_event.cumsum().astype(int)

    return active


def build_operational_events(frame: pd.DataFrame) -> pd.DataFrame:
    active = detect_event_groups(frame)

    output_columns = [
        "event_id",
        "market_label",
        "smard_region",
        "event_start_utc",
        "event_end_utc",
        "event_start_local",
        "event_end_local",
        "duration_hours",
        "peak_risk_score",
        "mean_risk_score",
        "maximum_driver_count",
        "dominant_driver",
        "peak_operational_state",
        "state_progression",
        "contains_constrained",
        "contains_critical",
        "multi_driver_event",
        "severity",
        "escalation_required",
        "operational_event_schema_version",
    ]

    if active.empty:
        return pd.DataFrame(columns=output_columns)

    rows: list[dict[str, object]] = []

    for event_number, (_, event) in enumerate(
        active.groupby("event_group", sort=True),
        start=1,
    ):
        event = event.sort_values("timestamp_utc").reset_index(drop=True)

        peak_state = max(
            event["operational_state"].astype(str),
            key=lambda state: STATE_RANK.get(state, -1),
        )

        severity = classify_event_severity(event)
        maximum_driver_count = int(event["risk_driver_count"].max())

        rows.append(
            {
                "event_id": f"OE-{event_number:04d}",
                "market_label": str(event["market_label"].iloc[0]),
                "smard_region": str(event["smard_region"].iloc[0]),
                "event_start_utc": event["timestamp_utc"].iloc[0],
                "event_end_utc": event["timestamp_utc"].iloc[-1],
                "event_start_local": event["timestamp_local"].iloc[0],
                "event_end_local": event["timestamp_local"].iloc[-1],
                "duration_hours": int(len(event)),
                "peak_risk_score": float(event["risk_score"].max()),
                "mean_risk_score": float(event["risk_score"].mean()),
                "maximum_driver_count": maximum_driver_count,
                "dominant_driver": select_event_dominant_driver(
                    event["dominant_driver"]
                ),
                "peak_operational_state": peak_state,
                "state_progression": "|".join(
                    event["operational_state"].astype(str)
                ),
                "contains_constrained": bool(
                    (event["operational_state"] == "CONSTRAINED").any()
                ),
                "contains_critical": bool(
                    (event["operational_state"] == "CRITICAL").any()
                ),
                "multi_driver_event": bool(maximum_driver_count >= 2),
                "severity": severity,
                "escalation_required": severity in {"HIGH", "EXTREME"},
                "operational_event_schema_version": (
                    OPERATIONAL_EVENT_SCHEMA_VERSION
                ),
            }
        )

    return pd.DataFrame(rows, columns=output_columns)


def summarize_operational_events(
    events: pd.DataFrame,
) -> OperationalEventSummary:
    if events.empty:
        return OperationalEventSummary(
            event_count=0,
            total_event_hours=0,
            longest_event_hours=0,
            highest_peak_risk_score=0.0,
            high_or_extreme_event_count=0,
            multi_driver_event_count=0,
        )

    return OperationalEventSummary(
        event_count=int(len(events)),
        total_event_hours=int(events["duration_hours"].sum()),
        longest_event_hours=int(events["duration_hours"].max()),
        highest_peak_risk_score=float(events["peak_risk_score"].max()),
        high_or_extreme_event_count=int(
            events["severity"].isin(["HIGH", "EXTREME"]).sum()
        ),
        multi_driver_event_count=int(
            events["multi_driver_event"].sum()
        ),
    )


def load_operational_risk(path: str) -> pd.DataFrame:
    input_path = pd.io.common.stringify_path(path)

    try:
        frame = pd.read_csv(input_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Operational-risk input file was not found: {input_path}"
        ) from exc

    return frame


def build_operational_event_table(
    input_path: str,
    output_path: str,
) -> pd.DataFrame:
    frame = load_operational_risk(input_path)
    events = build_operational_events(frame)

    destination = pd.io.common.stringify_path(output_path)
    pd.DataFrame(events).to_csv(destination, index=False)

    return events
