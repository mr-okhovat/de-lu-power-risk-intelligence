import pandas as pd

from src.reporting.reviewer_ready_v1 import aggregate, safe_div


def test_safe_div() -> None:
    assert safe_div(2, 4) == 0.5
    assert safe_div(1, 0) is None


def test_aggregate() -> None:
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

    out = aggregate(df)

    assert out["rows"] == 200
    assert out["signal_rows"] == 20
    assert out["all_months_lift_above_one"] is True
    assert round(out["aggregate_event_lift"], 2) > 1
