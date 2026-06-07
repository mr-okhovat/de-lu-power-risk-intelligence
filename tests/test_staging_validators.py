import pandas as pd

from src.data_quality.staging_validators import (
    render_quality_report,
    validate_staging_frame,
)


def test_validate_staging_frame_pass() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-01-01", periods=2, freq="h", tz="UTC"),
            "total_load_mw": [10.0, 20.0],
        }
    )

    result = validate_staging_frame(
        df,
        value_columns=["total_load_mw"],
        positive_only_columns=["total_load_mw"],
        provisional_columns=[],
    )

    assert result.status == "PASS"
    assert result.row_count == 2
    assert result.missing_by_column["total_load_mw"] == 0


def test_validate_staging_frame_with_provisional_column_is_limited() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-01-01", periods=2, freq="h", tz="UTC"),
            "wind_candidate_mw": [10.0, 20.0],
        }
    )

    result = validate_staging_frame(
        df,
        value_columns=["wind_candidate_mw"],
        positive_only_columns=["wind_candidate_mw"],
        provisional_columns=["wind_candidate_mw"],
    )

    assert result.status == "PASS WITH LIMITATION"


def test_render_quality_report() -> None:
    df = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-01-01", periods=2, freq="h", tz="UTC"),
            "total_load_mw": [10.0, 20.0],
        }
    )

    result = validate_staging_frame(
        df,
        value_columns=["total_load_mw"],
        positive_only_columns=["total_load_mw"],
        provisional_columns=[],
    )

    report = render_quality_report(
        result=result,
        market_label="DE-LU",
        smard_region="DE",
        start="2024-01-01",
        end="2024-01-01",
        value_columns=["total_load_mw"],
        provisional_columns=[],
    )

    assert "# Data Quality Report" in report
    assert "DE-LU" in report
    assert "PASS" in report
