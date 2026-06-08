from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


VERSION = "13B.1"


ARTIFACTS = [
    ("project", "README.md", True),
    ("orchestration", "scripts/run_project_checkpoint.sh", True),
    ("orchestration", "src/core/project_orchestrator.py", True),
    ("reviewer", "reports/reviewer_ready_v2.md", True),
    ("reviewer", "reports/reviewer_quick_path.md", True),
    ("reviewer", "reports/senior_reviewer_note.md", True),
    ("reviewer", "reports/reviewer_ready_v2.json", True),
    ("reviewer", "dashboards/reviewer_ready_v2_metrics.csv", True),
    ("intake", "reports/dataset_adapter_registry_run.md", True),
    ("intake", "reports/dataset_adapter_registry_run.json", True),
    ("intake", "reports/dataset_intake_summary.md", True),
    ("intake", "reports/dataset_intake_summary.json", True),
    ("intake", "dashboards/dataset_intake_summary.csv", True),
    ("availability", "reports/data_availability_index.md", True),
    ("availability", "reports/data_availability_index.json", True),
    ("availability", "dashboards/data_availability_index.csv", True),
    ("run_catalog", "reports/market_month_run_catalog.md", True),
    ("run_catalog", "reports/market_month_run_catalog.json", True),
    ("run_catalog", "dashboards/market_month_run_catalog.csv", True),
    ("active_selection", "reports/active_run_selection.md", True),
    ("active_selection", "reports/active_run_selection.json", True),
    ("active_selection", "dashboards/active_run_selection.csv", True),
    ("lead_time", "reports/lead_time_evaluation_2024-05_to_2024-08.md", True),
    ("lead_time", "dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv", True),
    ("visual", "reports/visual_reviewer_pack.md", True),
    ("dashboard", "app/streamlit_app.py", True),
    ("dashboard", "reports/figures/dashboard/dashboard_overview.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_selected_month.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_diagnostics.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_lead_time.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_dataset_intake.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_data_availability.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_run_catalog.png", True),
    ("dashboard", "reports/figures/dashboard/dashboard_reviewer_files.png", True),
    ("core", "src/core/data_contracts.py", True),
    ("core", "src/core/dataset_adapters.py", True),
    ("core", "src/core/adapter_registry.py", True),
    ("core", "src/core/intake_summary.py", True),
]


@dataclass(frozen=True)
class ArtifactRow:
    category: str
    path: str
    required: bool
    exists: bool
    size_bytes: int | None
    sha256: str | None


def file_hash(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def inspect_artifact(category: str, path_text: str, required: bool) -> ArtifactRow:
    path = Path(path_text)

    if not path.exists():
        return ArtifactRow(
            category=category,
            path=path_text,
            required=required,
            exists=False,
            size_bytes=None,
            sha256=None,
        )

    return ArtifactRow(
        category=category,
        path=path_text,
        required=required,
        exists=True,
        size_bytes=path.stat().st_size,
        sha256=file_hash(path),
    )


def build_manifest() -> pd.DataFrame:
    rows = [
        asdict(inspect_artifact(category, path, required))
        for category, path, required in ARTIFACTS
    ]

    return pd.DataFrame(rows)


def manifest_metrics(df: pd.DataFrame) -> dict[str, int | bool]:
    required = df[df["required"] == True]
    missing_required = required[required["exists"] == False]

    return {
        "artifacts": int(len(df)),
        "required_artifacts": int(len(required)),
        "existing_artifacts": int(df["exists"].sum()),
        "missing_required_artifacts": int(len(missing_required)),
        "all_required_present": len(missing_required) == 0,
    }


def report_text(df: pd.DataFrame, metrics: dict[str, int | bool], output_csv: str) -> str:
    lines = [
        "# Project artifact manifest",
        "",
        f"Version: `{VERSION}`",
        f"Manifest table: `{output_csv}`",
        "",
        "## Status",
        "",
        f"- Artifacts tracked: `{metrics['artifacts']}`",
        f"- Required artifacts: `{metrics['required_artifacts']}`",
        f"- Existing artifacts: `{metrics['existing_artifacts']}`",
        f"- Missing required artifacts: `{metrics['missing_required_artifacts']}`",
        f"- All required present: `{metrics['all_required_present']}`",
        "",
        "## Artifacts",
        "",
        "| category | path | required | exists | size bytes | sha256 |",
        "|---|---|---:|---:|---:|---|",
    ]

    for row in df.to_dict("records"):
        sha = row["sha256"] or ""
        short_sha = sha[:12] if sha else ""
        size = "" if pd.isna(row["size_bytes"]) else int(row["size_bytes"])
        lines.append(
            f"| {row['category']} | `{row['path']}` | {row['required']} | "
            f"{row['exists']} | {size} | `{short_sha}` |"
        )

    lines += [
        "",
        "## Readout",
        "",
    ]

    if metrics["all_required_present"]:
        lines.append("All required checkpoint artifacts are present.")
    else:
        lines.append("One or more required checkpoint artifacts are missing. Rebuild the checkpoint before review.")

    lines += [
        "",
        "This manifest is for reproducibility and review control. It does not validate market logic by itself.",
        "",
    ]

    return "\n".join(lines)


def build(output_csv: str, output_report: str, output_json: str) -> None:
    df = build_manifest()
    metrics = manifest_metrics(df)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(df, metrics, output_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "metrics": metrics,
                "manifest_csv": output_csv,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | artifact manifest={output_report}")
    print(f"OK | missing_required={metrics['missing_required_artifacts']}")

    if not metrics["all_required_present"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-csv", default="dashboards/project_artifact_manifest.csv")
    parser.add_argument("--output-report", default="reports/project_artifact_manifest.md")
    parser.add_argument("--output-json", default="reports/project_artifact_manifest.json")
    args = parser.parse_args()

    build(
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
