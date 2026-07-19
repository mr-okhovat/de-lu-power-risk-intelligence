import json

import pytest

from src.orchestration import run_all
from src.orchestration.pipeline_steps import PipelineConfig


def make_config() -> PipelineConfig:
    return PipelineConfig(
        name="summary-test",
        run_label="test-run",
        start="2024-08-01",
        end="2024-08-02",
        market_label="DE-LU",
        smard_region="DE",
        resolution="hour",
        filters=[],
        min_history=24,
        signal_positive_threshold=0.0,
        high_quantile=0.95,
        low_quantile=0.05,
        run_tests_first=False,
        run_tests_last=False,
        include_reviewer_pack=False,
        include_event_study=False,
        include_signal_event_evaluation=False,
    )


def test_write_summary_includes_market_data_admission(
    tmp_path,
    monkeypatch,
) -> None:
    paths = {
        "market_data_admission_json": str(tmp_path / "admission.json"),
        "run_summary": str(tmp_path / "summary.md"),
        "run_summary_json": str(tmp_path / "summary.json"),
    }
    monkeypatch.setattr(run_all, "output_paths", lambda _: paths)

    admission = {
        "dataset_id": "hourly_features_DE-LU",
        "decision": "ACCEPT",
        "reliability_score": 100.0,
    }
    (tmp_path / "admission.json").write_text(
        json.dumps(admission),
        encoding="utf-8",
    )

    results = [
        {
            "name": "market_data_admission",
            "status": "PASS",
            "duration_seconds": 0.5,
        }
    ]

    run_all.write_summary(make_config(), results, "PASS")

    markdown = (tmp_path / "summary.md").read_text(encoding="utf-8")
    summary_json = json.loads(
        (tmp_path / "summary.json").read_text(encoding="utf-8")
    )

    assert "## Market data admission" in markdown
    assert "- Decision: ACCEPT" in markdown
    assert "- Reliability score: 100.0" in markdown
    assert "- Dataset: hourly_features_DE-LU" in markdown
    assert summary_json["market_data_admission"] == admission


@pytest.mark.parametrize(
    "report_content",
    [None, "{broken-json"],
)
def test_summary_survives_unavailable_admission_report(
    tmp_path,
    monkeypatch,
    report_content,
) -> None:
    paths = {
        "market_data_admission_json": str(tmp_path / "admission.json"),
        "run_summary": str(tmp_path / "summary.md"),
        "run_summary_json": str(tmp_path / "summary.json"),
    }
    monkeypatch.setattr(run_all, "output_paths", lambda _: paths)

    if report_content is not None:
        (tmp_path / "admission.json").write_text(
            report_content,
            encoding="utf-8",
        )

    results = [
        {
            "name": "market_data_admission",
            "status": "FAIL",
            "duration_seconds": 0.5,
        }
    ]

    run_all.write_summary(make_config(), results, "FAIL")

    markdown = (tmp_path / "summary.md").read_text(encoding="utf-8")
    summary_json = json.loads(
        (tmp_path / "summary.json").read_text(encoding="utf-8")
    )

    assert "- Result: unavailable" in markdown
    assert summary_json["market_data_admission"] is None
