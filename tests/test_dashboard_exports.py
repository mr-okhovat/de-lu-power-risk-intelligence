import pandas as pd

from src.reporting.dashboard_exports import (
    DASHBOARD_SCHEMA_VERSION,
    build_feature_dictionary,
    build_market_overview_export,
    validate_dashboard_export,
)


def make_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": ["2024-06-01 00:00:00+00:00"],
            "timestamp_local": ["2024-06-01 02:00:00+02:00"],
            "market_label": ["DE-LU"],
            "smard_region": ["DE"],
            "total_load_mw": [100.0],
            "residual_load_official_mw": [70.0],
            "wind_onshore_validated_mw": [20.0],
            "wind_offshore_validated_mw": [5.0],
            "solar_validated_mw": [5.0],
            "wind_total_mw": [25.0],
            "renewable_generation_mw": [30.0],
            "renewable_share": [0.3],
            "wind_share": [0.25],
            "solar_share": [0.05],
            "load_ramp_mw": [None],
            "residual_load_ramp_mw": [None],
            "renewable_generation_ramp_mw": [None],
            "local_date": ["2024-06-01"],
            "local_hour": [2],
            "local_weekday": ["Saturday"],
            "is_weekend": [True],
            "feature_schema_version": ["3A.1"],
        }
    )


def test_build_market_overview_export_adds_schema_version() -> None:
    export = build_market_overview_export(make_feature_frame())

    assert "dashboard_schema_version" in export.columns
    assert export["dashboard_schema_version"].iloc[0] == DASHBOARD_SCHEMA_VERSION


def test_build_feature_dictionary_has_required_columns() -> None:
    dictionary = build_feature_dictionary()

    assert {"column_name", "unit_or_type", "description", "dashboard_schema_version"} <= set(dictionary.columns)
    assert "total_load_mw" in set(dictionary["column_name"])


def test_validate_dashboard_export_passes() -> None:
    export = build_market_overview_export(make_feature_frame())

    result = validate_dashboard_export(export)

    assert result.status == "PASS"
    assert result.row_count == 1
    assert result.duplicate_timestamp_count == 0
