import pandas as pd

from app.streamlit_app import (
    bucket_counts,
    csv_bytes,
    file_status_table,
    kpis,
    month_tag,
    monthly_lift_frame,
    monthly_rate_frame,
    paths,
    price_event_summary,
    reason_summary,
    signal_cases,
    timeline_combined,
    timeline_price,
    timeline_risk,
    top_cases,
)


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


def make_cross() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": ["May 2024", "June 2024"],
            "base_event_rate": [0.25, 0.26],
            "signal_event_rate": [0.50, 0.57],
            "event_lift": [2.0, 2.2],
        }
    )


def test_month_tag() -> None:
    assert month_tag("2024-06-01", "2024-06-30") == "DE-LU_2024-06-01_to_2024-06-30"


def test_paths() -> None:
    out = paths("2024-06-01", "2024-06-30")

    assert str(out["evaluation"]).endswith("signal_price_evaluation_DE-LU_2024-06-01_to_2024-06-30.csv")
    assert "visual_pack" in out


def test_file_status_table() -> None:
    out = file_status_table(paths("2024-06-01", "2024-06-30"))

    assert {"file", "path", "exists"}.issubset(out.columns)


def test_kpis() -> None:
    out = kpis(make_eval())

    assert out["rows"] == 4
    assert out["signals"] == 2
    assert out["events"] == 2
    assert out["precision"] == 0.5


def test_timeline_frames() -> None:
    df = make_eval()

    assert "price_eur_per_mwh" in timeline_price(df).columns
    assert "risk_score" in timeline_risk(df).columns
    assert {"price_eur_per_mwh", "risk_score"}.issubset(timeline_combined(df).columns)


def test_bucket_counts() -> None:
    out = bucket_counts(make_eval())

    assert set(out["bucket"]) == {"TN", "TP", "FP", "FN"}


def test_reason_summary() -> None:
    out = reason_summary(make_eval())

    assert "A" in set(out["reason_code"])
    assert "B" in set(out["reason_code"])


def test_price_event_summary() -> None:
    out = price_event_summary(make_eval())

    assert "HIGH_PRICE_LEVEL" in set(out["price_event_label"])


def test_signal_cases() -> None:
    out = signal_cases(make_eval())

    assert len(out) == 2


def test_top_cases() -> None:
    out = top_cases(make_eval(), n=2)

    assert len(out) == 2
    assert out.iloc[0]["risk_score"] == 80


def test_monthly_frames() -> None:
    cross = make_cross()

    assert "event_lift" in monthly_lift_frame(cross).columns
    assert {"base_event_rate", "signal_event_rate"}.issubset(monthly_rate_frame(cross).columns)


def test_csv_bytes() -> None:
    data = csv_bytes(make_cross())

    assert isinstance(data, bytes)
    assert b"event_lift" in data
