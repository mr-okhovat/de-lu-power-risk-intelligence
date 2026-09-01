import json

import pandas as pd
import pytest

from src.risk.operational_event_diagnostics import (
    build_duration_distribution,
    build_event_driver_summary,
    build_operational_event_diagnostics,
    build_severity_distribution,
    diagnose_operational_events,
)
from src.risk.operational_event_intelligence import (
    build_operational_events,
)

from tests.test_operational_event_intelligence import make_frame


def make_events() -> pd.DataFrame:
    return build_operational_events(make_frame())


def test_diagnostics_pass_for_unique_event_ids() -> None:
    diagnostics = diagnose_operational_events(make_events())

    assert diagnostics["status"] == "PASS"
    assert diagnostics["event_count"] == 2
    assert diagnostics["duplicate_event_id_count"] == 0
    assert diagnostics["escalation_required_count"] == 1


def test_duplicate_event_ids_fail_diagnostics() -> None:
    events = make_events()
    events.loc[1, "event_id"] = events.loc[0, "event_id"]

    diagnostics = diagnose_operational_events(events)

    assert diagnostics["status"] == "FAIL"
    assert diagnostics["duplicate_event_id_count"] == 1


def test_severity_distribution_includes_zero_categories() -> None:
    result = build_severity_distribution(make_events())

    assert list(result["severity"]) == [
        "LOW",
        "MEDIUM",
        "HIGH",
        "EXTREME",
    ]
    assert result["count"].sum() == 2


def test_duration_distribution_counts_events() -> None:
    result = build_duration_distribution(make_events())

    assert result["count"].sum() == 2
    assert set(result["duration_hours"]) == {1, 4}


def test_driver_summary_aggregates_events() -> None:
    result = build_event_driver_summary(make_events())

    assert result["count"].sum() == 2
    assert "dominant_driver" in result.columns


def test_missing_required_column_is_rejected() -> None:
    events = make_events().drop(columns=["severity"])

    with pytest.raises(ValueError, match="missing required columns"):
        diagnose_operational_events(events)


def test_build_diagnostics_writes_all_outputs(tmp_path) -> None:
    input_path = tmp_path / "events.csv"
    report_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    severity_path = tmp_path / "severity.csv"
    duration_path = tmp_path / "duration.csv"
    driver_path = tmp_path / "drivers.csv"

    make_events().to_csv(input_path, index=False)

    diagnostics = build_operational_event_diagnostics(
        str(input_path),
        str(report_path),
        str(json_path),
        str(severity_path),
        str(duration_path),
        str(driver_path),
    )

    assert diagnostics["status"] == "PASS"

    for path in [
        report_path,
        json_path,
        severity_path,
        duration_path,
        driver_path,
    ]:
        assert path.exists()

    loaded = json.loads(json_path.read_text())

    assert loaded["event_count"] == 2
