import pandas as pd

from src.features.market_features import (
    engineer_market_features,
    safe_divide,
    validate_feature_frame,
)


def make_staging_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-06-01", periods=3, freq="h", tz="UTC"),
            "timestamp_local": pd.date_range("2024-06-01 02:00", periods=3, freq="h", tz="Europe/Berlin"),
            "market_label": ["DE-LU", "DE-LU", "DE-LU"],
            "smard_region": ["DE", "DE", "DE"],
            "total_load_mw": [100.0, 120.0, 110.0],
            "residual_load_official_mw": [70.0, 80.0, 75.0],
            "wind_onshore_validated_mw": [20.0, 25.0, 20.0],
            "solar_validated_mw": [5.0, 10.0, 10.0],
            "wind_offshore_validated_mw": [5.0, 5.0, 5.0],
            "missing_any_flag": [False, False, False],
        }
    )


def test_safe_divide_handles_zero_denominator() -> None:
    numerator = pd.Series([1.0, 2.0])
    denominator = pd.Series([1.0, 0.0])

    result = safe_divide(numerator, denominator)

    assert result.iloc[0] == 1.0
    assert pd.isna(result.iloc[1])


def test_engineer_market_features_core_formulas() -> None:
    df = engineer_market_features(make_staging_frame())

    assert "renewable_generation_mw" in df.columns
    assert "residual_gap_mw" in df.columns

    assert df["wind_total_mw"].tolist() == [25.0, 30.0, 25.0]
    assert df["renewable_generation_mw"].tolist() == [30.0, 40.0, 35.0]
    assert df["residual_load_calculated_mw"].tolist() == [70.0, 80.0, 75.0]
    assert df["residual_gap_mw"].tolist() == [0.0, 0.0, 0.0]


def test_engineer_market_features_ramps() -> None:
    df = engineer_market_features(make_staging_frame())

    assert pd.isna(df["load_ramp_mw"].iloc[0])
    assert df["load_ramp_mw"].iloc[1] == 20.0
    assert df["load_ramp_mw"].iloc[2] == -10.0


def test_validate_feature_frame_passes() -> None:
    features = engineer_market_features(make_staging_frame())

    result = validate_feature_frame(features)

    assert result.status == "PASS"
    assert result.row_count == 3
    assert result.residual_gap_pass is True
    assert result.ramp_missing_by_column["load_ramp_mw"] == 1
