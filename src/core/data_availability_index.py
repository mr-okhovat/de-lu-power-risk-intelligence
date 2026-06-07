from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


VERSION = "14A.1"

SIGNAL_EVAL_RE = re.compile(
    r"signal_price_evaluation_(?P<market>.+?)_(?P<start>\d{4}-\d{2}-\d{2})_to_(?P<end>\d{4}-\d{2}-\d{2})\.csv$"
)

ADAPTED_SIGNAL_EVAL_RE = re.compile(
    r"signal_price_evaluation_(?P<market>.+?)_(?P<start>\d{4}-\d{2}-\d{2})_to_(?P<end>\d{4}-\d{2}-\d{2})_registry_adapted\.csv$"
)


def read_yaml(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing YAML file: {p}")

    data = yaml.safe_load(p.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML file: {p}")

    return data


def read_optional_csv(path: str) -> pd.DataFrame:
    p = Path(path)

    if not p.exists():
        return pd.DataFrame()

    return pd.read_csv(p)


def parse_signal_file(path: Path, adapted: bool) -> dict[str, Any] | None:
    pattern = ADAPTED_SIGNAL_EVAL_RE if adapted else SIGNAL_EVAL_RE
    match = pattern.search(path.name)

    if not match:
        return None

    return {
        "market": match.group("market"),
        "start": match.group("start"),
        "end": match.group("end"),
    }


def file_rows(path: Path) -> int | None:
    if not path.exists():
        return None

    try:
        return int(len(pd.read_csv(path)))
    except Exception:
        return None


def registry_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []

    for item in registry.get("datasets", []):
        source = Path(item["input"])
        adapted = Path(item["adapted_output"])

        parsed = parse_signal_file(source, adapted=False) or {}

        rows.append(
            {
                "dataset_id": item["id"],
                "dataset_type": "signal_price_evaluation",
                "market": parsed.get("market", ""),
                "start": parsed.get("start", ""),
                "end": parsed.get("end", ""),
                "registered": True,
                "source_file": str(source),
                "source_exists": source.exists(),
                "source_rows": file_rows(source),
                "adapted_file": str(adapted),
                "adapted_exists": adapted.exists(),
                "adapted_rows": file_rows(adapted),
                "contract_report": item.get("contract_report", ""),
                "contract_report_exists": Path(item.get("contract_report", "")).exists(),
                "adapter_report": item.get("adapter_report", ""),
                "adapter_report_exists": Path(item.get("adapter_report", "")).exists(),
            }
        )

    return rows


def discovered_unregistered_rows(registry: dict[str, Any], processed_dir: str) -> list[dict[str, Any]]:
    registered_inputs = {str(Path(item["input"])) for item in registry.get("datasets", [])}
    rows = []

    for path in sorted(Path(processed_dir).glob("signal_price_evaluation_*.csv")):
        parsed = parse_signal_file(path, adapted=False)
        if not parsed:
            continue

        if str(path) in registered_inputs:
            continue

        rows.append(
            {
                "dataset_id": f"unregistered_{parsed['market']}_{parsed['start']}_to_{parsed['end']}",
                "dataset_type": "signal_price_evaluation",
                "market": parsed["market"],
                "start": parsed["start"],
                "end": parsed["end"],
                "registered": False,
                "source_file": str(path),
                "source_exists": path.exists(),
                "source_rows": file_rows(path),
                "adapted_file": "",
                "adapted_exists": False,
                "adapted_rows": None,
                "contract_report": "",
                "contract_report_exists": False,
                "adapter_report": "",
                "adapter_report_exists": False,
            }
        )

    return rows


def attach_intake_status(index: pd.DataFrame, intake: pd.DataFrame) -> pd.DataFrame:
    if index.empty:
        return index

    out = index.copy()

    default_cols = {
        "intake_status": "",
        "intake_row_count": None,
        "analytics_ready": False,
    }

    for col, value in default_cols.items():
        out[col] = value

    if intake.empty or "dataset_id" not in intake.columns:
        return out

    keep = [
        col for col in [
            "dataset_id",
            "status",
            "row_count",
            "adapted_output",
            "contract_report",
        ]
        if col in intake.columns
    ]

    merged = out.merge(
        intake[keep],
        how="left",
        on="dataset_id",
        suffixes=("", "_intake"),
    )

    merged["intake_status"] = merged.get("status", "").fillna("")
    merged["intake_row_count"] = merged.get("row_count", pd.Series([None] * len(merged)))
    merged["analytics_ready"] = (
        (merged["registered"] == True)
        & (merged["source_exists"] == True)
        & (merged["adapted_exists"] == True)
        & (merged["contract_report_exists"] == True)
        & (merged["intake_status"] == "PASS")
    )

    drop_cols = [col for col in ["status", "row_count", "adapted_output_intake", "contract_report_intake"] if col in merged.columns]
    return merged.drop(columns=drop_cols)


def build_index(
    *,
    registry_file: str,
    intake_summary_csv: str,
    processed_dir: str,
) -> pd.DataFrame:
    registry = read_yaml(registry_file)
    intake = read_optional_csv(intake_summary_csv)

    rows = registry_rows(registry)
    rows.extend(discovered_unregistered_rows(registry, processed_dir))

    index = pd.DataFrame(rows)

    if index.empty:
        return index

    index = attach_intake_status(index, intake)

    ordered = [
        "dataset_id",
        "dataset_type",
        "market",
        "start",
        "end",
        "registered",
        "analytics_ready",
        "intake_status",
        "source_exists",
        "adapted_exists",
        "contract_report_exists",
        "source_rows",
        "adapted_rows",
        "intake_row_count",
        "source_file",
        "adapted_file",
        "contract_report",
        "adapter_report",
    ]

    available = [col for col in ordered if col in index.columns]
    extra = [col for col in index.columns if col not in available]

    return index[available + extra].sort_values(["market", "start", "dataset_id"]).reset_index(drop=True)


def metrics(index: pd.DataFrame) -> dict[str, Any]:
    if index.empty:
        return {
            "datasets": 0,
            "registered": 0,
            "unregistered": 0,
            "analytics_ready": 0,
            "markets": 0,
            "period_start": None,
            "period_end": None,
        }

    starts = index["start"].replace("", pd.NA).dropna()
    ends = index["end"].replace("", pd.NA).dropna()

    return {
        "datasets": int(len(index)),
        "registered": int((index["registered"] == True).sum()),
        "unregistered": int((index["registered"] == False).sum()),
        "analytics_ready": int((index["analytics_ready"] == True).sum()),
        "markets": int(index["market"].replace("", pd.NA).dropna().nunique()),
        "period_start": None if starts.empty else str(starts.min()),
        "period_end": None if ends.empty else str(ends.max()),
    }


def report_text(index: pd.DataFrame, metric: dict[str, Any], output_csv: str) -> str:
    lines = [
        "# Data availability index",
        "",
        f"Version: `{VERSION}`",
        f"Index table: `{output_csv}`",
        "",
        "## Status",
        "",
        f"- Datasets found: `{metric['datasets']}`",
        f"- Registered datasets: `{metric['registered']}`",
        f"- Unregistered datasets: `{metric['unregistered']}`",
        f"- Analytics-ready datasets: `{metric['analytics_ready']}`",
        f"- Markets: `{metric['markets']}`",
        f"- Period start: `{metric['period_start']}`",
        f"- Period end: `{metric['period_end']}`",
        "",
        "## Dataset index",
        "",
        "| dataset | market | start | end | registered | ready | status | rows |",
        "|---|---|---|---|---:|---:|---|---:|",
    ]

    for row in index.to_dict("records"):
        rows = row.get("intake_row_count")
        rows_text = "" if pd.isna(rows) else int(rows)
        lines.append(
            f"| {row['dataset_id']} | {row.get('market', '')} | {row.get('start', '')} | "
            f"{row.get('end', '')} | {row.get('registered')} | {row.get('analytics_ready')} | "
            f"{row.get('intake_status', '')} | {rows_text} |"
        )

    lines += [
        "",
        "## Readout",
        "",
    ]

    if metric["unregistered"] == 0 and metric["registered"] == metric["analytics_ready"]:
        lines.append("All discovered signal-price evaluation datasets are registered and analytics-ready.")
    elif metric["unregistered"] > 0:
        lines.append("Some discovered datasets are not registered. Register them before relying on them in analytics.")
    else:
        lines.append("Some registered datasets are not yet analytics-ready. Check adapter and contract reports.")

    lines += [
        "",
        "This index is a data availability layer. It does not validate market logic or signal quality.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    registry_file: str,
    intake_summary_csv: str,
    processed_dir: str,
    output_csv: str,
    output_report: str,
    output_json: str,
) -> None:
    index = build_index(
        registry_file=registry_file,
        intake_summary_csv=intake_summary_csv,
        processed_dir=processed_dir,
    )
    metric = metrics(index)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    index.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(index, metric, output_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "metrics": metric,
                "index_csv": output_csv,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | data availability index={output_report}")
    print(f"OK | datasets={metric['datasets']} | ready={metric['analytics_ready']}")

    if metric["unregistered"] > 0:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="src/config/dataset_adapter_registry.yaml")
    parser.add_argument("--intake-summary", default="dashboards/dataset_intake_summary.csv")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--output-csv", default="dashboards/data_availability_index.csv")
    parser.add_argument("--output-report", default="reports/data_availability_index.md")
    parser.add_argument("--output-json", default="reports/data_availability_index.json")
    args = parser.parse_args()

    build(
        registry_file=args.registry,
        intake_summary_csv=args.intake_summary,
        processed_dir=args.processed_dir,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
