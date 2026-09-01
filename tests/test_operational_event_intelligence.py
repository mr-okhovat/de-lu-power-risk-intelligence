import pandas as pd
import pytest

from src.risk.operational_event_intelligence import (
    build_operational_events,
    classify_event_severity,
    select_event_dominant_driver,
    summarize_operational_events,
)


def make_frame() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2024-08-01",
        periods=8,
        freq="h",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "timestamp_local": timestamps.tz_convert("Europe/Berlin"),
            "market_label": ["DE-LU"] * 8,
            "smard_region": ["DE"] * 8,
            "risk_score": [0, 30, 40, 70, 30, 0, 35, 0],
            "operational_state": [
                "STABLE",
                "HEIGHTENED",
                "HEIGHTENED",
                "CONSTRAINED",
                "HEIGHTENED",
                "STABLE",
                "HEIGHTENED",
                "STABLE",
            ],
            "attention_level": [
                "ROUTINE",
                "MONITOR",
                "MONITOR",
                "ACTIVE",
                "MONITOR",
                "ROUTINE",
                "MONITOR",
                "ROUTINE",
            ],
            "recommended_action": ["ACTION"] * 8,
            "risk_driver_count": [0, 1, 2, 3, 1, 0, 1, 0],
            "dominant_driver": [
                "NONE",
                "HIGH_LOAD_RAMP",
                "LOW_RENEWABLE_SHARE",
                "HIGH_RESIDUAL_LOAD",
                "HIGH_LOAD_RAMP",
                "NONE",
                "HIGH_RESIDUAL_LOAD_RAMP",
                "NONE",
            ],
            "reason_codes": ["NONE"] * 8,
            "operational_risk_schema_version": ["1.0"] * 8,
        }
    )


def test_build_operational_events_groups_contiguous_hours() -> None:
    events = build_operational_events(make_frame())

    assert len(events) == 2

    first = events.iloc[0]
    second = events.iloc[1]

    assert first["event_id"] == "OE-0001"
    assert first["duration_hours"] == 4
    assert first["peak_risk_score"] == 70
    assert first["peak_operational_state"] == "CONSTRAINED"
    assert first["severity"] == "HIGH"
    assert first["escalation_required"]

    assert second["event_id"] == "OE-0002"
    assert second["duration_hours"] == 1
    assert second["severity"] == "LOW"


def test_stable_hours_create_no_events() -> None:
    frame = make_frame()
    frame["operational_state"] = "STABLE"
    frame["risk_score"] = 0
    frame["risk_driver_count"] = 0
    frame["dominant_driver"] = "NONE"

    events = build_operational_events(frame)

    assert events.empty


def test_dominant_driver_uses_priority_for_ties() -> None:
    values = pd.Series(
        [
            "HIGH_LOAD_RAMP",
            "HIGH_RESIDUAL_LOAD",
        ]
    )

    assert select_event_dominant_driver(values) == "HIGH_RESIDUAL_LOAD"


def test_event_severity_accounts_for_persistence() -> None:
    frame = make_frame().iloc[1:5].copy()
    frame["operational_state"] = "HEIGHTENED"
    frame["risk_driver_count"] = 1

    assert classify_event_severity(frame) == "HIGH"


def test_summary_aggregates_event_metrics() -> None:
    events = build_operational_events(make_frame())
    summary = summarize_operational_events(events)

    assert summary.event_count == 2
    assert summary.total_event_hours == 5
    assert summary.longest_event_hours == 4
    assert summary.highest_peak_risk_score == 70
    assert summary.high_or_extreme_event_count == 1
    assert summary.multi_driver_event_count == 1


def test_missing_required_column_is_rejected() -> None:
    frame = make_frame().drop(columns=["risk_score"])

    with pytest.raises(ValueError, match="missing required columns"):
        build_operational_events(frame)


def test_low_score_four_hour_event_is_medium() -> None:
    frame = make_frame().iloc[1:5].copy()
    frame["operational_state"] = "HEIGHTENED"
    frame["risk_score"] = 30
    frame["risk_driver_count"] = 1

    assert classify_event_severity(frame) == "MEDIUM"


def test_single_constrained_hour_is_high() -> None:
    frame = make_frame().iloc[3:4].copy()
    frame["operational_state"] = "CONSTRAINED"
    frame["risk_score"] = 60
    frame["risk_driver_count"] = 3

    assert classify_event_severity(frame) == "HIGH"


def test_build_operational_event_table_writes_csv(tmp_path) -> None:
    from src.risk.operational_event_intelligence import (
        build_operational_event_table,
    )

    input_path = tmp_path / "operational_risk.csv"
    output_path = tmp_path / "operational_events.csv"

    make_frame().to_csv(input_path, index=False)

    events = build_operational_event_table(
        str(input_path),
        str(output_path),
    )

    assert output_path.exists()
    assert len(events) == 2

    written = pd.read_csv(output_path)

    assert list(written["event_id"]) == ["OE-0001", "OE-0002"]
    assert list(written["severity"]) == ["HIGH", "LOW"]


def test_load_operational_risk_rejects_missing_file(tmp_path) -> None:
    from src.risk.operational_event_intelligence import load_operational_risk

    missing_path = tmp_path / "missing.csv"

    with pytest.raises(
        FileNotFoundError,
        match="Operational-risk input file was not found",
    ):
        load_operational_risk(str(missing_path))
