from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


VERSION = "15B.1"


@dataclass(frozen=True)
class Stage:
    name: str
    command: list[str]
    required_outputs: list[str]


@dataclass(frozen=True)
class StageResult:
    name: str
    status: str
    command: list[str]
    required_outputs: list[str]
    missing_outputs: list[str]
    return_code: int


def default_stages(*, include_screenshots: bool = False) -> list[Stage]:
    stages = [
        Stage(
            name="tests",
            command=["python", "-m", "pytest"],
            required_outputs=[],
        ),
        Stage(
            name="dataset_registry",
            command=["bash", "scripts/run_dataset_adapter_registry.sh"],
            required_outputs=[
                "reports/dataset_adapter_registry_run.md",
                "reports/dataset_adapter_registry_run.json",
            ],
        ),
        Stage(
            name="intake_summary",
            command=["bash", "scripts/build_intake_summary.sh"],
            required_outputs=[
                "reports/dataset_intake_summary.md",
                "reports/dataset_intake_summary.json",
                "dashboards/dataset_intake_summary.csv",
            ],
        ),
        Stage(
            name="data_availability_index",
            command=["bash", "scripts/build_data_availability_index.sh"],
            required_outputs=[
                "reports/data_availability_index.md",
                "reports/data_availability_index.json",
                "dashboards/data_availability_index.csv",
            ],
        ),
        Stage(
            name="run_catalog",
            command=["bash", "scripts/build_run_catalog.sh"],
            required_outputs=[
                "reports/market_month_run_catalog.md",
                "reports/market_month_run_catalog.json",
                "dashboards/market_month_run_catalog.csv",
            ],
        ),
        Stage(
            name="reviewer_ready_v2",
            command=[
                "python",
                "-m",
                "src.reporting.reviewer_ready_v2",
                "--price-csv",
                "dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv",
                "--lead-csv",
                "dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv",
                "--output-report",
                "reports/reviewer_ready_v2.md",
                "--output-json",
                "reports/reviewer_ready_v2.json",
                "--metrics-csv",
                "dashboards/reviewer_ready_v2_metrics.csv",
                "--update-readme",
            ],
            required_outputs=[
                "reports/reviewer_ready_v2.md",
                "reports/reviewer_ready_v2.json",
                "dashboards/reviewer_ready_v2_metrics.csv",
            ],
        ),
    ]

    if include_screenshots:
        stages.append(
            Stage(
                name="dashboard_screenshots",
                command=["python", "scripts/capture_dashboard_screenshots.py"],
                required_outputs=[
                    "reports/figures/dashboard/dashboard_overview.png",
                    "reports/figures/dashboard/dashboard_selected_month.png",
                    "reports/figures/dashboard/dashboard_diagnostics.png",
                    "reports/figures/dashboard/dashboard_lead_time.png",
                    "reports/figures/dashboard/dashboard_dataset_intake.png",
                    "reports/figures/dashboard/dashboard_reviewer_files.png",
                ],
            )
        )

    stages.append(
        Stage(
            name="artifact_manifest",
            command=["bash", "scripts/build_artifact_manifest.sh"],
            required_outputs=[
                "reports/project_artifact_manifest.md",
                "reports/project_artifact_manifest.json",
                "dashboards/project_artifact_manifest.csv",
            ],
        )
    )

    return stages


def missing_outputs(paths: list[str]) -> list[str]:
    return [path for path in paths if not Path(path).exists()]


def run_stage(stage: Stage, *, dry_run: bool = False) -> StageResult:
    if dry_run:
        return StageResult(
            name=stage.name,
            status="DRY RUN",
            command=stage.command,
            required_outputs=stage.required_outputs,
            missing_outputs=[],
            return_code=0,
        )

    completed = subprocess.run(stage.command, check=False)
    missing = missing_outputs(stage.required_outputs)

    status = "PASS" if completed.returncode == 0 and not missing else "FAIL"

    return StageResult(
        name=stage.name,
        status=status,
        command=stage.command,
        required_outputs=stage.required_outputs,
        missing_outputs=missing,
        return_code=int(completed.returncode),
    )


def overall_status(results: list[StageResult]) -> str:
    if not results:
        return "FAIL"

    if all(result.status in {"PASS", "DRY RUN"} for result in results):
        return "PASS"

    return "FAIL"


def report_text(results: list[StageResult], *, include_screenshots: bool, dry_run: bool) -> str:
    status = overall_status(results)
    now = datetime.now(timezone.utc).isoformat()

    lines = [
        "# Project checkpoint run",
        "",
        f"Version: `{VERSION}`",
        f"Timestamp UTC: `{now}`",
        f"Status: `{status}`",
        f"Dry run: `{dry_run}`",
        f"Dashboard screenshots included: `{include_screenshots}`",
        "",
        "## Stages",
        "",
        "| stage | status | return code | missing outputs |",
        "|---|---|---:|---|",
    ]

    for result in results:
        missing = ", ".join(result.missing_outputs)
        lines.append(
            f"| {result.name} | {result.status} | {result.return_code} | {missing} |"
        )

    lines += [
        "",
        "## Readout",
        "",
    ]

    if status == "PASS":
        lines.append("The project checkpoint rebuilt successfully.")
    else:
        lines.append("One or more checkpoint stages failed. Fix the failed stage before adding new analytics.")

    lines += [
        "",
        "This command is an orchestration layer. It does not change analytics logic by itself.",
        "",
    ]

    return "\n".join(lines)


def write_outputs(
    results: list[StageResult],
    *,
    output_report: str,
    output_json: str,
    include_screenshots: bool,
    dry_run: bool,
) -> None:
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    Path(output_report).write_text(
        report_text(results, include_screenshots=include_screenshots, dry_run=dry_run),
        encoding="utf-8",
    )

    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "status": overall_status(results),
                "include_screenshots": include_screenshots,
                "dry_run": dry_run,
                "results": [asdict(result) for result in results],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def run_checkpoint(
    *,
    include_screenshots: bool,
    dry_run: bool,
    output_report: str,
    output_json: str,
) -> list[StageResult]:
    results = []

    for stage in default_stages(include_screenshots=include_screenshots):
        print(f"RUN | {stage.name}")
        result = run_stage(stage, dry_run=dry_run)
        results.append(result)

        print(f"{result.status} | {stage.name}")

        if result.status == "FAIL":
            break

    write_outputs(
        results,
        output_report=output_report,
        output_json=output_json,
        include_screenshots=include_screenshots,
        dry_run=dry_run,
    )

    if overall_status(results) != "PASS":
        raise SystemExit(1)

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-screenshots", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--output-report",
        default="reports/project_checkpoint_run.md",
    )
    parser.add_argument(
        "--output-json",
        default="reports/project_checkpoint_run.json",
    )
    args = parser.parse_args()

    run_checkpoint(
        include_screenshots=args.include_screenshots,
        dry_run=args.dry_run,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
