from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


VERSION = "8C.1"

FEATURE_REQUIRED = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "total_load_mw",
    "residual_load_official_mw",
    "renewable_generation_mw",
    "renewable_share",
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
]

PRICE_REQUIRED = [
    "timestamp_utc",
    "price_eur_per_mwh",
    "price_filter_id",
]

RISK_REQUIRED = [
    "timestamp_utc",
    "risk_score",
    "regime_label",
    "reason_codes",
]


@dataclass(frozen=True)
class PanelQuality:
    status: str
    row_count: int
    feature_rows: int
    price_rows: int
    risk_rows: int
    missing_price_rows: int
    missing_risk_rows: int
    duplicate_timestamps: int
    min_price: float | None
    max_price: float | None
    mean_price: float | None
    max_risk_score: float | None
    high_risk_rows: int
    notes: list[str]


def read_csv(path: str, required: list[str]) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing input file: {p}")

    df = pd.read_csv(p)

    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def build_panel(features: pd.DataFrame, prices: pd.DataFrame, risks: pd.DataFrame) -> pd.DataFrame:
    price_cols = [
        "timestamp_utc",
        "price_eur_per_mwh",
        "price_filter_id",
    ]

    risk_cols = [
        "timestamp_utc",
        "risk_score",
        "regime_label",
        "reason_codes",
    ]

    out = features.merge(prices[price_cols], on="timestamp_utc", how="left")
    out = out.merge(risks[risk_cols], on="timestamp_utc", how="left")

    out["price_risk_panel_version"] = VERSION

    front = [
        "timestamp_utc",
        "timestamp_local",
        "market_label",
        "smard_region",
        "price_eur_per_mwh",
        "risk_score",
        "regime_label",
        "reason_codes",
    ]

    rest = [col for col in out.columns if col not in front]

    return out[front + rest].reset_index(drop=True)


def check_panel(panel: pd.DataFrame, feature_rows: int, price_rows: int, risk_rows: int) -> PanelQuality:
    missing_price_rows = int(panel["price_eur_per_mwh"].isna().sum())
    missing_risk_rows = int(panel["risk_score"].isna().sum())
    duplicate_timestamps = int(panel["timestamp_utc"].duplicated().sum())
    high_risk_rows = int((panel["risk_score"] >= 60).sum())

    notes = []

    if len(panel) != feature_rows:
        notes.append(f"Panel rows differ from feature rows: panel={len(panel)}, features={feature_rows}.")

    if missing_price_rows:
        notes.append(f"Rows without price: {missing_price_rows}.")

    if missing_risk_rows:
        notes.append(f"Rows without risk signal: {missing_risk_rows}.")

    if duplicate_timestamps:
        notes.append(f"Duplicate timestamps: {duplicate_timestamps}.")

    if not notes:
        notes.append("Panel join passed. Features, prices and risk signals align hourly.")

    blocking = (
        len(panel) != feature_rows
        or missing_price_rows > 0
        or missing_risk_rows > 0
        or duplicate_timestamps > 0
    )

    return PanelQuality(
        status="PASS" if not blocking else "CHECK NEEDED",
        row_count=int(len(panel)),
        feature_rows=int(feature_rows),
        price_rows=int(price_rows),
        risk_rows=int(risk_rows),
        missing_price_rows=missing_price_rows,
        missing_risk_rows=missing_risk_rows,
        duplicate_timestamps=duplicate_timestamps,
        min_price=None if len(panel) == 0 else float(panel["price_eur_per_mwh"].min()),
        max_price=None if len(panel) == 0 else float(panel["price_eur_per_mwh"].max()),
        mean_price=None if len(panel) == 0 else float(panel["price_eur_per_mwh"].mean()),
        max_risk_score=None if len(panel) == 0 else float(panel["risk_score"].max()),
        high_risk_rows=high_risk_rows,
        notes=notes,
    )


def report_text(quality: PanelQuality, output_csv: str) -> str:
    lines = [
        "# Price-risk panel quality",
        "",
        f"Version: {VERSION}",
        f"Status: {quality.status}",
        f"Output: `{output_csv}`",
        "",
        "## Join checks",
        "",
        f"- Panel rows: {quality.row_count}",
        f"- Feature rows: {quality.feature_rows}",
        f"- Price rows: {quality.price_rows}",
        f"- Risk rows: {quality.risk_rows}",
        f"- Missing price rows: {quality.missing_price_rows}",
        f"- Missing risk rows: {quality.missing_risk_rows}",
        f"- Duplicate timestamps: {quality.duplicate_timestamps}",
        "",
        "## First read",
        "",
        f"- Min price EUR/MWh: {quality.min_price}",
        f"- Max price EUR/MWh: {quality.max_price}",
        f"- Mean price EUR/MWh: {quality.mean_price}",
        f"- Max risk score: {quality.max_risk_score}",
        f"- High-risk rows: {quality.high_risk_rows}",
        "",
        "## Notes",
        "",
    ]

    for note in quality.notes:
        lines.append(f"- {note}")

    lines += [
        "",
        "This file is the first combined panel for price-aware analysis. It is not yet an event study or a backtest.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    feature_file: str,
    price_file: str,
    risk_file: str,
    output_csv: str,
    output_report: str,
    output_json: str,
) -> None:
    features = read_csv(feature_file, FEATURE_REQUIRED)
    prices = read_csv(price_file, PRICE_REQUIRED)
    risks = read_csv(risk_file, RISK_REQUIRED)

    panel = build_panel(features, prices, risks)
    quality = check_panel(panel, len(features), len(prices), len(risks))

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    panel.to_csv(output_csv, index=False)
    Path(output_report).write_text(report_text(quality, output_csv), encoding="utf-8")
    Path(output_json).write_text(json.dumps(asdict(quality), indent=2, sort_keys=True), encoding="utf-8")

    print(f"OK | panel rows={quality.row_count} | status={quality.status}")
    print(f"OK | output={output_csv}")

    if quality.status != "PASS":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-file", required=True)
    parser.add_argument("--price-file", required=True)
    parser.add_argument("--risk-file", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    build(
        feature_file=args.feature_file,
        price_file=args.price_file,
        risk_file=args.risk_file,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
