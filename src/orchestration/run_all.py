from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.orchestration.pipeline_steps import (
    PipelineConfig,
    PipelineStep,
    build_pipeline_steps,
    load_pipeline_config,
    output_paths,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def render_command(command: list[str]) -> str:
    return " ".join(command)


def run_step(step: PipelineStep, *, dry_run: bool = False) -> dict[str, object]:
    started_at = utc_now_iso()
    start_time = time.monotonic()

    print(f"\n=== RUNNING: {step.name} ===")
    print(step.description)
    print(render_command(step.command))

    if dry_run:
        return {
            "name": step.name,
            "description": step.description,
            "command": step.command,
            "status": "DRY_RUN",
            "started_at_utc": started_at,
            "finished_at_utc": utc_now_iso(),
            "duration_seconds": 0.0,
            "return_code": 0,
        }

    completed = subprocess.run(step.command, check=False)
    duration = time.monotonic() - start_time
    finished_at = utc_now_iso()

    status = "PASS" if completed.returncode == 0 else "FAIL"

    return {
        "name": step.name,
        "description": step.description,
        "command": step.command,
        "status": status,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "duration_seconds": round(duration, 3),
        "return_code": completed.returncode,
    }


def render_pipeline_summary(
    *,
    config: PipelineConfig,
    step_results: list[dict[str, object]],
    status: str,
    paths: dict[str, str],
    dry_run: bool,
) -> str:
    lines: list[str] = [
        "# Pipeline Run Summary",
        "",
        f"- Pipeline: `{config.name}`",
        f"- Run label: `{config.run_label}`",
        f"- Status: `{status}`",
        f"- Dry run: `{dry_run}`",
        f"- Start date: `{config.start}`",
        f"- End date: `{config.end}`",
        f"- Market label: `{config.market_label}`",
        f"- SMARD region: `{config.smard_region}`",
        f"- Resolution: `{config.resolution}`",
        f"- Filters: `{config.filters}`",
        "",
        "## Step Results",
        "",
        "| Step | Status | Duration seconds |",
        "|---|---:|---:|",
    ]

    for result in step_results:
        lines.append(
            f"| {result['name']} | {result['status']} | {result['duration_seconds']} |"
        )

    lines.extend(["", "## Key Outputs", ""])

    key_outputs = [
        "staging",
        "features",
        "dashboard_market_overview",
        "risk_signals",
        "risk_diagnostics_report",
        "event_labels",
        "signal_event_evaluation",
        "signal_event_report",
    ]

    for key in key_outputs:
        lines.append(f"- `{key}`: `{paths[key]}`")

    lines.extend(
        [
            "",
            "## Methodological Boundary",
            "",
            "This automated run reproduces the current public-data analytics pipeline. It does not create a trading strategy, execution logic, or P&L claim.",
            "",
        ]
    )

    return "\n".join(lines)


def write_summary_outputs(
    *,
    config: PipelineConfig,
    step_results: list[dict[str, object]],
    status: str,
    dry_run: bool,
) -> None:
    paths = output_paths(config)

    summary_md = Path(paths["run_summary"])
    summary_json = Path(paths["run_summary_json"])

    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)

    summary_md.write_text(
        render_pipeline_summary(
            config=config,
            step_results=step_results,
            status=status,
            paths=paths,
            dry_run=dry_run,
        ),
        encoding="utf-8",
    )

    summary_json.write_text(
        json.dumps(
            {
                "config": asdict(config),
                "status": status,
                "dry_run": dry_run,
                "step_results": step_results,
                "outputs": paths,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def run_pipeline(config_path: str | Path, *, dry_run: bool = False) -> int:
    config = load_pipeline_config(config_path)
    steps = build_pipeline_steps(config)

    step_results: list[dict[str, object]] = []

    final_status = "PASS"

    for step in steps:
        result = run_step(step, dry_run=dry_run)
        step_results.append(result)

        if result["status"] == "FAIL":
            final_status = "FAIL"
            write_summary_outputs(
                config=config,
                step_results=step_results,
                status=final_status,
                dry_run=dry_run,
            )
            print(f"\nPIPELINE FAILED at step: {step.name}")
            return 1

    write_summary_outputs(
        config=config,
        step_results=step_results,
        status=final_status,
        dry_run=dry_run,
    )

    print("\nPIPELINE PASS")
    print(f"Summary: {output_paths(config)['run_summary']}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full DE-LU Power Risk Intelligence pipeline.")

    parser.add_argument("--config", default="config/pipeline_sample.yaml")
    parser.add_argument("--dry-run", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(run_pipeline(args.config, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
