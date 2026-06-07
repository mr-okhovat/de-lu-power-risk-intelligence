from src.data_ingestion.smard_filter_discovery import (
    FilterProbeResult,
    epoch_ms_to_utc_iso,
    render_markdown_report,
)


def test_epoch_ms_to_utc_iso() -> None:
    assert epoch_ms_to_utc_iso(0) == "1970-01-01T00:00:00+00:00"


def test_render_markdown_report_contains_ok_and_fail() -> None:
    results = [
        FilterProbeResult(
            filter_id="410",
            filter_name="Total Load",
            unit="MW",
            category="consumption",
            ok=True,
            index_url="https://example.com/ok",
            timestamp_count=10,
            first_chunk_utc="2024-01-01T00:00:00+00:00",
            last_chunk_utc="2024-02-01T00:00:00+00:00",
            error=None,
        ),
        FilterProbeResult(
            filter_id="9999",
            filter_name="Invalid Candidate",
            unit="MW",
            category="test",
            ok=False,
            index_url="https://example.com/fail",
            timestamp_count=0,
            first_chunk_utc=None,
            last_chunk_utc=None,
            error="404 Client Error",
        ),
    ]

    report = render_markdown_report(
        results=results,
        smard_region="DE",
        resolution="hour",
    )

    assert "# SMARD Filter Discovery Report" in report
    assert "| 410 | Total Load | consumption | MW | OK | 10 |" in report
    assert "| 9999 | Invalid Candidate | test | MW | FAIL | 0 |" in report
    assert "Failed Filters" in report
    assert "404 Client Error" in report
