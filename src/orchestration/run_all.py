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


def run_step(step: PipelineStep, *, dry_run: bool = False) -> dict[str, object]:
    started_at = utc_now_iso()
    start = time.monotonic()

    print(f"\n=== RUNNING: {step.name} ===")
    print(step.description)
    print(" ".join(step.command))

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

    return {
        "name": step.name,
        "description": step.description,
        "command": step.command,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "started_at_utc": started_at,
        "finished_at_utc": utc_now_iso(),
        "duration_seconds": round(time.monotonic() - start, 3),
        "return_code": completed.returncode,
    }


def render_pipeline_summary(
    *,
    config: PipelineConfig,
    step_results: list[dict[str, object]],
    status: str,
    paths: dict[str, str],
) -> str:
    lines = [
        "# Pipeline Run Summary",
        "",
        f"- Pipeline: `{config.name}`",
        f"- Run label: `{config.run_label}`",
        f"- Status: `{status}`",
        f"- Start date: `{config.start}`",
        f"- End date: `{config.end}`",
        f"- Market label: `{config.market_label}`",
        f"- SMARD region: `{config.smard_region}`",
        f"- Event study enabled: `{config.include_event_study}`",
        f"- Signal-event evaluation enabled: `{config.include_signal_event_evaluation}`",
        "",
        "## Step Results",
        "",
        "| Step | Status | Duration seconds |",
        "|---|---:|---:|",
    ]

    for result in step_results:
        lines.append(f"| {result['name']} | {result['status']} | {result['duration_seconds']} |")

    lines.extend([
        "",
        "## Key Outputs",
        "",
        f"- `staging`: `{paths['staging']}`",
        f"- `features`: `{paths['features']}`",
        f"- `dashboard_market_overview`: `{paths['dashboard_market_overview']}`",
        f"- `risk_signals`: `{paths['risk_signals']}`",
        f"- `risk_diagnostics_report`: `{paths['risk_diagnostics_report']}`",
        "",
        "## Methodological Boundary",
        "",
        "This automated run reproduces the currently implemented public-data analytics pipeline through risk diagnostics. It does not create a trading strategy, execution logic, or P&L claim.",
        "",
    ])

    return "\n".join(lines)


def write_summary_outputs(
    *,
    config: PipelineConfig,
    step_results: list[dict[str, object]],
    status: str,
) -> None:
    paths = output_paths(config)

    summary_md = Path(paths["run_summary"])
    summary_json = Path(paths["run_summary_json"])

    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)

    summary_md.write_text(
        render_pipeline_summary(config=config, step_results=step_results, status=status, paths=paths),
        encoding="utf-8",
    )

    summary_json.write_text(
        json.dumps(
            {
                "config": asdict(config),
                "status": status,
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

    for step in steps:
        result = run_step(step, dry_run=dry_run)
        step_results.append(result)

        if result["status"] == "FAIL":
            if not dry_run:
                write_summary_outputs(config=config, step_results=step_results, status="FAIL")
            print(f"\nPIPELINE FAILED at step: {step.name}")
            return 1

    if not dry_run:
        write_summary_outputs(config=config, step_results=step_results, status="PASS")

    print("\nPIPELINE PASS")

    if dry_run:
        print("Dry run completed. No summary files were written.")
    else:
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
