import pandas as pd

from src.prices.price_risk_behavior import bucket_profile, event_lift, price_quantile_table, reason_price_profile


def make_eval() -> pd.DataFrame:
    ts = pd.date_range("2024-06-01", periods=4, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "price_eur_per_mwh": [10.0, 100.0, 20.0, 80.0],
            "price_ramp_eur_per_mwh": [None, 90.0, -80.0, 60.0],
            "risk_score": [0, 70, 80, 0],
            "regime_label": ["NORMAL", "STRESSED", "EXTREME", "NORMAL"],
            "reason_codes": ["NO_RULE_TRIGGERED", "A", "B", "NO_RULE_TRIGGERED"],
            "is_price_event": [False, True, False, True],
            "price_event_labels": ["NO_PRICE_EVENT", "HIGH_PRICE_LEVEL", "NO_PRICE_EVENT", "HIGH_PRICE_RAMP_UP"],
            "signal_positive": [False, True, True, False],
            "event_positive": [False, True, False, True],
            "confusion_bucket": ["TN", "TP", "FP", "FN"],
        }
    )


def test_event_lift() -> None:
    lift = event_lift(make_eval())

    assert lift["signal_rows"] == 2
    assert lift["price_event_rows"] == 2
    assert lift["event_lift_when_signal_positive"] == 1.0


def test_bucket_profile() -> None:
    out = bucket_profile(make_eval())

    assert set(out["bucket"]) == {"TN", "TP", "FP", "FN"}


def test_reason_price_profile() -> None:
    out = reason_price_profile(make_eval())

    assert "A" in set(out["reason_code"])


def test_price_quantile_table() -> None:
    out = price_quantile_table(make_eval())

    assert "price_q90" in out.columns
