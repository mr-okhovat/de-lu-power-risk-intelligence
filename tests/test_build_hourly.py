import json
from pathlib import Path

import pandas as pd

from src.staging.build_hourly import (
    build_expected_hourly_index,
    extract_series_points,
    load_smard_series_from_raw,
)
from src.config.load_series_registry import SeriesDefinition


def test_extract_series_points_from_list_payload() -> None:
    payload = {"series": [[1717192800000, 10.5], [1717196400000, None]]}

    assert extract_series_points(payload) == [
        (1717192800000, 10.5),
        (1717196400000, None),
    ]


def test_extract_series_points_from_dict_payload() -> None:
    payload = {
        "series": [
            {"timestamp": 1717192800000, "value": 10.5},
            {"timestamp": 1717196400000, "value": None},
        ]
    }

    assert extract_series_points(payload) == [
        (1717192800000, 10.5),
        (1717196400000, None),
    ]


def test_build_expected_hourly_index() -> None:
    df = build_expected_hourly_index(start="2024-06-01", end="2024-06-01")

    assert len(df) == 24
    assert str(df["timestamp_utc"].iloc[0]).endswith("+00:00")


def test_load_smard_series_from_raw(tmp_path: Path) -> None:
    raw_dir = tmp_path / "410"
    raw_dir.mkdir(parents=True)

    payload = {
        "series": [
            [1717192800000, 100.0],
            [1717196400000, 200.0],
        ]
    }

    raw_file = raw_dir / "smard_410_DE_hour_1717192800000.json"
    raw_file.write_text(json.dumps(payload), encoding="utf-8")

    series_definition = SeriesDefinition(
        filter_id="410",
        internal_name="total_load",
        display_name="Total Load",
        source="SMARD",
        source_region_field="smard_region",
        default_smard_region="DE",
        market_label="DE-LU",
        unit="MW",
        category="consumption",
        semantic_status="endpoint_verified_semantics_locked",
        allowed_for_staging=True,
        allowed_for_final_features=True,
        expected_direction="positive",
        notes="test",
    )

    df = load_smard_series_from_raw(
        raw_root=tmp_path,
        series_definition=series_definition,
        smard_region="DE",
        resolution="hour",
        start_ms=1717192800000,
        end_ms_exclusive=1717200000000,
    )

    assert len(df) == 2
    assert "total_load_mw" in df.columns
    assert float(df["total_load_mw"].sum()) == 300.0
