import pandas as pd

from src.reporting.reviewer_ready_v2 import aggregate_price, lead_readout, lead_summary, safe_div


def test_safe_div() -> None:
    assert safe_div(2, 4) == 0.5
    assert safe_div(1, 0) is None


def test_aggregate_price() -> None:
    df = pd.DataFrame(
        {
            "month": ["A", "B"],
            "rows": [100, 100],
            "signal_rows": [10, 10],
            "price_event_rows": [20, 20],
            "tp": [5, 4],
            "fp": [5, 6],
            "fn": [15, 16],
            "tn": [75, 74],
            "precision": [0.5, 0.4],
            "recall": [0.25, 0.2],
            "event_lift": [2.5, 2.0],
        }
    )

    out = aggregate_price(df)

    assert out["rows"] == 200
    assert out["signal_rows"] == 20
    assert out["aggregate_event_lift"] > 1


def test_lead_summary_and_readout() -> None:
    df = pd.DataFrame(
        {
            "mode": ["exact_hour", "future_window"],
            "horizon_hours": [0, 3],
            "target_definition": ["event_at_t_plus_0", "any_event_next_3h"],
            "signal_rows": [10, 10],
            "target_event_rows": [20, 30],
            "tp": [5, 4],
            "fp": [5, 6],
            "fn": [15, 26],
            "tn": [75, 64],
            "precision": [0.5, 0.4],
            "recall": [0.25, 0.133],
            "event_lift": [2.0, 1.5],
        }
    )

    lead = lead_summary(df)

    assert lead["same_hour"] is not None
    assert lead["next_3h_window"] is not None
    assert "forward-window" in lead_readout(lead)
