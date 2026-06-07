import pandas as pd

from src.signals.risk_engine import (
    build_risk_signals,
    past_percentile_rank,
    regime_from_score,
    score_row,
    validate_risk_signals,
)


def make_feature_frame() -> pd.DataFrame:
    periods = 30

    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-06-01", periods=periods, freq="h", tz="UTC"),
            "timestamp_local": pd.date_range("2024-06-01 02:00", periods=periods, freq="h", tz="Europe/Berlin"),
            "market_label": ["DE-LU"] * periods,
            "smard_region": ["DE"] * periods,
            "total_load_mw": [100.0 + i for i in range(periods)],
            "residual_load_official_mw": [50.0 + i for i in range(periods)],
            "renewable_generation_mw": [50.0] * periods,
            "renewable_share": [0.50 - (i * 0.005) for i in range(periods)],
            "load_ramp_mw": [None] + [1.0] * (periods - 2) + [20.0],
            "residual_load_ramp_mw": [None] + [1.0] * (periods - 2) + [25.0],
            "renewable_generation_ramp_mw": [None] + [0.5] * (periods - 2) + [15.0],
            "feature_schema_version": ["3A.1"] * periods,
        }
    )


def test_past_percentile_rank_uses_past_only() -> None:
    values = pd.Series([1, 2, 3, 4, 100])

    result = past_percentile_rank(values, min_history=2)

    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == 1.0
    assert result.iloc[4] == 1.0


def test_regime_from_score() -> None:
    assert regime_from_score(0) == "NORMAL"
    assert regime_from_score(30) == "WATCH"
    assert regime_from_score(60) == "STRESSED"
    assert regime_from_score(85) == "EXTREME"


def test_score_row_with_rules() -> None:
    row = pd.Series(
        {
            "residual_load_percentile": 0.95,
            "renewable_share_percentile": 0.05,
            "abs_residual_load_ramp_percentile": 0.95,
            "abs_load_ramp_percentile": 0.95,
            "abs_renewable_generation_ramp_percentile": 0.95,
        }
    )

    score, reasons = score_row(row)

    assert score == 100
    assert "HIGH_RESIDUAL_LOAD" in reasons
    assert "LOW_RENEWABLE_SHARE" in reasons


def test_build_risk_signals_and_validate() -> None:
    features = make_feature_frame()
    signals = build_risk_signals(features, min_history=24)

    assert len(signals) == len(features)
    assert "risk_score" in signals.columns
    assert "regime_label" in signals.columns
    assert "reason_codes" in signals.columns

    result = validate_risk_signals(signals)

    assert result.status == "PASS"
    assert result.row_count == len(features)
