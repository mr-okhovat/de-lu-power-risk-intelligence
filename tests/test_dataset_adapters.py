import pandas as pd

from src.core.dataset_adapters import adapt_frame, to_bool


def adapter() -> dict:
    return {
        "name": "test_adapter",
        "version": "x",
        "sort_by": "timestamp_utc",
        "fields": [
            {"source": "time", "target": "timestamp_utc", "dtype": "datetime", "required": True},
            {"source": "price", "target": "price_eur_per_mwh", "dtype": "numeric", "required": True},
            {"source": "score", "target": "risk_score", "dtype": "numeric", "required": True},
            {"source": "signal", "target": "signal_positive", "dtype": "boolean", "required": True},
            {"constant": "ADAPTED", "target": "source_label", "dtype": "string", "required": False},
        ],
    }


def test_to_bool() -> None:
    assert to_bool("true") is True
    assert to_bool("0") is False
    assert pd.isna(to_bool("maybe"))


def test_adapt_frame_passes() -> None:
    df = pd.DataFrame(
        {
            "time": ["2024-06-01T01:00:00Z", "2024-06-01T00:00:00Z"],
            "price": ["50.5", "40.0"],
            "score": [10, 20],
            "signal": ["false", "true"],
        }
    )

    out, result = adapt_frame(df, adapter())

    assert result.status == "PASS"
    assert list(out.columns) == [
        "timestamp_utc",
        "price_eur_per_mwh",
        "risk_score",
        "signal_positive",
        "source_label",
    ]
    assert out.iloc[0]["price_eur_per_mwh"] == 40.0


def test_adapt_frame_finds_missing_required_source() -> None:
    df = pd.DataFrame(
        {
            "time": ["2024-06-01T00:00:00Z"],
            "price": [40.0],
            "signal": [True],
        }
    )

    _, result = adapt_frame(df, adapter())

    assert result.status == "CHECK NEEDED"
    assert "score" in result.missing_source_columns


def test_adapt_frame_finds_conversion_error() -> None:
    df = pd.DataFrame(
        {
            "time": ["bad-date"],
            "price": ["x"],
            "score": [20],
            "signal": ["maybe"],
        }
    )

    _, result = adapt_frame(df, adapter())

    assert result.status == "CHECK NEEDED"
    assert result.conversion_errors["timestamp_utc"] == 1
    assert result.conversion_errors["price_eur_per_mwh"] == 1
    assert result.conversion_errors["signal_positive"] == 1
