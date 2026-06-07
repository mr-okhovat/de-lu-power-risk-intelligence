from pathlib import Path

import yaml


def test_registry_contains_core_monthly_datasets() -> None:
    registry = yaml.safe_load(Path("src/config/dataset_adapter_registry.yaml").read_text(encoding="utf-8"))

    ids = {item["id"] for item in registry["datasets"]}

    assert ids == {
        "signal_price_evaluation_2024_05",
        "signal_price_evaluation_2024_06",
        "signal_price_evaluation_2024_07",
        "signal_price_evaluation_2024_08",
    }


def test_registry_paths_are_complete() -> None:
    registry = yaml.safe_load(Path("src/config/dataset_adapter_registry.yaml").read_text(encoding="utf-8"))

    required = {
        "id",
        "input",
        "adapter",
        "contract",
        "adapted_output",
        "adapter_report",
        "adapter_json",
        "contract_report",
        "contract_json",
    }

    for item in registry["datasets"]:
        assert required.issubset(item.keys())
        assert item["input"].endswith(".csv")
        assert item["adapted_output"].endswith(".csv")
