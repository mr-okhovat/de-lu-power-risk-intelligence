from pathlib import Path

from src.core.project_orchestrator import (
    Stage,
    default_stages,
    missing_outputs,
    overall_status,
    run_stage,
)


def test_default_stages_without_screenshots() -> None:
    stages = default_stages(include_screenshots=False)
    names = [stage.name for stage in stages]

    assert names == [
        "tests",
        "dataset_registry",
        "intake_summary",
        "reviewer_ready_v2",
        "artifact_manifest",
    ]


def test_default_stages_with_screenshots() -> None:
    stages = default_stages(include_screenshots=True)
    names = [stage.name for stage in stages]

    assert names == [
        "tests",
        "dataset_registry",
        "intake_summary",
        "reviewer_ready_v2",
        "dashboard_screenshots",
        "artifact_manifest",
    ]


def test_manifest_runs_after_screenshots_when_enabled() -> None:
    stages = default_stages(include_screenshots=True)
    names = [stage.name for stage in stages]

    assert names.index("dashboard_screenshots") < names.index("artifact_manifest")


def test_missing_outputs(tmp_path: Path) -> None:
    existing = tmp_path / "exists.txt"
    existing.write_text("ok", encoding="utf-8")

    missing = missing_outputs([str(existing), str(tmp_path / "missing.txt")])

    assert missing == [str(tmp_path / "missing.txt")]


def test_run_stage_dry_run() -> None:
    stage = Stage(
        name="demo",
        command=["python", "--version"],
        required_outputs=["does_not_matter.txt"],
    )

    result = run_stage(stage, dry_run=True)

    assert result.status == "DRY RUN"
    assert result.return_code == 0


def test_overall_status() -> None:
    stage = Stage(name="demo", command=["python", "--version"], required_outputs=[])
    result = run_stage(stage, dry_run=True)

    assert overall_status([result]) == "PASS"
