import pandas as pd

from src.reporting.cross_month_behavior import readout, split_reasons, summarize_month, top_reason


def test_split_reasons() -> None:
    assert split_reasons("A|B") == ["A", "B"]
    assert split_reasons("") == []


def test_top_reason_ignores_no_rule() -> None:
    df = pd.DataFrame({"reason_codes": ["NO_RULE_TRIGGERED", "A|B", "A"]})

    assert top_reason(df) == "A"


def test_summarize_month() -> None:
    df = pd.DataFrame(
        {
            "risk_score": [0, 30, 60, 85],
            "regime_label": ["NORMAL", "WATCH", "STRESSED", "EXTREME"],
            "reason_codes": ["NO_RULE_TRIGGERED", "A", "B", "B"],
        }
    )

    out = summarize_month("Test", "2024-01-01", "2024-01-31", "x.csv", df)

    assert out["rows"] == 4
    assert out["high_risk_rows"] == 2
    assert out["extreme_rows"] == 1


def test_readout() -> None:
    summary = pd.DataFrame(
        {
            "high_risk_share": [0.01, 0.02],
            "max_risk_score": [60, 85],
        }
    )

    assert "unchanged" in readout(summary) or "controlled" in readout(summary)
