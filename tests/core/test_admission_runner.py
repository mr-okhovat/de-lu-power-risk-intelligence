import pandas as pd

from src.pipeline.admission_runner import (
    admission_passes_for_pipeline,
    run_market_data_admission,
)


def test_runner_allows_healthy_dataset() -> None:
    frame = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2024-01-01 00:00",
                periods=24,
                freq="h",
                tz="UTC",
            )
        }
    )

    result = run_market_data_admission(
        frame,
        dataset_id="runner_accept",
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-01 23:00",
        as_of_utc="2024-01-02 00:00",
    )

    assert admission_passes_for_pipeline(result) is True


def test_runner_blocks_quarantined_dataset() -> None:
    frame = pd.DataFrame(
        {
            "timestamp_utc": [
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 10:00:00+00:00",
            ]
        }
    )

    result = run_market_data_admission(
        frame,
        dataset_id="runner_quarantine",
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-01 23:00",
        as_of_utc="2024-01-05 00:00",
    )

    assert admission_passes_for_pipeline(result) is False


def test_write_admission_report(tmp_path) -> None:
    frame = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2024-01-01 00:00",
                periods=24,
                freq="h",
                tz="UTC",
            )
        }
    )

    result = run_market_data_admission(
        frame,
        dataset_id="report_test",
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-01 23:00",
        as_of_utc="2024-01-02 00:00",
    )

    from src.pipeline.admission_runner import (
        write_admission_report,
    )

    output_path = write_admission_report(
        result,
        tmp_path / "admission_report.json",
    )

    report = output_path.read_text(
        encoding="utf-8"
    )

    assert output_path.exists()
    assert '"dataset_id": "report_test"' in report
    assert '"decision": "ACCEPT"' in report
    assert '"reliability_score": 100.0' in report
