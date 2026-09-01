import pandas as pd
import pytest

from src.risk.operational_risk import (
    attention_level_from_regime,
    build_operational_risk,
    operational_state_from_regime,
    select_dominant_driver,
    split_reason_codes,
)


def make_signals() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2024-08-01", periods=4, freq="h", tz="UTC"
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
            "reason_codes": [
                "NO_RULE_TRIGGERED",
                "HIGH_LOAD_RAMP",
                "LOW_RENEWABLE_SHARE|HIGH_RESIDUAL_LOAD_RAMP",
                "HIGH_RESIDUAL_LOAD|LOW_RENEWABLE_SHARE|HIGH_LOAD_RAMP",
            ],
            "risk_schema_version": ["4A.1"] * 4,
        }
    )


def test_split_reason_codes_excludes_no_rule_triggered() -> None:
    assert split_reason_codes("NO_RULE_TRIGGERED") == []
    assert split_reason_codes("HIGH_LOAD_RAMP|LOW_RENEWABLE_SHARE") == [
        "HIGH_LOAD_RAMP",
        "LOW_RENEWABLE_SHARE",
    ]


def test_operational_classification() -> None:
    assert operational_state_from_regime("NORMAL") == "STABLE"
    assert operational_state_from_regime("EXTREME") == "CRITICAL"
    assert attention_level_from_regime("STRESSED") == "ACTIVE"

    with pytest.raises(ValueError):
        operational_state_from_regime("UNKNOWN")


def test_dominant_driver_uses_declared_priority() -> None:
    result = select_dominant_driver(
        ["HIGH_LOAD_RAMP", "LOW_RENEWABLE_SHARE", "HIGH_RESIDUAL_LOAD"]
    )

    assert result == "HIGH_RESIDUAL_LOAD"
    assert select_dominant_driver([]) == "NONE"


def test_build_operational_risk() -> None:
    result = build_operational_risk(make_signals())

    assert len(result) == 4
    assert result.loc[0, "operational_state"] == "STABLE"
    assert result.loc[3, "operational_state"] == "CRITICAL"
    assert result.loc[3, "attention_level"] == "IMMEDIATE"
    assert result.loc[2, "risk_driver_count"] == 2
    assert result.loc[3, "dominant_driver"] == "HIGH_RESIDUAL_LOAD"
    assert result.loc[0, "dominant_driver"] == "NONE"
    assert result["operational_risk_schema_version"].eq("1.0").all()


def test_build_operational_risk_rejects_missing_columns() -> None:
    signals = make_signals().drop(columns=["reason_codes"])

    with pytest.raises(ValueError, match="reason_codes"):
        build_operational_risk(signals)


def test_build_operational_risk_table_writes_output(tmp_path) -> None:
    from src.risk.operational_risk import build_operational_risk_table

    input_file = tmp_path / "risk_signals.csv"
    output_file = tmp_path / "operational_risk.csv"

    make_signals().to_csv(input_file, index=False)

    result = build_operational_risk_table(
        input_file=input_file,
        output_file=output_file,
    )

    assert output_file.exists()
    assert len(result) == 4

    written = pd.read_csv(output_file)

    assert written.loc[3, "operational_state"] == "CRITICAL"
    assert written.loc[3, "attention_level"] == "IMMEDIATE"


def test_load_risk_signals_rejects_missing_file(tmp_path) -> None:
    from src.risk.operational_risk import load_risk_signals

    missing = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="Risk-signal file not found"):
        load_risk_signals(missing)
