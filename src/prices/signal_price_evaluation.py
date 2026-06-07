from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


VERSION = "8E.1"

REQUIRED = [
    "timestamp_utc",
    "price_eur_per_mwh",
    "price_ramp_eur_per_mwh",
    "risk_score",
    "regime_label",
    "reason_codes",
    "is_price_event",
    "price_event_labels",
]


@dataclass(frozen=True)
class Metrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    precision: float | None
    recall: float | None
    f1_score: float | None
    signal_rate: float
    event_rate: float


@dataclass(frozen=True)
class EvaluationQuality:
    status: str
    row_count: int
    signal_threshold: float
    price_event_rows: int
    signal_rows: int
    duplicate_timestamps: int
    missing_price_rows: int
    missing_risk_rows: int
    metrics: Metrics
    notes: list[str]


def read_events(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing input file: {p}")

    df = pd.read_csv(p)

    missing = [col for col in REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    if df["is_price_event"].dtype != bool:
        df["is_price_event"] = df["is_price_event"].astype(str).str.lower().isin(["true", "1", "yes"])

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def safe_div(a: int, b: int) -> float | None:
    if b == 0:
        return None
    return float(a / b)


def f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return None
    return float(2 * precision * recall / (precision + recall))


def classify(row: pd.Series) -> str:
    signal = bool(row["signal_positive"])
    event = bool(row["event_positive"])

    if signal and event:
        return "TP"
    if signal and not event:
        return "FP"
    if not signal and event:
        return "FN"
    return "TN"


def evaluate(df: pd.DataFrame, signal_threshold: float) -> pd.DataFrame:
    out = df.copy()
    out["signal_positive"] = out["risk_score"] >= signal_threshold
    out["event_positive"] = out["is_price_event"]
    out["confusion_bucket"] = out.apply(classify, axis=1)
    out["signal_price_eval_version"] = VERSION
    return out


def compute_metrics(df: pd.DataFrame) -> Metrics:
    tp = int((df["confusion_bucket"] == "TP").sum())
    fp = int((df["confusion_bucket"] == "FP").sum())
    tn = int((df["confusion_bucket"] == "TN").sum())
    fn = int((df["confusion_bucket"] == "FN").sum())

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)

    rows = len(df)

    return Metrics(
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        precision=precision,
        recall=recall,
        f1_score=f1(precision, recall),
        signal_rate=float((tp + fp) / rows) if rows else 0.0,
        event_rate=float((tp + fn) / rows) if rows else 0.0,
    )


def confusion_table(metrics: Metrics) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"bucket": "TP", "signal_positive": True, "price_event": True, "count": metrics.true_positive},
            {"bucket": "FP", "signal_positive": True, "price_event": False, "count": metrics.false_positive},
            {"bucket": "FN", "signal_positive": False, "price_event": True, "count": metrics.false_negative},
            {"bucket": "TN", "signal_positive": False, "price_event": False, "count": metrics.true_negative},
        ]
    )


def event_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    labels = sorted(
        {
            label
            for value in df["price_event_labels"].dropna()
            for label in str(value).split("|")
            if label and label != "NO_PRICE_EVENT"
        }
    )

    for label in labels:
        mask = df["price_event_labels"].str.contains(label, regex=False, na=False)
        subset = df[mask]

        rows.append(
            {
                "price_event_label": label,
                "rows": int(len(subset)),
                "signal_positive_rows": int(subset["signal_positive"].sum()),
                "mean_risk_score": float(subset["risk_score"].mean()) if len(subset) else None,
                "mean_price_eur_per_mwh": float(subset["price_eur_per_mwh"].mean()) if len(subset) else None,
                "version": VERSION,
            }
        )

    return pd.DataFrame(rows)


