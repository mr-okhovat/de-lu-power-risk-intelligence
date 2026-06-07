import pandas as pd

from app.streamlit_app import (
    artifact_manifest_core_table,
    artifact_manifest_metrics,
    checkpoint_metrics,
    checkpoint_stage_table,
)


def test_checkpoint_helpers() -> None:
    payload = {
        "status": "PASS",
        "include_screenshots": False,
        "results": [
            {
                "name": "tests",
                "status": "PASS",
                "return_code": 0,
                "missing_outputs": [],
            },
            {
                "name": "artifact_manifest",
                "status": "PASS",
                "return_code": 0,
                "missing_outputs": [],
            },
        ],
    }

    metrics = checkpoint_metrics(payload)
    table = checkpoint_stage_table(payload)

    assert metrics["status"] == "PASS"
    assert metrics["stages"] == 2
    assert metrics["failed_stages"] == 0
    assert "stage" in table.columns


def test_artifact_manifest_helpers() -> None:
    df = pd.DataFrame(
        {
            "category": ["a", "b"],
            "path": ["a.txt", "b.txt"],
            "required": [True, True],
            "exists": [True, False],
            "size_bytes": [10, None],
            "sha256": ["abc123456789xxxx", None],
        }
    )

    metrics = artifact_manifest_metrics(df)
    table = artifact_manifest_core_table(df)

    assert metrics["artifacts"] == 2
    assert metrics["required"] == 2
    assert metrics["missing_required"] == 1
    assert metrics["all_required_present"] is False
    assert table.iloc[0]["sha256"] == "abc123456789"
