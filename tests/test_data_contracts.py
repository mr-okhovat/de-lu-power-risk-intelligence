import pandas as pd

from src.core.data_contracts import validate_frame


def contract() -> dict:
    return {
        "name": "test_contract",
        "version": "x",
        "primary_key": ["timestamp_utc"],
        "fields": [
            {"name": "timestamp_utc", "dtype": "datetime", "required": True, "nullable": False},
            {"name": "value", "dtype": "numeric", "required": True, "nullable": False, "min_value": 0},
            {"name": "flag", "dtype": "boolean", "required": True, "nullable": False},
            {"name": "bucket", "dtype": "string", "required": True, "nullable": False, "allowed_values": ["A", "B"]},
        ],
    }


def test_validate_frame_passes() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": ["2024-06-01T00:00:00Z", "2024-06-01T01:00:00Z"],
            "value": [1.0, 2.0],
            "flag": [True, False],
            "bucket": ["A", "B"],
        }
    )

    result = validate_frame(df, contract(), "memory.csv")

    assert result.status == "PASS"


def test_validate_frame_finds_missing_column() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": ["2024-06-01T00:00:00Z"],
            "value": [1.0],
            "flag": [True],
        }
    )

    result = validate_frame(df, contract(), "memory.csv")

    assert result.status == "CHECK NEEDED"
    assert "bucket" in result.missing_required_columns


def test_validate_frame_finds_bad_values() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": ["bad-date"],
            "value": [-1.0],
            "flag": ["maybe"],
            "bucket": ["C"],
        }
    )

    result = validate_frame(df, contract(), "memory.csv")

    assert result.status == "CHECK NEEDED"
    assert result.dtype_violations["timestamp_utc"] == 1
    assert result.dtype_violations["flag"] == 1
    assert result.range_violations["value"] == 1
    assert result.allowed_value_violations["bucket"] == 1


def test_validate_frame_finds_duplicate_key() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": ["2024-06-01T00:00:00Z", "2024-06-01T00:00:00Z"],
            "value": [1.0, 2.0],
            "flag": [True, False],
            "bucket": ["A", "B"],
        }
    )

    result = validate_frame(df, contract(), "memory.csv")

    assert result.status == "CHECK NEEDED"
    assert result.duplicate_key_rows == 1
