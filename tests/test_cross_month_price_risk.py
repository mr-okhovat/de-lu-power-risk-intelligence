import pandas as pd

from src.prices.cross_month_price_risk import f1, readout, safe_div


def test_safe_div() -> None:
    assert safe_div(2, 4) == 0.5
    assert safe_div(1, 0) is None


def test_f1() -> None:
    assert round(f1(0.5, 0.5), 3) == 0.5
    assert f1(None, 0.5) is None


def test_readout_positive_lift() -> None:
    summary = pd.DataFrame({"event_lift": [2.0, 1.6, 1.7]})

    assert "higher price-event concentration" in readout(summary)
