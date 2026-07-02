import json

import pandas as pd

from src.data_quality.feature_release_gate import run_feature_release_gate


def make_valid_feature_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2024-06-01", periods=3, freq="h", tz="UTC")

    return pd.DataFrame(
        {
            "timestamp_utc": timestamps,
            "timestamp_local": timestamps.tz_convert("Europe/Berlin"),
            "market_label": ["DE-LU", "DE-LU", "DE-LU"],
            "smard_region": ["DE", "DE", "DE"],
            "total_load_mw": [100.0, 110.0, 120.0],
            "residual_load_official_mw": [70.0, 75.0, 80.0],
            "wind_onshore_validated_mw": [20.0, 25.0, 30.0],
            "solar_validated_mw": [5.0, 5.0, 5.0],
            "wind_offshore_validated_mw": [5.0, 5.0, 5.0],
            "missing_any_flag": [False, False, False],
            "wind_total_mw": [25.0, 30.0, 35.0],
            "renewable_generation_mw": [30.0, 35.0, 40.0],
            "residual_load_calculated_mw": [70.0, 75.0, 80.0],
            "residual_gap_mw": [0.0, 0.0, 0.0],
            "residual_gap_abs_mw": [0.0, 0.0, 0.0],
            "renewable_share": [0.30, 0.32, 0.33],
            "wind_share": [0.25, 0.27, 0.29],
            "solar_share": [0.05, 0.05, 0.04],
            "load_ramp_mw": [None, 10.0, 10.0],
            "residual_load_ramp_mw": [None, 5.0, 5.0],
            "renewable_generation_ramp_mw": [None, 5.0, 5.0],
            "local_date": ["2024-06-01", "2024-06-01", "2024-06-01"],
            "local_hour": [2, 3, 4],
            "local_weekday": ["Saturday", "Saturday", "Saturday"],
            "is_weekend": [True, True, True],
            "feature_schema_version": ["3A.1", "3A.1", "3A.1"],
        }
    )


def write_valid_bundle(tmp_path):
    feature_path = tmp_path / "hourly_features_DE-LU_2024-06-01.csv"
    metadata_path = tmp_path / "hourly_features_DE-LU_2024-06-01.metadata.json"

    make_valid_feature_frame().to_csv(feature_path, index=False)

    metadata_path.write_text(
        json.dumps(
            {
                "feature_output": str(feature_path),
                "feature_schema_version": "3A.1",
                "quality_result": {
                    "row_count": 3,
                    "status": "PASS",
                },
            }
        ),
        encoding="utf-8",
    )

    return feature_path, metadata_path


def test_valid_bundle_is_ready(tmp_path) -> None:
    feature_path, metadata_path = write_valid_bundle(tmp_path)

    result = run_feature_release_gate(
        feature_path,
        metadata_path=metadata_path,
    )

    assert result.status == "READY"
    assert result.hourly_continuity_breaks == 0
    assert result.residual_gap_pass is True
    assert result.blocking_reasons == []


def test_missing_ramp_after_first_observation_blocks_release(tmp_path) -> None:
    feature_path, metadata_path = write_valid_bundle(tmp_path)

    frame = pd.read_csv(feature_path)
    frame.loc[2, "load_ramp_mw"] = None
    frame.to_csv(feature_path, index=False)

    result = run_feature_release_gate(
        feature_path,
        metadata_path=metadata_path,
    )

    assert result.status == "BLOCKED"
    assert result.ramp_missing_outside_first_by_column["load_ramp_mw"] == 1


def test_share_outside_valid_range_blocks_release(tmp_path) -> None:
    feature_path, metadata_path = write_valid_bundle(tmp_path)

    frame = pd.read_csv(feature_path)
    frame.loc[1, "renewable_share"] = 1.2
    frame.to_csv(feature_path, index=False)

    result = run_feature_release_gate(
        feature_path,
        metadata_path=metadata_path,
    )

    assert result.status == "BLOCKED"
    assert result.share_range_violations["renewable_share"] == 1


def test_metadata_row_count_mismatch_blocks_release(tmp_path) -> None:
    feature_path, metadata_path = write_valid_bundle(tmp_path)

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["quality_result"]["row_count"] = 999
    metadata_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_feature_release_gate(
        feature_path,
        metadata_path=metadata_path,
    )

    assert result.status == "BLOCKED"
    assert result.metadata_checks["metadata_row_count_matches"] is False
