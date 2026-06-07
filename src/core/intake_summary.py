from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


VERSION = "12E.1"


def read_yaml(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing YAML file: {p}")

    with p.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML file: {p}")

    return data


def read_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing JSON file: {p}")

    return json.loads(p.read_text(encoding="utf-8"))


def registry_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    datasets = registry.get("datasets", [])

    if not isinstance(datasets, list):
        raise ValueError("Registry datasets must be a list.")

    return {str(item["id"]): item for item in datasets}


def row_from_result(result: dict[str, Any], registry_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    dataset_id = str(result["id"])
    registry_entry = registry_lookup.get(dataset_id, {})

    adapter = result.get("adapter") or {}
    contract = result.get("contract") or {}

    return {
        "dataset_id": dataset_id,
        "status": result.get("status"),
        "failed_stage": "" if result.get("status") == "PASS" else result.get("stage", ""),
        "input_file": registry_entry.get("input", adapter.get("input_file", "")),
        "adapted_output": registry_entry.get("adapted_output", adapter.get("output_file", "")),
        "adapter_name": adapter.get("adapter_name", ""),
        "contract_name": contract.get("contract_name", ""),
        "adapter_status": adapter.get("status", ""),
        "contract_status": contract.get("status", ""),
        "row_count": int(adapter.get("row_count") or contract.get("row_count") or 0),
        "adapter_report": registry_entry.get("adapter_report", ""),
        "contract_report": registry_entry.get("contract_report", ""),
    }


def build_summary_frame(registry: dict[str, Any], registry_run: dict[str, Any]) -> pd.DataFrame:
    lookup = registry_index(registry)
    results = registry_run.get("results", [])

    if not isinstance(results, list):
        raise ValueError("Registry run results must be a list.")

    rows = [row_from_result(item, lookup) for item in results]

    return pd.DataFrame(rows)


def metrics(summary: pd.DataFrame) -> dict[str, Any]:
    if summary.empty:
        return {
            "registered_datasets": 0,
            "passed_datasets": 0,
            "failed_datasets": 0,
            "canonical_rows": 0,
            "all_passed": False,
        }

    passed = int((summary["status"] == "PASS").sum())
    failed = int(len(summary) - passed)

    return {
        "registered_datasets": int(len(summary)),
        "passed_datasets": passed,
        "failed_datasets": failed,
        "canonical_rows": int(summary.loc[summary["status"] == "PASS", "row_count"].sum()),
        "all_passed": failed == 0,
    }


def report_text(summary: pd.DataFrame, metric: dict[str, Any], summary_csv: str) -> str:
    lines = [
        "# Dataset intake summary",
        "",
        f"Version: `{VERSION}`",
        f"Summary table: `{summary_csv}`",
        "",
        "## Intake status",
        "",
        f"- Registered datasets: `{metric['registered_datasets']}`",
        f"- Passed datasets: `{metric['passed_datasets']}`",
        f"- Failed datasets: `{metric['failed_datasets']}`",
        f"- Canonical rows available: `{metric['canonical_rows']}`",
        f"- All passed: `{metric['all_passed']}`",
        "",
        "## Registered datasets",
        "",
        "| dataset | status | rows | adapted output | contract report |",
        "|---|---|---:|---|---|",
    ]

    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['dataset_id']} | {row['status']} | {row['row_count']} | "
            f"`{row['adapted_output']}` | `{row['contract_report']}` |"
        )

    lines += [
        "",
        "## Readout",
        "",
    ]

    if metric["all_passed"]:
        lines.append("All registered datasets passed adapter mapping and contract validation.")
    else:
        lines.append("One or more datasets need attention before they should enter analytics.")

    lines += [
        "",
        "This is the controlled intake layer. New datasets should enter through the same adapter-plus-contract path before analysis.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    registry_file: str,
    registry_run_json: str,
    summary_csv: str,
    output_report: str,
    output_json: str,
) -> None:
    registry = read_yaml(registry_file)
    registry_run = read_json(registry_run_json)

    summary = build_summary_frame(registry, registry_run)
    metric = metrics(summary)

    Path(summary_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(summary_csv, index=False)
    Path(output_report).write_text(report_text(summary, metric, summary_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "registry_file": registry_file,
                "registry_run_json": registry_run_json,
                "metrics": metric,
                "summary_csv": summary_csv,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | intake summary={output_report}")
    print(f"OK | datasets={metric['registered_datasets']} | passed={metric['passed_datasets']} | rows={metric['canonical_rows']}")

    if not metric["all_passed"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--registry-run-json", required=True)
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    build(
        registry_file=args.registry,
        registry_run_json=args.registry_run_json,
        summary_csv=args.summary_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
