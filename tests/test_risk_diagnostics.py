import pandas as pd

from src.reporting.risk_diagnostics import (
    build_reason_code_summary,
    build_regime_distribution,
    build_top_risk_hours,
    diagnose_risk_signals,
    split_reason_codes,
)


def make_signals() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-06-01", periods=4, freq="h", tz="UTC"),
            "timestamp_local": pd.date_range("2024-06-01 02:00", periods=4, freq="h", tz="Europe/Berlin"),
            "market_label": ["DE-LU"] * 4,
            "smard_region": ["DE"] * 4,
            "risk_score": [0, 30, 60, 90],
            "regime_label": ["NORMAL", "WATCH", "STRESSED", "EXTREME"],
            "reason_codes": [
                "NO_RULE_TRIGGERED",
                "HIGH_LOAD_RAMP",
                "HIGH_RESIDUAL_LOAD|HIGH_LOAD_RAMP",
                "HIGH_RESIDUAL_LOAD|LOW_RENEWABLE_SHARE",
            ],
            "risk_schema_version": ["4A.1"] * 4,
        }
    )


def test_split_reason_codes() -> None:
    assert split_reason_codes("A|B|C") == ["A", "B", "C"]
    assert split_reason_codes("") == []
    assert split_reason_codes(None) == []


def test_build_regime_distribution() -> None:
    result = build_regime_distribution(make_signals())

    assert set(result["regime_label"]) == {"NORMAL", "WATCH", "STRESSED", "EXTREME"}
    assert int(result["count"].sum()) == 4


def test_build_reason_code_summary() -> None:
    result = build_reason_code_summary(make_signals())

    assert "HIGH_LOAD_RAMP" in set(result["reason_code"])
    assert "NO_RULE_TRIGGERED" in set(result["reason_code"])


def test_build_top_risk_hours() -> None:
    result = build_top_risk_hours(make_signals(), top_n=2)

    assert len(result) == 2
    assert result["risk_score"].iloc[0] == 90


def test_diagnose_risk_signals_passes() -> None:
    result = diagnose_risk_signals(make_signals())

    assert result.status == "PASS"
    assert result.row_count == 4
    assert result.high_risk_count == 2
    assert result.extreme_count == 1
