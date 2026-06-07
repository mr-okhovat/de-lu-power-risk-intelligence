import pandas as pd

from src.reporting.risk_behavior_review import hourly_profile, reason_counts, split_reasons


def test_split_reasons() -> None:
    assert split_reasons("A|B") == ["A", "B"]
    assert split_reasons("") == []


def test_reason_counts() -> None:
    df = pd.DataFrame({"reason_codes": ["A|B", "A", "NO_RULE_TRIGGERED"]})
    out = reason_counts(df)

    assert "A" in set(out["reason_code"])
    assert int(out[out["reason_code"] == "A"]["count"].iloc[0]) == 2


def test_hourly_profile() -> None:
    df = pd.DataFrame(
        {
            "timestamp_local": pd.date_range("2024-06-01", periods=3, freq="h", tz="Europe/Berlin"),
            "risk_score": [0, 60, 90],
        }
    )

    out = hourly_profile(df)

    assert "high_risk_share" in out.columns
    assert int(out["high_risk_rows"].sum()) == 2
