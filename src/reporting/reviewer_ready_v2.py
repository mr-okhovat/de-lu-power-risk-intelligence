from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VERSION = "11D.1"

PRICE_REQUIRED = [
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

LEAD_REQUIRED = [
    "mode",
    "horizon_hours",
    "target_definition",
    "signal_rows",
    "target_event_rows",
    "tp",
    "fp",
    "fn",
    "tn",
    "precision",
    "recall",
    "event_lift",
]


def read_csv(path: str, required: list[str]) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing input file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    return df


def safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return float(a / b)


def aggregate_price(summary: pd.DataFrame) -> dict[str, object]:
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

    lift = None
    if precision is not None and base_event_rate:
        lift = precision / base_event_rate

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
        "aggregate_event_lift": lift,
        "min_monthly_lift": float(summary["event_lift"].min()),
        "max_monthly_lift": float(summary["event_lift"].max()),
    }


def lead_row(lead: pd.DataFrame, mode: str, horizon: int) -> dict[str, object] | None:
    subset = lead[
        (lead["mode"] == mode)
        & (lead["horizon_hours"] == horizon)
    ]

    if subset.empty:
        return None

    return subset.iloc[0].to_dict()


def lead_summary(lead: pd.DataFrame) -> dict[str, object]:
    same_hour = lead_row(lead, "exact_hour", 0)
    next_1h = lead_row(lead, "exact_hour", 1)
    next_3h_window = lead_row(lead, "future_window", 3)
    next_6h_window = lead_row(lead, "future_window", 6)

    return {
        "same_hour": same_hour,
        "next_1h": next_1h,
        "next_3h_window": next_3h_window,
        "next_6h_window": next_6h_window,
    }


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"

    if isinstance(value, float):
        return f"{value:.{digits}f}"

    return str(value)


def lead_lift(item: dict[str, object] | None) -> object:
    if item is None:
        return None
    return item.get("event_lift")


def lead_readout(lead: dict[str, object]) -> str:
    same = lead_lift(lead["same_hour"])
    w3 = lead_lift(lead["next_3h_window"])

    if w3 is not None and w3 > 1.25:
        return "Lead-time check shows some forward-window event concentration, especially within the next 3 hours. This is still not forecast skill and needs longer-window validation."

    if same is not None and same > 1:
        return "The signal is stronger as a same-hour diagnostic than as an early-warning signal. Treat it as a market stress diagnostic for now."

    return "Lead-time behavior is weak. The current signal should be treated as diagnostic, not predictive."


def metrics_table(price: dict[str, object], lead: dict[str, object]) -> pd.DataFrame:
    rows = [
        {"metric": "months", "value": price["months"]},
        {"metric": "rows", "value": price["rows"]},
        {"metric": "signal_rows", "value": price["signal_rows"]},
        {"metric": "price_event_rows", "value": price["price_event_rows"]},
        {"metric": "aggregate_precision", "value": price["precision"]},
        {"metric": "aggregate_recall", "value": price["recall"]},
        {"metric": "aggregate_event_lift", "value": price["aggregate_event_lift"]},
        {"metric": "min_monthly_lift", "value": price["min_monthly_lift"]},
        {"metric": "max_monthly_lift", "value": price["max_monthly_lift"]},
    ]

    for key in ["same_hour", "next_1h", "next_3h_window", "next_6h_window"]:
        item = lead[key]
        if item is None:
            rows.append({"metric": f"{key}_event_lift", "value": None})
        else:
            rows.append({"metric": f"{key}_event_lift", "value": item.get("event_lift")})
            rows.append({"metric": f"{key}_precision", "value": item.get("precision")})
            rows.append({"metric": f"{key}_recall", "value": item.get("recall")})

    return pd.DataFrame(rows)


