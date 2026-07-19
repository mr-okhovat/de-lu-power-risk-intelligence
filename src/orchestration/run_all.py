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


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_step(step: PipelineStep, dry_run: bool) -> dict[str, object]:
    started = now_utc()
    t0 = time.monotonic()

    print(f"\n=== {step.name} ===")
    print(step.description)
    print(" ".join(step.command))

    if dry_run:
        return {
            "name": step.name,
            "status": "DRY_RUN",
            "command": step.command,
            "started_at_utc": started,
            "finished_at_utc": now_utc(),
            "duration_seconds": 0.0,
            "return_code": 0,
        }

    result = subprocess.run(step.command, check=False)

    return {
        "name": step.name,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "command": step.command,
        "started_at_utc": started,
        "finished_at_utc": now_utc(),
        "duration_seconds": round(time.monotonic() - t0, 3),
        "return_code": result.returncode,
    }


def read_admission_summary(
    path: str | Path,
) -> dict[str, object] | None:
    report_path = Path(path)

    if not report_path.exists():
        return None

    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def render_summary(
    config: PipelineConfig,
    results: list[dict[str, object]],
    status: str,
    admission: dict[str, object] | None = None,
) -> str:
    paths = output_paths(config)

    lines = [
        "# Pipeline run summary",
        "",
        f"Pipeline: {config.name}",
        f"Run: {config.run_label}",
        f"Status: {status}",
        f"Window: {config.start} to {config.end}",
        f"Market: {config.market_label}",
        f"SMARD region: {config.smard_region}",
        "",
        "## Steps",
        "",
        "| step | status | seconds |",
        "|---|---:|---:|",
    ]

    for item in results:
        lines.append(f"| {item['name']} | {item['status']} | {item['duration_seconds']} |")

    admission_executed = any(
        item.get("name") == "market_data_admission"
        for item in results
    )

    if admission is not None:
        lines += [
            "",
            "## Market data admission",
            "",
            f"- Decision: {admission.get('decision', 'UNKNOWN')}",
            f"- Reliability score: {admission.get('reliability_score', 'UNKNOWN')}",
            f"- Dataset: {admission.get('dataset_id', 'UNKNOWN')}",
            f"- Report: `{paths['market_data_admission_json']}`",
        ]
    elif admission_executed:
        lines += [
            "",
            "## Market data admission",
            "",
            "- Result: unavailable",
            f"- Expected report: `{paths['market_data_admission_json']}`",
        ]

    lines += [
        "",
        "## Outputs",
        "",
    ]

    for name, path in sorted(paths.items()):
        if name in {"run_summary", "run_summary_json"}:
            lines.append(f"- {name}: `{path}` (written by this run)")
            continue

        exists = "yes" if Path(path).exists() else "no"
        lines.append(f"- {name}: `{path}` ({exists})")

    lines += [
        "",
        "This run reproduces the implemented public-data pipeline. It does not claim trading profitability, execution capability, or P&L.",
        "",
    ]

    return "\n".join(lines)


def write_summary(config: PipelineConfig, results: list[dict[str, object]], status: str) -> None:
    paths = output_paths(config)
    md = Path(paths["run_summary"])
    js = Path(paths["run_summary_json"])

    md.parent.mkdir(parents=True, exist_ok=True)
    js.parent.mkdir(parents=True, exist_ok=True)

    admission = read_admission_summary(
        paths["market_data_admission_json"]
    )

    md.write_text(
        render_summary(
            config,
            results,
            status,
            admission=admission,
        ),
        encoding="utf-8",
    )

    js.write_text(
        json.dumps(
            {
                "config": asdict(config),
                "status": status,
                "steps": results,
                "market_data_admission": admission,
                "outputs": paths,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def run_pipeline(config_path: str, dry_run: bool) -> int:
    config = load_pipeline_config(config_path)
    steps = build_pipeline_steps(config)

    results: list[dict[str, object]] = []

    for step in steps:
        result = run_step(step, dry_run)
        results.append(result)

        if result["status"] == "FAIL":
            if not dry_run:
                write_summary(config, results, "FAIL")
            print(f"\nPIPELINE FAILED: {step.name}")
            return 1

    if not dry_run:
        write_summary(config, results, "PASS")

    print("\nPIPELINE PASS")
    if dry_run:
        print("Dry run only. No summary file was written.")
    else:
        print(f"Summary: {output_paths(config)['run_summary']}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/pipeline_sample.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    raise SystemExit(run_pipeline(args.config, args.dry_run))


if __name__ == "__main__":
    main()
