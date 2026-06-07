from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VERSION = "8I.1"

REQUIRED = [
    "month",
    "rows",
    "signal_rows",
    "price_event_rows",
    "tp",
    "fp",
    "fn",
    "tn",
    "precision",
    "recall",
    "event_lift",
]


def read_summary(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing input file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    return df


def safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return float(a / b)


def aggregate(summary: pd.DataFrame) -> dict[str, object]:
    rows = int(summary["rows"].sum())
    signals = int(summary["signal_rows"].sum())
    events = int(summary["price_event_rows"].sum())

    tp = int(summary["tp"].sum())
    fp = int(summary["fp"].sum())
    fn = int(summary["fn"].sum())
    tn = int(summary["tn"].sum())

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    base_event_rate = safe_div(events, rows)
    signal_event_rate = precision

    lift = None
    if base_event_rate and signal_event_rate is not None:
        lift = signal_event_rate / base_event_rate

    return {
        "months": int(len(summary)),
        "rows": rows,
        "signal_rows": signals,
        "price_event_rows": events,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "base_event_rate": base_event_rate,
        "signal_event_rate": signal_event_rate,
        "aggregate_event_lift": lift,
        "min_monthly_lift": float(summary["event_lift"].min()),
        "max_monthly_lift": float(summary["event_lift"].max()),
        "mean_monthly_lift": float(summary["event_lift"].mean()),
        "all_months_lift_above_one": bool((summary["event_lift"] > 1).all()),
    }


def metric_table(metrics: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"metric": key, "value": value} for key, value in metrics.items()]
    )


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def report_text(summary: pd.DataFrame, metrics: dict[str, object], metrics_csv: str) -> str:
    lines = [
        "# Reviewer-ready v1",
        "",
        f"Version: {VERSION}",
        "",
        "## What this is",
        "",
        "A reproducible public-data analytics prototype for DE-LU power-market risk intelligence.",
        "",
        "It ingests SMARD data, builds hourly market features, creates an explainable fundamentals risk signal, adds day-ahead price data, labels ex-post price events, and compares signal-positive hours with price-event behavior across four months.",
        "",
        "It is not a trading system, not a price forecast, and not a P&L backtest.",
        "",
        "## Current evidence",
        "",
        f"- Months reviewed: {metrics['months']}",
        f"- Rows reviewed: {metrics['rows']}",
        f"- Signal-positive hours: {metrics['signal_rows']}",
        f"- Price-event hours: {metrics['price_event_rows']}",
        f"- Aggregate precision: {fmt(metrics['precision'])}",
        f"- Aggregate recall: {fmt(metrics['recall'])}",
        f"- Aggregate event lift: {fmt(metrics['aggregate_event_lift'])}",
        f"- Monthly lift range: {fmt(metrics['min_monthly_lift'])} to {fmt(metrics['max_monthly_lift'])}",
        f"- Metrics table: `{metrics_csv}`",
        "",
        "## Monthly price-risk result",
        "",
        "| month | signals | events | TP | FP | FN | precision | recall | lift |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['month']} | {row['signal_rows']} | {row['price_event_rows']} | "
            f"{row['tp']} | {row['fp']} | {row['fn']} | "
            f"{fmt(row['precision'])} | {fmt(row['recall'])} | {fmt(row['event_lift'])} |"
        )

    lines += [
        "",
        "## Readout",
        "",
    ]

    if metrics["all_months_lift_above_one"]:
        lines.append(
            "Signal-positive hours show a higher price-event concentration than the monthly base rate in every reviewed month."
        )
    else:
        lines.append(
            "The signal does not consistently beat the monthly base event rate. This needs review before further use."
        )

    lines += [
        "",
        "The current signal is conservative. That is visible in the low number of signal-positive hours and low recall. The useful point is that when the signal does fire, it is not random relative to price-event behavior.",
        "",
        "## What to ask a reviewer",
        "",
        "1. Does the fundamentals framing make sense for DE-LU power-market stress monitoring?",
        "2. Are the current risk reasons useful, or are they too coarse for trading analytics?",
        "3. Is the price-event definition acceptable as a first ex-post diagnostic?",
        "4. Which layer should come next: forecast error, balancing/imbalance, weather, cross-border flows, or intraday prices?",
        "",
        "## Main files to inspect",
        "",
        "- `reports/cross_month_price_risk_2024-05_to_2024-08.md`",
        "- `dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv`",
        "- `reports/price_risk_behavior_2024-06-01_to_2024-06-30.md`",
        "- `src/prices/cross_month_price_risk.py`",
        "- `src/signals/risk_engine.py`",
        "- `src/features/market_features.py`",
        "",
        "## Caveats",
        "",
        "- Four months are not enough for a robust statistical claim.",
        "- Price events are ex-post labels, not signal inputs.",
        "- The current evaluation checks same-hour alignment, not lead time.",
        "- No P&L, execution, tradability or forecast-skill claim is made.",
        "- The next serious layer should add forecast errors or balancing/imbalance context.",
        "",
    ]

    return "\n".join(lines)


def build(price_risk_csv: str, output_report: str, output_json: str, metrics_csv: str) -> None:
    summary = read_summary(price_risk_csv)
    metrics = aggregate(summary)

    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_csv).parent.mkdir(parents=True, exist_ok=True)

    metric_table(metrics).to_csv(metrics_csv, index=False)
    Path(output_report).write_text(report_text(summary, metrics, metrics_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "source": price_risk_csv,
                "metrics": metrics,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | reviewer-ready report={output_report}")
    print(f"OK | aggregate_event_lift={metrics['aggregate_event_lift']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-risk-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--metrics-csv", required=True)
    args = parser.parse_args()

    build(
        price_risk_csv=args.price_risk_csv,
        output_report=args.output_report,
        output_json=args.output_json,
        metrics_csv=args.metrics_csv,
    )


if __name__ == "__main__":
    main()
