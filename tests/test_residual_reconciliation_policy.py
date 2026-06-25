from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from src.data_quality.residual_reconciliation_policy import (
    match_documented_residual_exceptions,
)


def write_registry(
    path: Path,
    *,
    exceptions: list[dict[str, object]],
) -> Path:
    payload = {
        "version": "test",
        "policy_id": "test-policy",
        "materiality_threshold_mw": 0.1,
        "match_tolerance_mw": 0.01,
        "exceptions": exceptions,
    }

    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )

    return path


def timestamps() -> pd.Series:
    return pd.Series(
        pd.date_range(
            "2021-01-04 00:00:00",
            periods=3,
            freq="h",
            tz="UTC",
        )
    )


def test_documented_exception_profile_matches(tmp_path: Path) -> None:
    registry_path = write_registry(
        tmp_path / "registry.yaml",
        exceptions=[
            {
                "timestamp_utc": "2021-01-04T01:00:00Z",
                "expected_signed_error_mw": 2.5,
            }
        ],
    )

    result = match_documented_residual_exceptions(
        timestamps(),
        [0.0, 2.5, 0.0],
        registry_path=registry_path,
    )

    assert result.pass_check is True
    assert result.observed_material_exception_count == 1
    assert result.expected_exception_count_in_window == 1
    assert result.unexpected_timestamp_count == 0
    assert result.signed_error_mismatch_count == 0
    assert result.missing_documented_exception_count == 0


def test_new_exception_timestamp_fails_policy(tmp_path: Path) -> None:
    registry_path = write_registry(
        tmp_path / "registry.yaml",
        exceptions=[
            {
                "timestamp_utc": "2021-01-04T01:00:00Z",
                "expected_signed_error_mw": 2.5,
            }
        ],
    )

    result = match_documented_residual_exceptions(
        timestamps(),
        [0.0, 0.0, 2.5],
        registry_path=registry_path,
    )

    assert result.pass_check is False
    assert result.unexpected_timestamp_count == 1
    assert result.missing_documented_exception_count == 1


def test_changed_signed_error_fails_policy(tmp_path: Path) -> None:
    registry_path = write_registry(
        tmp_path / "registry.yaml",
        exceptions=[
            {
                "timestamp_utc": "2021-01-04T01:00:00Z",
                "expected_signed_error_mw": 2.5,
            }
        ],
    )

    result = match_documented_residual_exceptions(
        timestamps(),
        [0.0, 2.75, 0.0],
        registry_path=registry_path,
    )

    assert result.pass_check is False
    assert result.signed_error_mismatch_count == 1


def test_missing_documented_exception_fails_policy(tmp_path: Path) -> None:
    registry_path = write_registry(
        tmp_path / "registry.yaml",
        exceptions=[
            {
                "timestamp_utc": "2021-01-04T01:00:00Z",
                "expected_signed_error_mw": 2.5,
            }
        ],
    )

    result = match_documented_residual_exceptions(
        timestamps(),
        [0.0, 0.0, 0.0],
        registry_path=registry_path,
    )

    assert result.pass_check is False
    assert result.missing_documented_exception_count == 1


def test_clean_window_passes_without_documented_exceptions(tmp_path: Path) -> None:
    registry_path = write_registry(
        tmp_path / "registry.yaml",
        exceptions=[],
    )

    result = match_documented_residual_exceptions(
        timestamps(),
        [0.0, 0.05, -0.05],
        registry_path=registry_path,
    )

    assert result.pass_check is True
    assert result.observed_material_exception_count == 0
    assert result.expected_exception_count_in_window == 0


def test_clean_window_outside_documented_period_passes(tmp_path: Path) -> None:
    registry_path = write_registry(
        tmp_path / "registry.yaml",
        exceptions=[
            {
                "timestamp_utc": "2021-01-04T01:00:00Z",
                "expected_signed_error_mw": 2.5,
            }
        ],
    )

    later_timestamps = pd.Series(
        pd.date_range(
            "2021-01-05 00:00:00",
            periods=3,
            freq="h",
            tz="UTC",
        )
    )

    result = match_documented_residual_exceptions(
        later_timestamps,
        [0.0, 0.0, 0.0],
        registry_path=registry_path,
    )

    assert result.pass_check is True
    assert result.observed_material_exception_count == 0
    assert result.expected_exception_count_in_window == 0
