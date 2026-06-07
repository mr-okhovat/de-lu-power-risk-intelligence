import pandas as pd

from src.prices.price_risk_panel import build_panel, check_panel


def make_features() -> pd.DataFrame:
    ts = pd.date_range("2024-06-01", periods=3, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "timestamp_local": ts.tz_convert("Europe/Berlin"),
            "market_label": ["DE-LU"] * 3,
            "smard_region": ["DE"] * 3,
            "total_load_mw": [1, 2, 3],
            "residual_load_official_mw": [1, 2, 3],
            "renewable_generation_mw": [1, 1, 1],
            "renewable_share": [0.1, 0.2, 0.3],
            "load_ramp_mw": [None, 1, 1],
            "residual_load_ramp_mw": [None, 1, 1],
            "renewable_generation_ramp_mw": [None, 1, 1],
        }
    )


def make_prices() -> pd.DataFrame:
    ts = pd.date_range("2024-06-01", periods=3, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "price_eur_per_mwh": [50.0, 60.0, 70.0],
            "price_filter_id": ["4169"] * 3,
        }
    )


def make_risks() -> pd.DataFrame:
    ts = pd.date_range("2024-06-01", periods=3, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "risk_score": [0, 60, 85],
            "regime_label": ["NORMAL", "STRESSED", "EXTREME"],
            "reason_codes": ["NO_RULE_TRIGGERED", "A", "B"],
        }
    )


def test_build_panel() -> None:
    panel = build_panel(make_features(), make_prices(), make_risks())

    assert len(panel) == 3
    assert "price_eur_per_mwh" in panel.columns
    assert "risk_score" in panel.columns


def test_check_panel_passes() -> None:
    panel = build_panel(make_features(), make_prices(), make_risks())
    quality = check_panel(panel, 3, 3, 3)

    assert quality.status == "PASS"
    assert quality.high_risk_rows == 2
