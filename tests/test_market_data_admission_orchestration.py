from src.orchestration import run_all
from src.orchestration.pipeline_steps import (
    PipelineConfig,
    PipelineStep,
)


def test_pipeline_stops_after_failed_market_data_admission(
    monkeypatch,
):
    config = PipelineConfig(
        name="admission-test",
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

    steps = [
        PipelineStep(
            "build_features",
            ["python", "build_features.py"],
            "Build features.",
        ),
        PipelineStep(
            "market_data_admission",
            ["python", "admission.py"],
            "Evaluate admission.",
        ),
        PipelineStep(
            "build_dashboard_exports",
            ["python", "dashboard.py"],
            "Build dashboard.",
        ),
        PipelineStep(
            "build_risk_signals",
            ["python", "risk.py"],
            "Build risk signals.",
        ),
    ]

    executed = []
    summaries = []

    monkeypatch.setattr(
        run_all,
        "load_pipeline_config",
        lambda _: config,
    )
    monkeypatch.setattr(
        run_all,
        "build_pipeline_steps",
        lambda _: steps,
    )

    def fake_run_step(step, dry_run):
        executed.append(step.name)

        failed = step.name == "market_data_admission"

        return {
            "name": step.name,
            "status": "FAIL" if failed else "PASS",
            "command": step.command,
            "started_at_utc": "2024-08-03T00:00:00+00:00",
            "finished_at_utc": "2024-08-03T00:00:01+00:00",
            "duration_seconds": 1.0,
            "return_code": 1 if failed else 0,
        }

    monkeypatch.setattr(
        run_all,
        "run_step",
        fake_run_step,
    )
    monkeypatch.setattr(
        run_all,
        "write_summary",
        lambda cfg, results, status: summaries.append(
            {
                "status": status,
                "steps": [item["name"] for item in results],
            }
        ),
    )

    return_code = run_all.run_pipeline(
        "unused.yaml",
        dry_run=False,
    )

    assert return_code == 1
    assert executed == [
        "build_features",
        "market_data_admission",
    ]
    assert "build_dashboard_exports" not in executed
    assert "build_risk_signals" not in executed
    assert summaries == [
        {
            "status": "FAIL",
            "steps": [
                "build_features",
                "market_data_admission",
            ],
        }
    ]
