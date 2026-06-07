from pathlib import Path

import pandas as pd
import yaml

from src.core.adapter_registry import read_registry, select_entries, run_registry


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_select_entries(tmp_path: Path) -> None:
    registry = {
        "datasets": [
            {"id": "a"},
            {"id": "b"},
        ]
    }

    assert len(select_entries(registry, None)) == 2
    assert select_entries(registry, "a")[0]["id"] == "a"


def test_read_registry(tmp_path: Path) -> None:
    p = tmp_path / "registry.yaml"
    write_file(p, "datasets:\n  - id: demo\n")

    registry = read_registry(str(p))

    assert registry["datasets"][0]["id"] == "demo"


def test_run_registry_passes(tmp_path: Path) -> None:
    input_file = tmp_path / "input.csv"
    pd.DataFrame(
        {
            "time": ["2024-06-01T00:00:00Z"],
            "price": [50.0],
            "score": [60],
            "signal": [True],
            "event": [True],
            "bucket": ["TP"],
            "labels": ["HIGH_PRICE_LEVEL"],
        }
    ).to_csv(input_file, index=False)

    adapter_file = tmp_path / "adapter.yaml"
    write_file(
        adapter_file,
        yaml.safe_dump(
            {
                "name": "demo_adapter",
                "version": "x",
                "fields": [
                    {"source": "time", "target": "timestamp_utc", "dtype": "datetime", "required": True},
                    {"source": "price", "target": "price_eur_per_mwh", "dtype": "numeric", "required": True},
                    {"source": "score", "target": "risk_score", "dtype": "numeric", "required": True},
                    {"source": "signal", "target": "signal_positive", "dtype": "boolean", "required": True},
                    {"source": "event", "target": "event_positive", "dtype": "boolean", "required": True},
                    {"source": "bucket", "target": "confusion_bucket", "dtype": "string", "required": True},
                    {"source": "labels", "target": "price_event_labels", "dtype": "string", "required": True},
                ],
            }
        ),
    )

    contract_file = tmp_path / "contract.yaml"
    write_file(
        contract_file,
        yaml.safe_dump(
            {
                "name": "demo_contract",
                "version": "x",
                "primary_key": ["timestamp_utc"],
                "fields": [
                    {"name": "timestamp_utc", "dtype": "datetime", "required": True, "nullable": False},
                    {"name": "price_eur_per_mwh", "dtype": "numeric", "required": True, "nullable": False},
                    {"name": "risk_score", "dtype": "numeric", "required": True, "nullable": False, "min_value": 0, "max_value": 100},
                    {"name": "signal_positive", "dtype": "boolean", "required": True, "nullable": False},
                    {"name": "event_positive", "dtype": "boolean", "required": True, "nullable": False},
                    {"name": "confusion_bucket", "dtype": "string", "required": True, "nullable": False, "allowed_values": ["TP", "FP", "FN", "TN"]},
                    {"name": "price_event_labels", "dtype": "string", "required": True, "nullable": False},
                ],
            }
        ),
    )

    registry_file = tmp_path / "registry.yaml"
    registry = {
        "datasets": [
            {
                "id": "demo",
                "input": str(input_file),
                "adapter": str(adapter_file),
                "contract": str(contract_file),
                "adapted_output": str(tmp_path / "adapted.csv"),
                "adapter_report": str(tmp_path / "adapter.md"),
                "adapter_json": str(tmp_path / "adapter.json"),
                "contract_report": str(tmp_path / "contract.md"),
                "contract_json": str(tmp_path / "contract.json"),
            }
        ]
    }
    write_file(registry_file, yaml.safe_dump(registry))

    result = run_registry(
        registry_file=str(registry_file),
        dataset=None,
        report_output=str(tmp_path / "registry.md"),
        json_output=str(tmp_path / "registry.json"),
    )

    assert result.status == "PASS"
    assert result.executed_entries == 1
    assert (tmp_path / "adapted.csv").exists()
