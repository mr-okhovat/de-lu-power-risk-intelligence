from pathlib import Path

import pandas as pd

from src.core.artifact_manifest import ArtifactRow, file_hash, manifest_metrics


def test_file_hash(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")

    assert len(file_hash(p)) == 64


def test_manifest_metrics_all_present() -> None:
    df = pd.DataFrame(
        [
            {"required": True, "exists": True},
            {"required": True, "exists": True},
            {"required": False, "exists": False},
        ]
    )

    out = manifest_metrics(df)

    assert out["required_artifacts"] == 2
    assert out["missing_required_artifacts"] == 0
    assert out["all_required_present"] is True


def test_manifest_metrics_missing_required() -> None:
    df = pd.DataFrame(
        [
            {"required": True, "exists": True},
            {"required": True, "exists": False},
        ]
    )

    out = manifest_metrics(df)

    assert out["missing_required_artifacts"] == 1
    assert out["all_required_present"] is False


def test_artifact_row_shape() -> None:
    row = ArtifactRow(
        category="demo",
        path="demo.txt",
        required=True,
        exists=False,
        size_bytes=None,
        sha256=None,
    )

    assert row.category == "demo"
    assert row.required is True
