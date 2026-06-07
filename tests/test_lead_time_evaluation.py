import pandas as pd

from src.prices.lead_time_evaluation import (
    exact_target,
    future_window_target,
    safe_div,
    score_target,
)


def make_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "signal_positive": [True, False, True, False, False],
            "event_positive": [False, True, False, True, False],
        }
    )


def test_safe_div() -> None:
    assert safe_div(2, 4) == 0.5
    assert safe_div(1, 0) is None


def test_exact_target_h1() -> None:
    work, target = exact_target(make_df(), 1)
    out = score_target(work, target)

    assert out["tp"] == 2
    assert out["precision"] == 1.0


def test_future_window_h1() -> None:
    work, target = future_window_target(make_df(), 1)
    out = score_target(work, target)

    assert out["tp"] == 2
    assert out["precision"] == 1.0


def test_future_window_h3() -> None:
    work, target = future_window_target(make_df(), 3)
    out = score_target(work, target)

    assert out["target_event_rows"] >= 1
