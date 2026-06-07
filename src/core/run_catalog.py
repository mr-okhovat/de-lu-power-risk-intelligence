from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


VERSION = "15A.1"


def read_csv_required(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing CSV file: {p}")

    return pd.read_csv(p)


def read_csv_optional(path: str) -> pd.DataFrame:
    p = Path(path)

    if not p.exists():
        return pd.DataFrame()

    return pd.read_csv(p)


def normalize_date(value: object) -> str:
    if pd.isna(value):
        return ""

    return str(value)[:10]


def month_key(start: object, end: object) -> str:
    return f"{normalize_date(start)}_to_{normalize_date(end)}"


def safe_float(value: object) -> float | None:
    if pd.isna(value):
        return None

    try:
        return float(value)
    except Exception:
        return None


def file_exists(path: object) -> bool:
    if pd.isna(path) or not str(path):
        return False

    return Path(str(path)).exists()


def enrich_with_same_hour(catalog: pd.DataFrame, cross_month: pd.DataFrame) -> pd.DataFrame:
    if catalog.empty or cross_month.empty:
        return catalog

    required = {"start", "end", "precision", "recall", "event_lift", "signal_rows", "price_event_rows", "tp", "fp", "fn"}
    if not required.issubset(cross_month.columns):
        return catalog

    cm = cross_month.copy()
    cm["run_key"] = cm.apply(lambda row: month_key(row["start"], row["end"]), axis=1)

    keep = [
        "run_key",
        "precision",
        "recall",
        "event_lift",
        "signal_rows",
        "price_event_rows",
        "tp",
        "fp",
        "fn",
    ]

    cm = cm[keep].rename(
        columns={
            "precision": "same_hour_precision",
            "recall": "same_hour_recall",
            "event_lift": "same_hour_event_lift",
            "signal_rows": "same_hour_signal_rows",
            "price_event_rows": "same_hour_price_event_rows",
            "tp": "same_hour_tp",
            "fp": "same_hour_fp",
            "fn": "same_hour_fn",
        }
    )

    return catalog.merge(cm, how="left", on="run_key")


def lead_metric_frame(lead_monthly: pd.DataFrame) -> pd.DataFrame:
    if lead_monthly.empty:
        return pd.DataFrame()

    required = {"start", "end", "mode", "horizon_hours", "precision", "recall", "event_lift"}
    if not required.issubset(lead_monthly.columns):
        return pd.DataFrame()

    work = lead_monthly.copy()
    work["run_key"] = work.apply(lambda row: month_key(row["start"], row["end"]), axis=1)

    targets = {
        ("exact_hour", 1): "exact_next_1h",
        ("future_window", 3): "window_next_3h",
        ("future_window", 6): "window_next_6h",
    }

    rows: list[dict[str, Any]] = []

    for run_key, group in work.groupby("run_key"):
        row: dict[str, Any] = {"run_key": run_key}

        for (mode, horizon), prefix in targets.items():
            subset = group[
                (group["mode"] == mode)
                & (group["horizon_hours"].astype(int) == horizon)
            ]

            if subset.empty:
                row[f"{prefix}_precision"] = None
                row[f"{prefix}_recall"] = None
                row[f"{prefix}_event_lift"] = None
                continue

            item = subset.iloc[0]
            row[f"{prefix}_precision"] = safe_float(item["precision"])
            row[f"{prefix}_recall"] = safe_float(item["recall"])
            row[f"{prefix}_event_lift"] = safe_float(item["event_lift"])

        rows.append(row)

    return pd.DataFrame(rows)


def enrich_with_lead_time(catalog: pd.DataFrame, lead_monthly: pd.DataFrame) -> pd.DataFrame:
    if catalog.empty or lead_monthly.empty:
        return catalog

    lead = lead_metric_frame(lead_monthly)

    if lead.empty:
        return catalog

    return catalog.merge(lead, how="left", on="run_key")


def build_base_catalog(availability: pd.DataFrame) -> pd.DataFrame:
    if availability.empty:
        return pd.DataFrame()

    rows = []

    for row in availability.to_dict("records"):
        start = normalize_date(row.get("start", ""))
        end = normalize_date(row.get("end", ""))
        market = str(row.get("market", ""))

        if not start or not end or not market:
            continue

        key = month_key(start, end)

        behavior_report = f"reports/price_risk_behavior_{start}_to_{end}.md"
        evaluation_file = row.get("source_file", "")
        adapted_file = row.get("adapted_file", "")
        contract_report = row.get("contract_report", "")

        rows.append(
            {
                "run_id": f"{market}_{key}",
                "run_key": key,
                "market": market,
                "start": start,
                "end": end,
                "dataset_id": row.get("dataset_id", ""),
                "registered": row.get("registered", False),
                "analytics_ready": row.get("analytics_ready", False),
                "intake_status": row.get("intake_status", ""),
                "source_rows": row.get("source_rows", None),
                "adapted_rows": row.get("adapted_rows", None),
                "intake_row_count": row.get("intake_row_count", None),
                "evaluation_file": evaluation_file,
                "adapted_file": adapted_file,
                "contract_report": contract_report,
                "behavior_report": behavior_report,
                "evaluation_file_exists": file_exists(evaluation_file),
                "adapted_file_exists": file_exists(adapted_file),
                "contract_report_exists": file_exists(contract_report),
                "behavior_report_exists": file_exists(behavior_report),
            }
        )

    return pd.DataFrame(rows)


def add_run_status(catalog: pd.DataFrame) -> pd.DataFrame:
    if catalog.empty:
        return catalog

    out = catalog.copy()

    required_flags = [
        "analytics_ready",
        "evaluation_file_exists",
        "adapted_file_exists",
        "contract_report_exists",
    ]

    for col in required_flags:
        if col not in out.columns:
            out[col] = False

    ready = pd.Series(True, index=out.index)

    for col in required_flags:
        ready = ready & out[col].astype(str).str.lower().isin(["true", "1", "yes"])

    out["run_ready"] = ready
    out["run_status"] = out["run_ready"].map({True: "READY", False: "CHECK NEEDED"})

    return out


def build_catalog(
    *,
    availability_csv: str,
    cross_month_csv: str,
    lead_monthly_csv: str,
) -> pd.DataFrame:
    availability = read_csv_required(availability_csv)
    cross_month = read_csv_optional(cross_month_csv)
    lead_monthly = read_csv_optional(lead_monthly_csv)

    catalog = build_base_catalog(availability)
    catalog = enrich_with_same_hour(catalog, cross_month)
    catalog = enrich_with_lead_time(catalog, lead_monthly)
    catalog = add_run_status(catalog)

    if catalog.empty:
        return catalog

    ordered = [
        "run_id",
        "market",
        "start",
        "end",
        "run_status",
        "run_ready",
        "dataset_id",
        "analytics_ready",
        "intake_status",
        "source_rows",
        "same_hour_signal_rows",
        "same_hour_price_event_rows",
        "same_hour_precision",
        "same_hour_recall",
        "same_hour_event_lift",
        "exact_next_1h_precision",
        "exact_next_1h_recall",
        "exact_next_1h_event_lift",
        "window_next_3h_precision",
        "window_next_3h_recall",
        "window_next_3h_event_lift",
        "window_next_6h_precision",
        "window_next_6h_recall",
        "window_next_6h_event_lift",
        "evaluation_file",
        "adapted_file",
        "contract_report",
        "behavior_report",
    ]

    available = [col for col in ordered if col in catalog.columns]
    extra = [col for col in catalog.columns if col not in available]

    return catalog[available + extra].sort_values(["market", "start"]).reset_index(drop=True)


def metrics(catalog: pd.DataFrame) -> dict[str, Any]:
    if catalog.empty:
        return {
            "runs": 0,
            "ready_runs": 0,
            "check_needed_runs": 0,
            "markets": 0,
            "period_start": None,
            "period_end": None,
            "mean_same_hour_lift": None,
            "mean_next_3h_window_lift": None,
        }

    ready = catalog["run_status"] == "READY"

    mean_same = None
    if "same_hour_event_lift" in catalog.columns:
        mean_same = safe_float(catalog["same_hour_event_lift"].mean())

    mean_3h = None
    if "window_next_3h_event_lift" in catalog.columns:
        mean_3h = safe_float(catalog["window_next_3h_event_lift"].mean())

    return {
        "runs": int(len(catalog)),
        "ready_runs": int(ready.sum()),
        "check_needed_runs": int((~ready).sum()),
        "markets": int(catalog["market"].nunique()) if "market" in catalog.columns else 0,
        "period_start": str(catalog["start"].min()) if "start" in catalog.columns else None,
        "period_end": str(catalog["end"].max()) if "end" in catalog.columns else None,
        "mean_same_hour_lift": mean_same,
        "mean_next_3h_window_lift": mean_3h,
    }


def report_text(catalog: pd.DataFrame, metric: dict[str, Any], output_csv: str) -> str:
    lines = [
        "# Market/month run catalog",
        "",
        f"Version: `{VERSION}`",
        f"Catalog table: `{output_csv}`",
        "",
        "## Status",
        "",
        f"- Runs: `{metric['runs']}`",
        f"- Ready runs: `{metric['ready_runs']}`",
        f"- Check-needed runs: `{metric['check_needed_runs']}`",
        f"- Markets: `{metric['markets']}`",
        f"- Period start: `{metric['period_start']}`",
        f"- Period end: `{metric['period_end']}`",
        f"- Mean same-hour event lift: `{metric['mean_same_hour_lift']}`",
        f"- Mean next-3h-window event lift: `{metric['mean_next_3h_window_lift']}`",
        "",
        "## Runs",
        "",
        "| run | status | rows | same-hour lift | next 1h lift | next 3h window lift |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for row in catalog.to_dict("records"):
        lines.append(
            f"| {row.get('run_id')} | {row.get('run_status')} | {row.get('source_rows')} | "
            f"{row.get('same_hour_event_lift', '')} | {row.get('exact_next_1h_event_lift', '')} | "
            f"{row.get('window_next_3h_event_lift', '')} |"
        )

    lines += [
        "",
        "## Readout",
        "",
    ]

    if metric["check_needed_runs"] == 0:
        lines.append("All cataloged market/month runs are ready.")
    else:
        lines.append("Some runs need attention before they should be used for review or downstream analytics.")

    lines += [
        "",
        "This catalog indexes completed analysis runs. It does not create new market signals.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    availability_csv: str,
    cross_month_csv: str,
    lead_monthly_csv: str,
    output_csv: str,
    output_report: str,
    output_json: str,
) -> None:
    catalog = build_catalog(
        availability_csv=availability_csv,
        cross_month_csv=cross_month_csv,
        lead_monthly_csv=lead_monthly_csv,
    )
    metric = metrics(catalog)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    catalog.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(catalog, metric, output_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "metrics": metric,
                "catalog_csv": output_csv,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | run catalog={output_report}")
    print(f"OK | runs={metric['runs']} | ready={metric['ready_runs']}")

    if metric["check_needed_runs"] > 0:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--availability-csv", default="dashboards/data_availability_index.csv")
    parser.add_argument("--cross-month-csv", default="dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv")
    parser.add_argument("--lead-monthly-csv", default="dashboards/lead_time_monthly_DE-LU_2024-05_to_2024-08.csv")
    parser.add_argument("--output-csv", default="dashboards/market_month_run_catalog.csv")
    parser.add_argument("--output-report", default="reports/market_month_run_catalog.md")
    parser.add_argument("--output-json", default="reports/market_month_run_catalog.json")
    args = parser.parse_args()

    build(
        availability_csv=args.availability_csv,
        cross_month_csv=args.cross_month_csv,
        lead_monthly_csv=args.lead_monthly_csv,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
