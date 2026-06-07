import pandas as pd

from src.reporting.visual_reviewer_pack import aggregate_metrics, figure_paths, safe_div


def test_safe_div() -> None:
    assert safe_div(2, 4) == 0.5
    assert safe_div(1, 0) is None


def test_aggregate_metrics() -> None:
    df = pd.DataFrame(
        {
            "rows": [100, 100],
            "signal_rows": [10, 10],
            "price_event_rows": [20, 20],
            "tp": [5, 4],
            "fp": [5, 6],
            "fn": [15, 16],
            "tn": [75, 74],
            "event_lift": [2.5, 2.0],
        }
    )

    out = aggregate_metrics(df)

    assert out["rows"] == 200
    assert out["signal_positive_hours"] == 20
    assert out["price_event_hours"] == 40
    assert round(out["aggregate_event_lift"], 2) > 1


def test_figure_paths() -> None:
    out = figure_paths("reports/figures")

    assert out["monthly_lift"].endswith("monthly_event_lift.png")
    assert out["june_timeline"].endswith("june_price_risk_timeline.png")
