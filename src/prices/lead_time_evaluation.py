from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VERSION = "11A.1"

MONTHS = [
    ("May 2024", "2024-05-01", "2024-05-31"),
    ("June 2024", "2024-06-01", "2024-06-30"),
    ("July 2024", "2024-07-01", "2024-07-31"),
    ("August 2024", "2024-08-01", "2024-08-31"),
]

REQUIRED = [
    "timestamp_utc",
    "signal_positive",
    "event_positive",
    "price_eur_per_mwh",
    "risk_score",
    "confusion_bucket",
]


def eval_path(market: str, start: str, end: str) -> str:
    return f"data/processed/signal_price_evaluation_{market}_{start}_to_{end}.csv"


def read_eval(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing evaluation file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    for col in ["signal_positive", "event_positive"]:
        if df[col].dtype != bool:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def safe_div(a: int | float, b: int | float) -> float | None:
    if b == 0:
        return None
    return float(a / b)


def metrics(rows: int, signals: int, targets: int, tp: int, fp: int, fn: int, tn: int) -> dict[str, object]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    base_rate = safe_div(targets, rows)
    signal_event_rate = precision

    lift = None
    if base_rate and signal_event_rate is not None:
        lift = signal_event_rate / base_rate

    return {
        "rows": int(rows),
        "signal_rows": int(signals),
        "target_event_rows": int(targets),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "precision": precision,
        "recall": recall,
        "base_event_rate": base_rate,
        "signal_event_rate": signal_event_rate,
        "event_lift": lift,
    }


def score_target(df: pd.DataFrame, target: pd.Series) -> dict[str, object]:
    signal = df["signal_positive"].astype(bool)
    target = target.astype(bool)

    tp = int((signal & target).sum())
    fp = int((signal & ~target).sum())
    fn = int((~signal & target).sum())
    tn = int((~signal & ~target).sum())

    return metrics(
        rows=len(df),
        signals=int(signal.sum()),
        targets=int(target.sum()),
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
    )


def exact_target(df: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    if horizon == 0:
        return df.copy(), df["event_positive"].copy()

    work = df.iloc[:-horizon].copy()
    target = df["event_positive"].shift(-horizon).iloc[:-horizon].fillna(False)

    return work, target


def future_window_target(df: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    if horizon <= 0:
        raise ValueError("Future window horizon must be positive.")

    target = pd.Series(False, index=df.index)

    for step in range(1, horizon + 1):
        target = target | df["event_positive"].shift(-step, fill_value=False)

    work = df.iloc[:-horizon].copy()
    target = target.iloc[:-horizon]

    return work, target


def monthly_rows(label: str, start: str, end: str, market: str) -> list[dict[str, object]]:
    df = read_eval(eval_path(market, start, end))
    rows = []

    for horizon in [0, 1, 2, 3, 6]:
        work, target = exact_target(df, horizon)
        out = score_target(work, target)
        out.update(
            {
                "month": label,
                "start": start,
                "end": end,
                "mode": "exact_hour",
                "horizon_hours": horizon,
                "target_definition": f"event_at_t_plus_{horizon}",
                "version": VERSION,
            }
        )
        rows.append(out)

    for horizon in [1, 3, 6, 12]:
        work, target = future_window_target(df, horizon)
        out = score_target(work, target)
        out.update(
            {
                "month": label,
                "start": start,
                "end": end,
                "mode": "future_window",
                "horizon_hours": horizon,
                "target_definition": f"any_event_next_{horizon}h",
                "version": VERSION,
            }
        )
        rows.append(out)

    return rows


def aggregate(summary: pd.DataFrame) -> pd.DataFrame:
    keys = ["mode", "horizon_hours", "target_definition"]
    count_cols = ["rows", "signal_rows", "target_event_rows", "tp", "fp", "fn", "tn"]

    grouped = summary.groupby(keys, as_index=False)[count_cols].sum()
    rows = []

    for row in grouped.to_dict("records"):
        out = metrics(
            rows=row["rows"],
            signals=row["signal_rows"],
            targets=row["target_event_rows"],
            tp=row["tp"],
            fp=row["fp"],
            fn=row["fn"],
            tn=row["tn"],
        )
        out.update(
            {
                "month": "All months",
                "start": "2024-05-01",
                "end": "2024-08-31",
                "mode": row["mode"],
                "horizon_hours": row["horizon_hours"],
                "target_definition": row["target_definition"],
                "version": VERSION,
            }
        )
        rows.append(out)

    return pd.DataFrame(rows)


def build_summary(market: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []

    for label, start, end in MONTHS:
        rows.extend(monthly_rows(label, start, end, market))

    monthly = pd.DataFrame(rows)
    all_months = aggregate(monthly)

    return monthly, all_months


def readout(aggregate_df: pd.DataFrame) -> str:
    same_hour = aggregate_df[
        (aggregate_df["mode"] == "exact_hour") & (aggregate_df["horizon_hours"] == 0)
    ]

    future_3h = aggregate_df[
        (aggregate_df["mode"] == "future_window") & (aggregate_df["horizon_hours"] == 3)
    ]

    if same_hour.empty or future_3h.empty:
        return "Lead-time readout could not be calculated."

    same_lift = same_hour.iloc[0]["event_lift"]
    future_lift = future_3h.iloc[0]["event_lift"]

    if future_lift is not None and future_lift > 1.25:
        return "The signal keeps some forward-looking event concentration in the next 3 hours, but this still needs longer-window validation."

    if same_lift is not None and same_lift > 1 and (future_lift is None or future_lift <= 1.25):
        return "The signal is stronger as a same-hour diagnostic than as a forward-looking early-warning signal."

    return "The lead-time behavior is weak. Treat the current signal as diagnostic, not predictive."


def make_report(monthly: pd.DataFrame, aggregate_df: pd.DataFrame, monthly_csv: str, aggregate_csv: str) -> str:
    lines = [
        "# Lead-time evaluation",
        "",
        f"Version: {VERSION}",
        "",
        "## Purpose",
        "",
        "This checks whether the current fundamentals signal has any forward-looking relationship with price events.",
        "",
        "Same-hour alignment was already tested. This report adds exact future-hour checks and forward-window checks.",
        "",
        "## Output tables",
        "",
        f"- Monthly table: `{monthly_csv}`",
        f"- Aggregate table: `{aggregate_csv}`",
        "",
        "## Aggregate lead-time summary",
        "",
        "| mode | horizon | target | signals | target events | precision | recall | lift |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]

    for row in aggregate_df.sort_values(["mode", "horizon_hours"]).to_dict("records"):
        lines.append(
            f"| {row['mode']} | {row['horizon_hours']} | {row['target_definition']} | "
            f"{row['signal_rows']} | {row['target_event_rows']} | "
            f"{row['precision']} | {row['recall']} | {row['event_lift']} |"
        )

    lines += [
        "",
        "## Readout",
        "",
        readout(aggregate_df),
        "",
        "## Caveat",
        "",
        "This is still not a trading backtest. It does not include forecast revisions, execution timing, liquidity, imbalance settlement or P&L.",
        "",
    ]

    return "\n".join(lines)


def build(market: str, monthly_csv: str, aggregate_csv: str, output_report: str, output_json: str) -> None:
    monthly, aggregate_df = build_summary(market)

    Path(monthly_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(aggregate_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    monthly.to_csv(monthly_csv, index=False)
    aggregate_df.to_csv(aggregate_csv, index=False)

    Path(output_report).write_text(
        make_report(monthly, aggregate_df, monthly_csv, aggregate_csv),
        encoding="utf-8",
    )

    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "market": market,
                "readout": readout(aggregate_df),
                "monthly_csv": monthly_csv,
                "aggregate_csv": aggregate_csv,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | lead-time report={output_report}")
    print(f"OK | readout={readout(aggregate_df)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--monthly-csv", required=True)
    parser.add_argument("--aggregate-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    build(
        market=args.market_label,
        monthly_csv=args.monthly_csv,
        aggregate_csv=args.aggregate_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
