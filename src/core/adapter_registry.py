from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from src.core import data_contracts
from src.core import dataset_adapters


VERSION = "12C.1"


@dataclass(frozen=True)
class RegistryRunResult:
    status: str
    registry_file: str
    selected_dataset: str | None
    total_entries: int
    executed_entries: int
    passed_entries: int
    failed_entries: int
    results: list[dict[str, Any]]


def read_registry(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing registry file: {p}")

    with p.open("r", encoding="utf-8") as handle:
        registry = yaml.safe_load(handle)

    if not isinstance(registry, dict):
        raise ValueError(f"Invalid registry file: {p}")

    if "datasets" not in registry:
        raise ValueError("Registry must contain a datasets list.")

    if not isinstance(registry["datasets"], list):
        raise ValueError("Registry datasets must be a list.")

    return registry


def select_entries(registry: dict[str, Any], dataset: str | None) -> list[dict[str, Any]]:
    entries = registry["datasets"]

    if dataset is None:
        return entries

    selected = [item for item in entries if item.get("id") == dataset]

    if not selected:
        raise ValueError(f"Dataset not found in registry: {dataset}")

    return selected


def require_keys(entry: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if key not in entry]

    if missing:
        dataset_id = entry.get("id", "<unknown>")
        raise ValueError(f"Registry entry {dataset_id} is missing keys: {missing}")


def run_adapter_step(entry: dict[str, Any]) -> dict[str, Any]:
    adapter = dataset_adapters.read_yaml(entry["adapter"])
    source = dataset_adapters.read_input(entry["input"])

    adapted, adapter_result = dataset_adapters.adapt_frame(source, adapter)

    adapter_result = dataset_adapters.AdapterResult(
        status=adapter_result.status,
        adapter_name=adapter_result.adapter_name,
        adapter_version=adapter_result.adapter_version,
        input_file=entry["input"],
        output_file=entry["adapted_output"],
        row_count=adapter_result.row_count,
        output_columns=adapter_result.output_columns,
        missing_source_columns=adapter_result.missing_source_columns,
        conversion_errors=adapter_result.conversion_errors,
        notes=adapter_result.notes,
    )

    Path(entry["adapted_output"]).parent.mkdir(parents=True, exist_ok=True)
    Path(entry["adapter_report"]).parent.mkdir(parents=True, exist_ok=True)
    Path(entry["adapter_json"]).parent.mkdir(parents=True, exist_ok=True)

    adapted.to_csv(entry["adapted_output"], index=False)
    Path(entry["adapter_report"]).write_text(dataset_adapters.report_text(adapter_result), encoding="utf-8")
    Path(entry["adapter_json"]).write_text(
        json.dumps(asdict(adapter_result), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return asdict(adapter_result)


def run_contract_step(entry: dict[str, Any]) -> dict[str, Any]:
    contract = data_contracts.read_contract(entry["contract"])
    canonical = data_contracts.read_input(entry["adapted_output"])
    contract_result = data_contracts.validate_frame(canonical, contract, entry["adapted_output"])

    Path(entry["contract_report"]).parent.mkdir(parents=True, exist_ok=True)
    Path(entry["contract_json"]).parent.mkdir(parents=True, exist_ok=True)

    Path(entry["contract_report"]).write_text(data_contracts.report_text(contract_result), encoding="utf-8")
    Path(entry["contract_json"]).write_text(
        json.dumps(asdict(contract_result), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return asdict(contract_result)


def run_entry(entry: dict[str, Any]) -> dict[str, Any]:
    required = [
        "id",
        "input",
        "adapter",
        "contract",
        "adapted_output",
        "adapter_report",
        "adapter_json",
        "contract_report",
        "contract_json",
    ]

    require_keys(entry, required)

    adapter_result = run_adapter_step(entry)

    if adapter_result["status"] != "PASS":
        return {
            "id": entry["id"],
            "status": "CHECK NEEDED",
            "stage": "adapter",
            "adapter": adapter_result,
            "contract": None,
        }

    contract_result = run_contract_step(entry)

    if contract_result["status"] != "PASS":
        return {
            "id": entry["id"],
            "status": "CHECK NEEDED",
            "stage": "contract",
            "adapter": adapter_result,
            "contract": contract_result,
        }

    return {
        "id": entry["id"],
        "status": "PASS",
        "stage": "complete",
        "adapter": adapter_result,
        "contract": contract_result,
    }


def report_text(result: RegistryRunResult) -> str:
    lines = [
        "# Dataset registry run",
        "",
        f"Version: `{VERSION}`",
        f"Status: `{result.status}`",
        f"Registry: `{result.registry_file}`",
        f"Selected dataset: `{result.selected_dataset}`",
        f"Total registry entries: `{result.total_entries}`",
        f"Executed entries: `{result.executed_entries}`",
        f"Passed entries: `{result.passed_entries}`",
        f"Failed entries: `{result.failed_entries}`",
        "",
        "## Results",
        "",
        "| dataset | status | failed stage |",
        "|---|---|---|",
    ]

    for item in result.results:
        failed_stage = "" if item["status"] == "PASS" else item["stage"]
        lines.append(f"| {item['id']} | {item['status']} | {failed_stage} |")

    lines += [
        "",
        "## Readout",
        "",
    ]

    if result.status == "PASS":
        lines.append("All selected datasets passed adapter mapping and contract validation.")
    else:
        lines.append("One or more datasets failed adapter mapping or contract validation.")

    lines.append("")

    return "\n".join(lines)


def run_registry(
    *,
    registry_file: str,
    dataset: str | None,
    report_output: str,
    json_output: str,
) -> RegistryRunResult:
    registry = read_registry(registry_file)
    entries = select_entries(registry, dataset)

    results = [run_entry(entry) for entry in entries]

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = len(results) - passed

    result = RegistryRunResult(
        status="PASS" if failed == 0 else "CHECK NEEDED",
        registry_file=registry_file,
        selected_dataset=dataset,
        total_entries=len(registry["datasets"]),
        executed_entries=len(entries),
        passed_entries=passed,
        failed_entries=failed,
        results=results,
    )

    Path(report_output).parent.mkdir(parents=True, exist_ok=True)
    Path(json_output).parent.mkdir(parents=True, exist_ok=True)

    Path(report_output).write_text(report_text(result), encoding="utf-8")
    Path(json_output).write_text(
        json.dumps(asdict(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | registry status={result.status}")
    print(f"OK | executed={result.executed_entries} | passed={result.passed_entries} | failed={result.failed_entries}")
    print(f"OK | report={report_output}")

    if result.status != "PASS":
        raise SystemExit(1)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--json-output", required=True)
    args = parser.parse_args()

    run_registry(
        registry_file=args.registry,
        dataset=args.dataset,
        report_output=args.report_output,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    main()
