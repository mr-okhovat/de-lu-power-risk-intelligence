import pandas as pd

from src.prices.price_events import build_events, check_quality, event_thresholds


def make_panel() -> pd.DataFrame:
    ts = pd.date_range("2024-06-01", periods=6, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "timestamp_local": ts.tz_convert("Europe/Berlin"),
            "market_label": ["DE-LU"] * 6,
            "price_eur_per_mwh": [-5.0, 20.0, 30.0, 100.0, 40.0, 10.0],
            "risk_score": [0, 0, 60, 85, 0, 30],
            "regime_label": ["NORMAL", "NORMAL", "STRESSED", "EXTREME", "NORMAL", "WATCH"],
            "reason_codes": ["NO_RULE_TRIGGERED", "NO_RULE_TRIGGERED", "A", "B", "NO_RULE_TRIGGERED", "C"],
        }
    )


def test_event_thresholds() -> None:
    levels = event_thresholds(make_panel(), 0.90, 0.10, 0.90)

    assert levels["high_price_threshold"] > levels["low_price_threshold"]
    assert levels["ramp_abs_threshold"] >= 0


def test_build_events_adds_labels() -> None:
    out, _ = build_events(make_panel(), 0.90, 0.10, 0.90)

    assert "price_event_labels" in out.columns
    assert int(out["is_price_event"].sum()) > 0


def test_check_quality_passes() -> None:
    out, levels = build_events(make_panel(), 0.90, 0.10, 0.90)
    quality = check_quality(out, levels)

    assert quality.status == "PASS"
    assert quality.event_rows > 0
