import pandas as pd

from src.core.intake_summary import build_summary_frame, metrics


def test_build_summary_frame() -> None:
    registry = {
        "datasets": [
            {
                "id": "demo",
                "input": "input.csv",
                "adapted_output": "adapted.csv",
                "adapter_report": "adapter.md",
                "contract_report": "contract.md",
            }
        ]
    }

    run = {
        "results": [
            {
                "id": "demo",
                "status": "PASS",
                "stage": "complete",
                "adapter": {
                    "status": "PASS",
                    "adapter_name": "demo_adapter",
                    "input_file": "input.csv",
                    "output_file": "adapted.csv",
                    "row_count": 10,
                },
                "contract": {
                    "status": "PASS",
                    "contract_name": "demo_contract",
                    "row_count": 10,
                },
            }
        ]
    }

    out = build_summary_frame(registry, run)

    assert len(out) == 1
    assert out.iloc[0]["dataset_id"] == "demo"
    assert out.iloc[0]["row_count"] == 10


def test_metrics() -> None:
    summary = pd.DataFrame(
        {
            "status": ["PASS", "CHECK NEEDED"],
            "row_count": [10, 5],
        }
    )

    out = metrics(summary)

    assert out["registered_datasets"] == 2
    assert out["passed_datasets"] == 1
    assert out["failed_datasets"] == 1
    assert out["canonical_rows"] == 10
    assert out["all_passed"] is False
