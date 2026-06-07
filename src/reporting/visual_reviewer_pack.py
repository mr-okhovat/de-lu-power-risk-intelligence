from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


VERSION = "9A.1"

CROSS_MONTH_REQUIRED = [
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
    "base_event_rate",
    "signal_event_rate",
    "event_lift",
]

EVAL_REQUIRED = [
    "timestamp_utc",
    "price_eur_per_mwh",
    "risk_score",
    "signal_positive",
    "event_positive",
    "confusion_bucket",
]


def read_cross_month(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing cross-month file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in CROSS_MONTH_REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    return df


def read_evaluation(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing evaluation file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in EVAL_REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    for col in ["signal_positive", "event_positive"]:
        if df[col].dtype != bool:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return float(a / b)


def aggregate_metrics(df: pd.DataFrame) -> dict[str, object]:
    rows = int(df["rows"].sum())
    signals = int(df["signal_rows"].sum())
    events = int(df["price_event_rows"].sum())
    tp = int(df["tp"].sum())
    fp = int(df["fp"].sum())
    fn = int(df["fn"].sum())
    tn = int(df["tn"].sum())

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    base_rate = safe_div(events, rows)
    signal_event_rate = precision

    lift = None
    if base_rate and signal_event_rate is not None:
        lift = signal_event_rate / base_rate

    return {
        "months": int(len(df)),
        "rows": rows,
        "signal_positive_hours": signals,
        "price_event_hours": events,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "base_event_rate": base_rate,
        "signal_event_rate": signal_event_rate,
        "aggregate_event_lift": lift,
        "monthly_lift_min": float(df["event_lift"].min()),
        "monthly_lift_max": float(df["event_lift"].max()),
    }


def metrics_table(metrics: dict[str, object]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"metric": key, "value": value} for key, value in metrics.items()]
    )


