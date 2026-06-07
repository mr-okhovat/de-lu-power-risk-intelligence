from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


VERSION = "8D.1"

REQUIRED = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "price_eur_per_mwh",
    "risk_score",
    "regime_label",
    "reason_codes",
]


@dataclass(frozen=True)
class PriceEventQuality:
    status: str
    row_count: int
    event_rows: int
    event_share: float
    missing_prices: int
    duplicate_timestamps: int
    negative_price_rows: int
    high_price_rows: int
    low_price_rows: int
    ramp_up_rows: int
    ramp_down_rows: int
    high_price_threshold: float
    low_price_threshold: float
    ramp_abs_threshold: float
    notes: list[str]


def read_panel(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing panel file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def event_thresholds(df: pd.DataFrame, high_q: float, low_q: float, ramp_q: float) -> dict[str, float]:
    price = df["price_eur_per_mwh"]
    ramp_abs = df["price_eur_per_mwh"].diff().abs().dropna()

    return {
        "high_price_threshold": float(price.quantile(high_q)),
        "low_price_threshold": float(price.quantile(low_q)),
        "ramp_abs_threshold": float(ramp_abs.quantile(ramp_q)) if len(ramp_abs) else 0.0,
    }


def row_labels(row: pd.Series, levels: dict[str, float]) -> list[str]:
    labels = []
    price = row["price_eur_per_mwh"]

    if pd.isna(price):
        return labels

    price = float(price)

    if price < 0:
        labels.append("NEGATIVE_PRICE")

    if price >= levels["high_price_threshold"]:
        labels.append("HIGH_PRICE_LEVEL")

    if price <= levels["low_price_threshold"]:
        labels.append("LOW_PRICE_LEVEL")

    ramp = row["price_ramp_eur_per_mwh"]

    if pd.notna(ramp) and levels["ramp_abs_threshold"] > 0:
        ramp = float(ramp)

        if ramp >= levels["ramp_abs_threshold"]:
            labels.append("HIGH_PRICE_RAMP_UP")

        if ramp <= -levels["ramp_abs_threshold"]:
            labels.append("HIGH_PRICE_RAMP_DOWN")

    return labels


def build_events(df: pd.DataFrame, high_q: float, low_q: float, ramp_q: float) -> tuple[pd.DataFrame, dict[str, float]]:
    out = df.copy()
    out["price_ramp_eur_per_mwh"] = out["price_eur_per_mwh"].diff()
    out["price_ramp_abs_eur_per_mwh"] = out["price_ramp_eur_per_mwh"].abs()

    levels = event_thresholds(out, high_q, low_q, ramp_q)
    labels = [row_labels(row, levels) for _, row in out.iterrows()]

    out["price_event_count"] = [len(item) for item in labels]
    out["price_event_labels"] = ["|".join(item) if item else "NO_PRICE_EVENT" for item in labels]
    out["is_price_event"] = out["price_event_count"] > 0
    out["price_event_schema_version"] = VERSION

    return out, levels


def count_label(df: pd.DataFrame, label: str) -> int:
    return int(df["price_event_labels"].str.contains(label, regex=False, na=False).sum())


def check_quality(df: pd.DataFrame, levels: dict[str, float]) -> PriceEventQuality:
    missing_prices = int(df["price_eur_per_mwh"].isna().sum())
    duplicate_timestamps = int(df["timestamp_utc"].duplicated().sum())
    event_rows = int(df["is_price_event"].sum())

    notes = []

    if missing_prices:
        notes.append(f"Missing prices: {missing_prices}.")

    if duplicate_timestamps:
        notes.append(f"Duplicate timestamps: {duplicate_timestamps}.")

    if event_rows == 0:
        notes.append("No price events were created.")

    if not notes:
        notes.append("Price event labels built successfully.")

    status = "PASS" if not (missing_prices or duplicate_timestamps or event_rows == 0) else "CHECK NEEDED"

    return PriceEventQuality(
        status=status,
        row_count=int(len(df)),
        event_rows=event_rows,
        event_share=float(event_rows / len(df)) if len(df) else 0.0,
        missing_prices=missing_prices,
        duplicate_timestamps=duplicate_timestamps,
        negative_price_rows=count_label(df, "NEGATIVE_PRICE"),
        high_price_rows=count_label(df, "HIGH_PRICE_LEVEL"),
        low_price_rows=count_label(df, "LOW_PRICE_LEVEL"),
        ramp_up_rows=count_label(df, "HIGH_PRICE_RAMP_UP"),
        ramp_down_rows=count_label(df, "HIGH_PRICE_RAMP_DOWN"),
        high_price_threshold=levels["high_price_threshold"],
        low_price_threshold=levels["low_price_threshold"],
        ramp_abs_threshold=levels["ramp_abs_threshold"],
        notes=notes,
    )


def report_text(quality: PriceEventQuality, output_csv: str) -> str:
    lines = [
        "# Price event labels",
        "",
        f"Version: {VERSION}",
        f"Status: {quality.status}",
        f"Output: `{output_csv}`",
        "",
        "## Thresholds",
        "",
        f"- High price threshold: {quality.high_price_threshold}",
        f"- Low price threshold: {quality.low_price_threshold}",
        f"- Absolute ramp threshold: {quality.ramp_abs_threshold}",
        "",
        "## Counts",
        "",
        f"- Rows: {quality.row_count}",
        f"- Event rows: {quality.event_rows}",
        f"- Event share: {quality.event_share}",
        f"- Negative price rows: {quality.negative_price_rows}",
        f"- High price rows: {quality.high_price_rows}",
        f"- Low price rows: {quality.low_price_rows}",
        f"- Ramp-up rows: {quality.ramp_up_rows}",
        f"- Ramp-down rows: {quality.ramp_down_rows}",
        "",
        "## Checks",
        "",
        f"- Missing prices: {quality.missing_prices}",
        f"- Duplicate timestamps: {quality.duplicate_timestamps}",
        "",
        "## Notes",
        "",
    ]

    for note in quality.notes:
        lines.append(f"- {note}")

    lines += [
        "",
        "These are ex-post labels. They are used for evaluation, not as signal inputs.",
        "",
    ]

    return "\n".join(lines)


def build(
    panel_file: str,
    output_csv: str,
    output_report: str,
    output_json: str,
    high_q: float,
    low_q: float,
    ramp_q: float,
) -> None:
    panel = read_panel(panel_file)
    events, levels = build_events(panel, high_q, low_q, ramp_q)
    quality = check_quality(events, levels)

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    events.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(quality, output_csv), encoding="utf-8")
    Path(output_json).write_text(json.dumps(asdict(quality), indent=2, sort_keys=True), encoding="utf-8")

    print(f"OK | price event rows={quality.event_rows} | status={quality.status}")
    print(f"OK | output={output_csv}")

    if quality.status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel-file", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--high-q", type=float, default=0.90)
    parser.add_argument("--low-q", type=float, default=0.10)
    parser.add_argument("--ramp-q", type=float, default=0.90)
    args = parser.parse_args()

    build(
        panel_file=args.panel_file,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
        high_q=args.high_q,
        low_q=args.low_q,
        ramp_q=args.ramp_q,
    )


if __name__ == "__main__":
    main()
