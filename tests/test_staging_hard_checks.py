import pandas as pd

from src.data_quality.staging_hard_checks import (
    count_hourly_continuity_breaks,
    reconcile_residual_load,
    run_staging_hard_checks,
)


def make_valid_staging_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_utc": pd.date_range("2024-06-01", periods=3, freq="h", tz="UTC"),
            "timestamp_local": pd.date_range("2024-06-01 02:00", periods=3, freq="h", tz="Europe/Berlin"),
            "market_label": ["DE-LU", "DE-LU", "DE-LU"],
            "smard_region": ["DE", "DE", "DE"],
            "total_load_mw": [100.0, 110.0, 120.0],
            "residual_load_official_mw": [70.0, 75.0, 80.0],
            "wind_candidate_mw": [20.0, 25.0, 30.0],
            "solar_candidate_mw": [5.0, 5.0, 5.0],
            "wind_offshore_candidate_mw": [5.0, 5.0, 5.0],
            "missing_any_flag": [False, False, False],
        }
    )


def test_count_hourly_continuity_breaks_zero() -> None:
    df = make_valid_staging_frame()

    assert count_hourly_continuity_breaks(df) == 0


def test_count_hourly_continuity_breaks_detects_gap() -> None:
    df = make_valid_staging_frame()
    df.loc[2, "timestamp_utc"] = pd.Timestamp("2024-06-01 04:00:00", tz="UTC")

    assert count_hourly_continuity_breaks(df) == 1


def test_reconcile_residual_load_passes() -> None:
    df = make_valid_staging_frame()

    result = reconcile_residual_load(df, tolerance_mw=1.0)

    assert result.checked is True
    assert result.pass_check is True
    assert result.max_abs_error_mw == 0.0


def test_reconcile_residual_load_fails() -> None:
    df = make_valid_staging_frame()
    df.loc[0, "residual_load_official_mw"] = 999.0

    result = reconcile_residual_load(df, tolerance_mw=1.0)

    assert result.checked is True
    assert result.pass_check is False


def test_run_staging_hard_checks_pass_with_limitation(tmp_path) -> None:
    df = make_valid_staging_frame()
    staging_file = tmp_path / "staging.csv"
    df.to_csv(staging_file, index=False)

    result = run_staging_hard_checks(staging_file)

    assert result.status == "PASS WITH LIMITATION"
    assert result.row_count == 3
    assert result.duplicate_timestamp_count == 0
    assert result.hourly_continuity_breaks == 0
    assert result.residual_reconciliation.pass_check is True