def save(fig: plt.Figure, path: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def plot_monthly_lift(df: pd.DataFrame, path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["month"], df["event_lift"], marker="o")
    ax.axhline(1.0, linewidth=1, linestyle="--")
    ax.set_title("Monthly event lift")
    ax.set_ylabel("Lift vs monthly base event rate")
    ax.set_xlabel("Month")
    ax.grid(True, alpha=0.3)
    save(fig, path)


def plot_precision_recall(df: pd.DataFrame, path: str) -> None:
    plot_df = df[["month", "precision", "recall"]].set_index("month")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    plot_df.plot(kind="bar", ax=ax)
    ax.set_title("Precision and recall by month")
    ax.set_ylabel("Rate")
    ax.set_xlabel("Month")
    ax.set_ylim(0, 1)
    ax.grid(True, axis="y", alpha=0.3)
    save(fig, path)


def plot_signal_vs_event_rate(df: pd.DataFrame, path: str) -> None:
    plot_df = df[["month", "base_event_rate", "signal_event_rate"]].set_index("month")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    plot_df.plot(marker="o", ax=ax)
    ax.set_title("Base event rate vs signal-positive event rate")
    ax.set_ylabel("Rate")
    ax.set_xlabel("Month")
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    save(fig, path)


def plot_confusion(df: pd.DataFrame, path: str) -> None:
    plot_df = df[["month", "tp", "fp", "fn"]].set_index("month")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    plot_df.plot(kind="bar", ax=ax)
    ax.set_title("Signal-price confusion buckets")
    ax.set_ylabel("Rows")
    ax.set_xlabel("Month")
    ax.grid(True, axis="y", alpha=0.3)
    save(fig, path)


def plot_june_timeline(df: pd.DataFrame, path: str) -> None:
    fig, ax_price = plt.subplots(figsize=(11, 4.8))

    ax_price.plot(df["timestamp_utc"], df["price_eur_per_mwh"], linewidth=1.2, label="Day-ahead price")
    ax_price.set_title("June 2024 price and risk timeline")
    ax_price.set_ylabel("EUR/MWh")
    ax_price.grid(True, alpha=0.3)

    signal = df[df["signal_positive"]]
    event = df[df["event_positive"]]

    ax_price.scatter(event["timestamp_utc"], event["price_eur_per_mwh"], marker=".", label="Price event")
    ax_price.scatter(signal["timestamp_utc"], signal["price_eur_per_mwh"], marker="x", label="Signal positive")

    ax_risk = ax_price.twinx()
    ax_risk.plot(df["timestamp_utc"], df["risk_score"], linewidth=1.0, alpha=0.6, label="Risk score")
    ax_risk.set_ylabel("Risk score")

    h1, l1 = ax_price.get_legend_handles_labels()
    h2, l2 = ax_risk.get_legend_handles_labels()
    ax_price.legend(h1 + h2, l1 + l2, loc="upper left")

    save(fig, path)


def figure_paths(fig_dir: str) -> dict[str, str]:
    base = Path(fig_dir)

    return {
        "monthly_lift": str(base / "monthly_event_lift.png"),
        "precision_recall": str(base / "precision_recall.png"),
        "signal_vs_event_rate": str(base / "signal_vs_event_rate.png"),
        "confusion": str(base / "confusion_summary.png"),
        "june_timeline": str(base / "june_price_risk_timeline.png"),
    }


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def report_text(metrics: dict[str, object], figures: dict[str, str], summary_csv: str) -> str:
    lines = [
        "# Visual reviewer pack",
        "",
        f"Version: {VERSION}",
        "",
        "## Current read",
        "",
        "The current fundamentals signal is conservative. It fires rarely, but signal-positive hours show higher ex-post price-event concentration than the monthly base rate across the reviewed months.",
        "",
        "This is still not a trading model, price forecast, or P&L backtest.",
        "",
        "## Key metrics",
        "",
        f"- Months: {metrics['months']}",
        f"- Rows: {metrics['rows']}",
        f"- Signal-positive hours: {metrics['signal_positive_hours']}",
        f"- Price-event hours: {metrics['price_event_hours']}",
        f"- Aggregate precision: {fmt(metrics['precision'])}",
        f"- Aggregate recall: {fmt(metrics['recall'])}",
        f"- Aggregate event lift: {fmt(metrics['aggregate_event_lift'])}",
        f"- Monthly lift range: {fmt(metrics['monthly_lift_min'])} to {fmt(metrics['monthly_lift_max'])}",
        f"- Summary CSV: `{summary_csv}`",
        "",
        "## Figures",
        "",
        f"![Monthly event lift]({figures['monthly_lift']})",
        "",
        f"![Precision and recall]({figures['precision_recall']})",
        "",
        f"![Base event rate vs signal-positive event rate]({figures['signal_vs_event_rate']})",
        "",
        f"![Confusion summary]({figures['confusion']})",
        "",
        f"![June price-risk timeline]({figures['june_timeline']})",
        "",
        "## Caveat",
        "",
        "The figures show ex-post alignment, not forecast skill. The next serious step should test lead time and add forecast-error or balancing/imbalance context.",
        "",
    ]

    return "\n".join(lines)


def build(
    cross_month_csv: str,
    june_evaluation_csv: str,
    fig_dir: str,
    output_report: str,
    output_json: str,
    summary_csv: str,
) -> None:
    cross = read_cross_month(cross_month_csv)
    june = read_evaluation(june_evaluation_csv)

    figures = figure_paths(fig_dir)
    metrics = aggregate_metrics(cross)

    plot_monthly_lift(cross, figures["monthly_lift"])
    plot_precision_recall(cross, figures["precision_recall"])
    plot_signal_vs_event_rate(cross, figures["signal_vs_event_rate"])
    plot_confusion(cross, figures["confusion"])
    plot_june_timeline(june, figures["june_timeline"])

    Path(summary_csv).parent.mkdir(parents=True, exist_ok=True)
    metrics_table(metrics).to_csv(summary_csv, index=False)

    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    Path(output_report).write_text(report_text(metrics, figures, summary_csv), encoding="utf-8")
    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "cross_month_csv": cross_month_csv,
                "june_evaluation_csv": june_evaluation_csv,
                "metrics": metrics,
                "figures": figures,
                "summary_csv": summary_csv,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | visual reviewer pack={output_report}")
    print(f"OK | figures={fig_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cross-month-csv", required=True)
    parser.add_argument("--june-evaluation-csv", required=True)
    parser.add_argument("--fig-dir", default="reports/figures")
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--summary-csv", required=True)
    args = parser.parse_args()

    build(
        cross_month_csv=args.cross_month_csv,
        june_evaluation_csv=args.june_evaluation_csv,
        fig_dir=args.fig_dir,
        output_report=args.output_report,
        output_json=args.output_json,
        summary_csv=args.summary_csv,
    )


if __name__ == "__main__":
    main()
