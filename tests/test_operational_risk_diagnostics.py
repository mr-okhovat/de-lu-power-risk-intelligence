import json

import pandas as pd

from src.risk.operational_risk_diagnostics import (
    build_attention_distribution,
    build_dominant_driver_summary,
    build_driver_count_distribution,
    build_operational_risk_diagnostics,
    build_state_distribution,
    diagnose_operational_risk,
)


def make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2024-08-01",
                periods=4,
                freq="h",
                tz="UTC",
            ),
            "timestamp_local": pd.date_range(
                "2024-08-01 02:00",
                periods=4,
                freq="h",
                tz="Europe/Berlin",
            ),
            "market_label": ["DE-LU"] * 4,
            "smard_region": ["DE"] * 4,
            "risk_score": [0, 30, 65, 90],
            "regime_label": ["NORMAL", "WATCH", "STRESSED", "EXTREME"],
            "operational_state": [
                "STABLE",
                "HEIGHTENED",
                "CONSTRAINED",
                "CRITICAL",
            ],
            "attention_level": [
                "ROUTINE",
                "MONITOR",
                "ACTIVE",
                "IMMEDIATE",
            ],
            "recommended_action": [
                "STANDARD_MONITORING",
                "INCREASE_MONITORING_FREQUENCY",
                "REVIEW_EXPOSURE_AND_FLEXIBILITY",
                "ESCALATE_AND_ASSESS_IMMEDIATE_MITIGATION",
            ],
            "risk_driver_count": [0, 1, 2, 3],
            "dominant_driver": [
                "NONE",
                "HIGH_LOAD_RAMP",
                "LOW_RENEWABLE_SHARE",
                "HIGH_RESIDUAL_LOAD",
            ],
            "reason_codes": [
                "NO_RULE_TRIGGERED",
                "HIGH_LOAD_RAMP",
                "LOW_RENEWABLE_SHARE|HIGH_RESIDUAL_LOAD_RAMP",
                "HIGH_RESIDUAL_LOAD|LOW_RENEWABLE_SHARE|HIGH_LOAD_RAMP",
            ],
            "risk_schema_version": ["4A.1"] * 4,
            "operational_risk_schema_version": ["1.0"] * 4,
        }
    )


def test_distributions_preserve_declared_order() -> None:
    frame = make_frame()

    states = build_state_distribution(frame)
    attention = build_attention_distribution(frame)

    assert states["operational_state"].tolist() == [
        "STABLE",
        "HEIGHTENED",
        "CONSTRAINED",
        "CRITICAL",
    ]
    assert attention["attention_level"].tolist() == [
        "ROUTINE",
        "MONITOR",
        "ACTIVE",
        "IMMEDIATE",
    ]
    assert states["count"].sum() == 4
    assert attention["count"].sum() == 4


def test_driver_summaries() -> None:
    frame = make_frame()

    dominant = build_dominant_driver_summary(frame)
    driver_counts = build_driver_count_distribution(frame)

    assert set(dominant["dominant_driver"]) == {
        "NONE",
        "HIGH_LOAD_RAMP",
        "LOW_RENEWABLE_SHARE",
        "HIGH_RESIDUAL_LOAD",
    }
    assert driver_counts["count"].sum() == 4


def test_diagnose_operational_risk() -> None:
    result = diagnose_operational_risk(make_frame())

    assert result.status == "PASS"
    assert result.row_count == 4
    assert result.critical_row_count == 1
    assert result.immediate_attention_count == 1
    assert result.multi_driver_row_count == 2
    assert result.no_driver_row_count == 1


def test_duplicate_timestamp_is_blocking() -> None:
    frame = make_frame()
    frame.loc[1, "timestamp_utc"] = frame.loc[0, "timestamp_utc"]

    result = diagnose_operational_risk(frame)

    assert result.status == "STOP — NEEDS VERIFICATION"
    assert result.duplicate_timestamp_count == 1


def test_build_writes_all_outputs(tmp_path) -> None:
    input_file = tmp_path / "operational_risk.csv"
    report = tmp_path / "report.md"
    output_json = tmp_path / "report.json"
    state_csv = tmp_path / "state.csv"
    attention_csv = tmp_path / "attention.csv"
    driver_csv = tmp_path / "driver.csv"
    driver_count_csv = tmp_path / "driver_count.csv"

    make_frame().to_csv(input_file, index=False)

    result = build_operational_risk_diagnostics(
        input_file=input_file,
        output_report=report,
        output_json=output_json,
        state_distribution_output=state_csv,
        attention_distribution_output=attention_csv,
        dominant_driver_output=driver_csv,
        driver_count_output=driver_count_csv,
    )

    assert result.status == "PASS"

    for output in [
        report,
        output_json,
        state_csv,
        attention_csv,
        driver_csv,
        driver_count_csv,
    ]:
        assert output.exists()

    payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert payload["status"] == "PASS"
    assert payload["critical_row_count"] == 1
    assert payload["operational_diagnostic_schema_version"] == "1.0"
