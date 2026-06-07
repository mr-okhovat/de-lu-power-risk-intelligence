import pandas as pd

from src.prices.signal_price_evaluation import compute_metrics, evaluate, event_type_summary


def make_events() -> pd.DataFrame:
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
        }
    )


def test_evaluate() -> None:
    out = evaluate(make_events(), 60)

    assert "confusion_bucket" in out.columns
    assert set(out["confusion_bucket"]) == {"TN", "TP", "FP", "FN"}


def test_compute_metrics() -> None:
    out = evaluate(make_events(), 60)
    metrics = compute_metrics(out)

    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.false_negative == 1
    assert metrics.true_negative == 1


def test_event_type_summary() -> None:
    out = evaluate(make_events(), 60)
    summary = event_type_summary(out)

    assert "HIGH_PRICE_LEVEL" in set(summary["price_event_label"])
