import pandas as pd

from app.streamlit_app import kpis, month_tag, paths, prepare_timeline, top_cases


def make_eval() -> pd.DataFrame:
    ts = pd.date_range("2024-06-01", periods=4, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": ts,
            "price_eur_per_mwh": [10.0, 100.0, 20.0, 80.0],
            "risk_score": [0, 70, 80, 0],
            "regime_label": ["NORMAL", "STRESSED", "EXTREME", "NORMAL"],
            "reason_codes": ["NO_RULE_TRIGGERED", "A", "B", "NO_RULE_TRIGGERED"],
            "price_event_labels": ["NO_PRICE_EVENT", "HIGH_PRICE_LEVEL", "NO_PRICE_EVENT", "HIGH_PRICE_RAMP_UP"],
            "signal_positive": [False, True, True, False],
            "event_positive": [False, True, False, True],
            "confusion_bucket": ["TN", "TP", "FP", "FN"],
        }
    )


def test_month_tag() -> None:
    assert month_tag("2024-06-01", "2024-06-30") == "DE-LU_2024-06-01_to_2024-06-30"


def test_paths() -> None:
    out = paths("2024-06-01", "2024-06-30")

    assert str(out["evaluation"]).endswith("signal_price_evaluation_DE-LU_2024-06-01_to_2024-06-30.csv")


def test_kpis() -> None:
    out = kpis(make_eval())

    assert out["rows"] == 4
    assert out["signals"] == 2
    assert out["events"] == 2
    assert out["precision"] == 0.5


def test_prepare_timeline() -> None:
    out = prepare_timeline(make_eval())

    assert "price_eur_per_mwh" in out.columns
    assert "risk_score" in out.columns


def test_top_cases() -> None:
    out = top_cases(make_eval(), n=2)

    assert len(out) == 2
    assert out.iloc[0]["risk_score"] == 80
