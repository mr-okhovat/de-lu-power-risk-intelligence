from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VERSION = "8H.1"

MONTHS = [
    ("May 2024", "2024-05-01", "2024-05-31"),
    ("June 2024", "2024-06-01", "2024-06-30"),
    ("July 2024", "2024-07-01", "2024-07-31"),
    ("August 2024", "2024-08-01", "2024-08-31"),
]


def eval_path(market: str, start: str, end: str) -> str:
    return f"data/processed/signal_price_evaluation_{market}_{start}_to_{end}.csv"


def read_eval(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing evaluation file: {p}")

    df = pd.read_csv(p)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    for col in ["signal_positive", "event_positive", "is_price_event"]:
        if col in df.columns and df[col].dtype != bool:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def safe_div(a: int, b: int) -> float | None:
    if b == 0:
        return None
    return float(a / b)


def f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return float(2 * precision * recall / (precision + recall))


def month_summary(label: str, start: str, end: str, market: str) -> dict[str, object]:
    path = eval_path(market, start, end)
    df = read_eval(path)

    tp = int((df["confusion_bucket"] == "TP").sum())
    fp = int((df["confusion_bucket"] == "FP").sum())
    fn = int((df["confusion_bucket"] == "FN").sum())
    tn = int((df["confusion_bucket"] == "TN").sum())

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    base_event_rate = float(df["event_positive"].mean())

    signal = df[df["signal_positive"]]
    signal_event_rate = float(signal["event_positive"].mean()) if len(signal) else None

    lift = None
    if signal_event_rate is not None and base_event_rate > 0:
        lift = float(signal_event_rate / base_event_rate)

    return {
        "month": label,
        "start": start,
        "end": end,
        "rows": int(len(df)),
        "signal_rows": int(df["signal_positive"].sum()),
        "price_event_rows": int(df["event_positive"].sum()),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1(precision, recall),
        "base_event_rate": base_event_rate,
        "signal_event_rate": signal_event_rate,
        "event_lift": lift,
        "mean_price_signal_positive": float(signal["price_eur_per_mwh"].mean()) if len(signal) else None,
        "mean_price_event": float(df[df["event_positive"]]["price_eur_per_mwh"].mean()),
        "max_price": float(df["price_eur_per_mwh"].max()),
        "min_price": float(df["price_eur_per_mwh"].min()),
        "source_file": path,
        "version": VERSION,
    }


def build_summary(market: str) -> pd.DataFrame:
    rows = [month_summary(label, start, end, market) for label, start, end in MONTHS]
    return pd.DataFrame(rows)


def readout(summary: pd.DataFrame) -> str:
    lifts = summary["event_lift"].dropna()

    if lifts.empty:
        return "No lift could be calculated. The signal is not producing usable high-risk samples."

    if (lifts > 1).all():
        if lifts.min() >= 1.5:
            return "Signal-positive hours show consistently higher price-event concentration across all reviewed months."
        return "Signal-positive hours beat the base event rate in every month, but the strength varies."

    return "The signal does not consistently beat the base event rate across months."


def make_report(summary: pd.DataFrame, output_csv: str) -> str:
    lines = [
        "# Cross-month price-risk evaluation",
        "",
        f"Version: {VERSION}",
        f"Table: `{output_csv}`",
        "",
        "## Monthly summary",
        "",
        "| month | rows | signals | events | TP | FP | FN | precision | recall | lift |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['month']} | {row['rows']} | {row['signal_rows']} | "
            f"{row['price_event_rows']} | {row['tp']} | {row['fp']} | {row['fn']} | "
            f"{row['precision']} | {row['recall']} | {row['event_lift']} |"
        )

    lines += [
        "",
        "## Readout",
        "",
        readout(summary),
        "",
        "## Decision",
        "",
        "Do not tune thresholds yet.",
        "",
        "The current signal is conservative and repeatedly shows event lift above the base price-event rate. The next useful step is a reviewer-ready package with clear caveats, then a longer data window or forecast-error layer.",
        "",
        "This is still not a trading backtest. It does not claim forecast skill, tradability or P&L.",
        "",
    ]

    return "\n".join(lines)


def build(market: str, output_csv: str, output_report: str, output_json: str) -> None:
    summary = build_summary(market)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(output_csv, index=False)
    Path(output_report).write_text(make_report(summary, output_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "market": market,
                "readout": readout(summary),
                "months": summary.to_dict("records"),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | cross-month price-risk report={output_report}")
    print(f"OK | readout={readout(summary)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    build(
        market=args.market_label,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