def report_text(
    price_summary: pd.DataFrame,
    lead_aggregate: pd.DataFrame,
    price: dict[str, object],
    lead: dict[str, object],
    metrics_csv: str,
) -> str:
    lines = [
        "# Reviewer-ready v2",
        "",
        f"Version: {VERSION}",
        "",
        "## What this is",
        "",
        "A reproducible public-data analytics prototype for DE-LU power-market risk intelligence.",
        "",
        "The project ingests SMARD/Bundesnetzagentur data, builds hourly market features, creates an explainable fundamentals risk signal, adds day-ahead price-event labels, checks cross-month signal-vs-price-event behavior, and now adds lead-time diagnostics.",
        "",
        "It is not a trading system, not a price forecast, and not a P&L backtest.",
        "",
        "## Current evidence",
        "",
        f"- Months reviewed: {price['months']}",
        f"- Rows reviewed: {price['rows']}",
        f"- Signal-positive hours: {price['signal_rows']}",
        f"- Price-event hours: {price['price_event_rows']}",
        f"- Aggregate precision: {fmt(price['precision'])}",
        f"- Aggregate recall: {fmt(price['recall'])}",
        f"- Aggregate same-hour event lift: {fmt(price['aggregate_event_lift'])}",
        f"- Monthly lift range: {fmt(price['min_monthly_lift'])} to {fmt(price['max_monthly_lift'])}",
        f"- Metrics table: `{metrics_csv}`",
        "",
        "## Monthly same-hour result",
        "",
        "| month | signals | events | TP | FP | FN | precision | recall | lift |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in price_summary.to_dict("records"):
        lines.append(
            f"| {row['month']} | {row['signal_rows']} | {row['price_event_rows']} | "
            f"{row['tp']} | {row['fp']} | {row['fn']} | "
            f"{fmt(row['precision'])} | {fmt(row['recall'])} | {fmt(row['event_lift'])} |"
        )

    lines += [
        "",
        "## Lead-time readout",
        "",
        lead_readout(lead),
        "",
        "| target | precision | recall | lift |",
        "|---|---:|---:|---:|",
    ]

    for label, key in [
        ("same hour", "same_hour"),
        ("exact next 1h", "next_1h"),
        ("any event next 3h", "next_3h_window"),
        ("any event next 6h", "next_6h_window"),
    ]:
        item = lead[key]
        if item is None:
            lines.append(f"| {label} | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {label} | {fmt(item.get('precision'))} | "
                f"{fmt(item.get('recall'))} | {fmt(item.get('event_lift'))} |"
            )

    lines += [
        "",
        "## What this means",
        "",
        "The signal is conservative. It fires rarely and recall remains low. The useful point is that signal-positive hours are not random relative to ex-post price-event behavior.",
        "",
        "Lead-time diagnostics clarify whether the signal is only a same-hour stress diagnostic or whether it also carries some forward-window concentration. This should guide the next development step.",
        "",
        "## What to review",
        "",
        "1. Does the fundamentals framing make sense for DE-LU market stress monitoring?",
        "2. Are the current reason codes useful or too coarse?",
        "3. Is the price-event labeling acceptable as a first ex-post diagnostic?",
        "4. Is the lead-time behavior strong enough to justify early-warning development?",
        "5. Should the next layer be forecast error, imbalance/balancing, weather, cross-border flows, or intraday prices?",
        "",
        "## Caveats",
        "",
        "- Four months are not enough for a robust statistical claim.",
        "- Price events are ex-post labels and are not used as signal inputs.",
        "- Lead-time checks are event alignment checks, not tradability tests.",
        "- No P&L, execution, liquidity, forecast skill, or production-readiness claim is made.",
        "",
        "## Main files",
        "",
        "- `reports/lead_time_evaluation_2024-05_to_2024-08.md`",
        "- `dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv`",
        "- `reports/cross_month_price_risk_2024-05_to_2024-08.md`",
        "- `reports/visual_reviewer_pack.md`",
        "- `app/streamlit_app.py`",
        "",
    ]

    return "\n".join(lines)


def readme_section(price: dict[str, object], lead: dict[str, object]) -> str:
    return f"""## Reviewer-ready v2

The current reviewer checkpoint includes both same-hour signal-price evaluation and lead-time diagnostics.

Key points:

- Same-hour aggregate event lift: {fmt(price["aggregate_event_lift"])}
- Aggregate precision: {fmt(price["precision"])}
- Aggregate recall: {fmt(price["recall"])}
- Same-hour lift is useful as a diagnostic readout.
- Lead-time behavior is now explicitly checked before making any early-warning claim.

Lead-time readout:

{lead_readout(lead)}

Main file:

    reports/reviewer_ready_v2.md

"""


def update_readme(price: dict[str, object], lead: dict[str, object]) -> None:
    path = Path("README.md")

    if not path.exists():
        return

    text = path.read_text(encoding="utf-8")
    section = readme_section(price, lead)

    marker = "## Current state"

    if "## Reviewer-ready v2" in text:
        start = text.index("## Reviewer-ready v2")
        next_pos = text.find("\n## ", start + 1)

        if next_pos == -1:
            text = text[:start] + section
        else:
            text = text[:start] + section + text[next_pos + 1:]
    elif marker in text:
        text = text.replace(marker, section + "\n" + marker, 1)
    else:
        text += "\n" + section

    path.write_text(text, encoding="utf-8")


def build(
    *,
    price_csv: str,
    lead_csv: str,
    output_report: str,
    output_json: str,
    metrics_csv: str,
    update_readme_flag: bool,
) -> None:
    price_summary = read_csv(price_csv, PRICE_REQUIRED)
    lead_aggregate = read_csv(lead_csv, LEAD_REQUIRED)

    price = aggregate_price(price_summary)
    lead = lead_summary(lead_aggregate)

    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_csv).parent.mkdir(parents=True, exist_ok=True)

    metrics_table(price, lead).to_csv(metrics_csv, index=False)

    Path(output_report).write_text(
        report_text(price_summary, lead_aggregate, price, lead, metrics_csv),
        encoding="utf-8",
    )

    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "price_csv": price_csv,
                "lead_csv": lead_csv,
                "price": price,
                "lead": lead,
                "lead_readout": lead_readout(lead),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    if update_readme_flag:
        update_readme(price, lead)

    print(f"OK | reviewer-ready v2={output_report}")
    print(f"OK | lead readout={lead_readout(lead)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-csv", required=True)
    parser.add_argument("--lead-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--metrics-csv", required=True)
    parser.add_argument("--update-readme", action="store_true")
    args = parser.parse_args()

    build(
        price_csv=args.price_csv,
        lead_csv=args.lead_csv,
        output_report=args.output_report,
        output_json=args.output_json,
        metrics_csv=args.metrics_csv,
        update_readme_flag=args.update_readme,
    )


if __name__ == "__main__":
    main()