def check_quality(df: pd.DataFrame, signal_threshold: float, metrics: Metrics) -> EvaluationQuality:
    duplicate_timestamps = int(df["timestamp_utc"].duplicated().sum())
    missing_price_rows = int(df["price_eur_per_mwh"].isna().sum())
    missing_risk_rows = int(df["risk_score"].isna().sum())

    notes = []

    if duplicate_timestamps:
        notes.append(f"Duplicate timestamps: {duplicate_timestamps}.")

    if missing_price_rows:
        notes.append(f"Missing price rows: {missing_price_rows}.")

    if missing_risk_rows:
        notes.append(f"Missing risk rows: {missing_risk_rows}.")

    if metrics.true_positive == 0:
        notes.append("No direct overlap between high risk signals and price events in this window.")

    if metrics.false_positive > metrics.true_positive:
        notes.append("More high-risk hours occurred without price events than with price events. This may be acceptable for a fundamentals stress proxy, but it needs review.")

    if not notes:
        notes.append("Signal-price evaluation completed without blocking data quality issues.")

    blocking = duplicate_timestamps > 0 or missing_price_rows > 0 or missing_risk_rows > 0

    return EvaluationQuality(
        status="PASS" if not blocking else "CHECK NEEDED",
        row_count=int(len(df)),
        signal_threshold=signal_threshold,
        price_event_rows=int(df["event_positive"].sum()),
        signal_rows=int(df["signal_positive"].sum()),
        duplicate_timestamps=duplicate_timestamps,
        missing_price_rows=missing_price_rows,
        missing_risk_rows=missing_risk_rows,
        metrics=metrics,
        notes=notes,
    )


def report_text(quality: EvaluationQuality, evaluation_csv: str, confusion_csv: str, event_summary_csv: str) -> str:
    m = quality.metrics

    lines = [
        "# Signal vs price-event evaluation",
        "",
        f"Version: {VERSION}",
        f"Status: {quality.status}",
        f"Evaluation table: `{evaluation_csv}`",
        f"Confusion table: `{confusion_csv}`",
        f"Event summary: `{event_summary_csv}`",
        "",
        "## Setup",
        "",
        f"- Rows: {quality.row_count}",
        f"- Signal threshold: {quality.signal_threshold}",
        f"- Price-event rows: {quality.price_event_rows}",
        f"- Signal-positive rows: {quality.signal_rows}",
        "",
        "## Metrics",
        "",
        f"- True positives: {m.true_positive}",
        f"- False positives: {m.false_positive}",
        f"- True negatives: {m.true_negative}",
        f"- False negatives: {m.false_negative}",
        f"- Precision: {m.precision}",
        f"- Recall: {m.recall}",
        f"- F1 score: {m.f1_score}",
        f"- Signal rate: {m.signal_rate}",
        f"- Event rate: {m.event_rate}",
        "",
        "## Data checks",
        "",
        f"- Duplicate timestamps: {quality.duplicate_timestamps}",
        f"- Missing price rows: {quality.missing_price_rows}",
        f"- Missing risk rows: {quality.missing_risk_rows}",
        "",
        "## Readout",
        "",
    ]

    if m.true_positive == 0:
        lines.append("The current high-risk signal does not overlap with the selected price-event labels in this window.")
    elif m.precision is not None and m.precision < 0.25:
        lines.append("Overlap exists, but precision is low. The fundamentals signal may capture stress conditions that do not always become price events.")
    else:
        lines.append("There is some alignment between high-risk fundamentals and price events. This needs a longer-window check before interpretation.")

    lines += [
        "",
        "## Notes",
        "",
    ]

    for note in quality.notes:
        lines.append(f"- {note}")

    lines += [
        "",
        "This is an ex-post alignment check, not a trading backtest. No P&L or predictability claim is made here.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    input_file: str,
    output_csv: str,
    output_report: str,
    output_json: str,
    confusion_csv: str,
    event_summary_csv: str,
    signal_threshold: float,
) -> None:
    source = read_events(input_file)
    evaluated = evaluate(source, signal_threshold)
    metrics = compute_metrics(evaluated)
    quality = check_quality(evaluated, signal_threshold, metrics)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(confusion_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(event_summary_csv).parent.mkdir(parents=True, exist_ok=True)

    evaluated.to_csv(output_csv, index=False)
    confusion_table(metrics).to_csv(confusion_csv, index=False)
    event_type_summary(evaluated).to_csv(event_summary_csv, index=False)

    Path(output_report).write_text(
        report_text(quality, output_csv, confusion_csv, event_summary_csv),
        encoding="utf-8",
    )

    Path(output_json).write_text(
        json.dumps(asdict(quality), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | signal-price evaluation rows={quality.row_count} | status={quality.status}")
    print(f"OK | report={output_report}")

    if quality.status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--confusion-csv", required=True)
    parser.add_argument("--event-summary-csv", required=True)
    parser.add_argument("--signal-threshold", type=float, default=60.0)
    args = parser.parse_args()

    build(
        input_file=args.input_file,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
        confusion_csv=args.confusion_csv,
        event_summary_csv=args.event_summary_csv,
        signal_threshold=args.signal_threshold,
    )


if __name__ == "__main__":
    main()
