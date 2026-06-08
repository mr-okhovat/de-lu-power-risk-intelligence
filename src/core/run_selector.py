from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


VERSION = "16A.1"


def read_catalog(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing run catalog: {p}")

    return pd.read_csv(p)


def select_runs(
    catalog: pd.DataFrame,
    *,
    market: str | None = None,
    start: str | None = None,
    end: str | None = None,
    ready_only: bool = True,
) -> pd.DataFrame:
    out = catalog.copy()

    if ready_only and "run_status" in out.columns:
        out = out[out["run_status"].astype(str).eq("READY")]

    if market:
        out = out[out["market"].astype(str).eq(market)]

    if start:
        out = out[out["start"].astype(str) >= start]

    if end:
        out = out[out["end"].astype(str) <= end]

    if out.empty:
        return out

    cols = [
        "run_id",
        "market",
        "start",
        "end",
        "run_status",
        "source_rows",
        "same_hour_event_lift",
        "window_next_3h_event_lift",
        "evaluation_file",
        "behavior_report",
    ]

    available = [col for col in cols if col in out.columns]
    return out[available].sort_values(["market", "start"]).reset_index(drop=True)


def metrics(selection: pd.DataFrame) -> dict[str, Any]:
    if selection.empty:
        return {
            "selected_runs": 0,
            "markets": 0,
            "period_start": None,
            "period_end": None,
            "mean_same_hour_lift": None,
            "mean_next_3h_window_lift": None,
        }

    same_hour = None
    if "same_hour_event_lift" in selection.columns:
        same_hour = float(pd.to_numeric(selection["same_hour_event_lift"], errors="coerce").mean())

    next_3h = None
    if "window_next_3h_event_lift" in selection.columns:
        next_3h = float(pd.to_numeric(selection["window_next_3h_event_lift"], errors="coerce").mean())

    return {
        "selected_runs": int(len(selection)),
        "markets": int(selection["market"].nunique()) if "market" in selection.columns else 0,
        "period_start": str(selection["start"].min()) if "start" in selection.columns else None,
        "period_end": str(selection["end"].max()) if "end" in selection.columns else None,
        "mean_same_hour_lift": same_hour,
        "mean_next_3h_window_lift": next_3h,
    }


def report_text(selection: pd.DataFrame, metric: dict[str, Any], output_csv: str) -> str:
    lines = [
        "# Active run selection",
        "",
        f"Version: `{VERSION}`",
        f"Selection table: `{output_csv}`",
        "",
        "## Status",
        "",
        f"- Selected runs: `{metric['selected_runs']}`",
        f"- Markets: `{metric['markets']}`",
        f"- Period start: `{metric['period_start']}`",
        f"- Period end: `{metric['period_end']}`",
        f"- Mean same-hour event lift: `{metric['mean_same_hour_lift']}`",
        f"- Mean next-3h-window event lift: `{metric['mean_next_3h_window_lift']}`",
        "",
        "## Selected runs",
        "",
        "| run | market | start | end | status | same-hour lift | next-3h lift |",
        "|---|---|---|---|---|---:|---:|",
    ]

    for row in selection.to_dict("records"):
        lines.append(
            f"| {row.get('run_id')} | {row.get('market')} | {row.get('start')} | {row.get('end')} | "
            f"{row.get('run_status')} | {row.get('same_hour_event_lift', '')} | "
            f"{row.get('window_next_3h_event_lift', '')} |"
        )

    lines += [
        "",
        "## Readout",
        "",
        "This file defines the active market/month runs used by downstream review layers.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    catalog_csv: str,
    output_csv: str,
    output_report: str,
    output_json: str,
    market: str | None,
    start: str | None,
    end: str | None,
    ready_only: bool,
) -> None:
    catalog = read_catalog(catalog_csv)
    selection = select_runs(
        catalog,
        market=market,
        start=start,
        end=end,
        ready_only=ready_only,
    )

    if selection.empty:
        raise SystemExit("No runs matched the selection criteria.")

    metric = metrics(selection)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    selection.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(selection, metric, output_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "catalog_csv": catalog_csv,
                "selection_csv": output_csv,
                "criteria": {
                    "market": market,
                    "start": start,
                    "end": end,
                    "ready_only": ready_only,
                },
                "metrics": metric,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | active run selection={output_report}")
    print(f"OK | selected_runs={metric['selected_runs']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-csv", default="dashboards/market_month_run_catalog.csv")
    parser.add_argument("--output-csv", default="dashboards/active_run_selection.csv")
    parser.add_argument("--output-report", default="reports/active_run_selection.md")
    parser.add_argument("--output-json", default="reports/active_run_selection.json")
    parser.add_argument("--market", default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--include-non-ready", action="store_true")
    args = parser.parse_args()

    build(
        catalog_csv=args.catalog_csv,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
        market=args.market,
        start=args.start,
        end=args.end,
        ready_only=not args.include_non_ready,
    )


if __name__ == "__main__":
    main()
