from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


VERSION = "7F.1"


def split_reasons(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [part for part in str(value).split("|") if part]


def signal_path(market: str, start: str, end: str) -> str:
    return f"data/processed/risk_signals_{market}_{start}_to_{end}.csv"


def read_signals(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing risk signal file: {p}")

    df = pd.read_csv(p)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def top_reason(df: pd.DataFrame) -> str:
    counter: Counter[str] = Counter()

    for value in df["reason_codes"]:
        counter.update(reason for reason in split_reasons(value) if reason != "NO_RULE_TRIGGERED")

    if not counter:
        return "none"

    return counter.most_common(1)[0][0]


def summarize_month(label: str, start: str, end: str, path: str, df: pd.DataFrame) -> dict[str, object]:
    high = df[df["risk_score"] >= 60]
    regimes = df["regime_label"].value_counts().to_dict()

    return {
        "label": label,
        "start": start,
        "end": end,
        "signal_file": path,
        "rows": int(len(df)),
        "mean_risk_score": round(float(df["risk_score"].mean()), 3),
        "median_risk_score": round(float(df["risk_score"].median()), 3),
        "max_risk_score": round(float(df["risk_score"].max()), 3),
        "high_risk_rows": int(len(high)),
        "high_risk_share": round(float(len(high) / len(df)), 4) if len(df) else 0.0,
        "extreme_rows": int((df["regime_label"] == "EXTREME").sum()),
        "normal_rows": int(regimes.get("NORMAL", 0)),
        "watch_rows": int(regimes.get("WATCH", 0)),
        "stressed_rows": int(regimes.get("STRESSED", 0)),
        "top_reason": top_reason(df),
        "version": VERSION,
    }


def build_summary(months: list[tuple[str, str, str]], market: str) -> pd.DataFrame:
    rows = []

    for label, start, end in months:
        path = signal_path(market, start, end)
        df = read_signals(path)
        rows.append(summarize_month(label, start, end, path, df))

    return pd.DataFrame(rows)


def readout(summary: pd.DataFrame) -> str:
    max_share = float(summary["high_risk_share"].max())
    min_share = float(summary["high_risk_share"].min())
    max_score = float(summary["max_risk_score"].max())

    if max_share == 0:
        return "The signal is not firing in any monthly window. That would be too quiet."
    if max_share > 0.25:
        return "At least one month has a very high signal rate. The rules may be too sensitive."
    if max_score < 60:
        return "No month reaches high-risk territory. The rules may miss medium-stress periods."
    if (max_share - min_share) > 0.10:
        return "Signal frequency varies noticeably across months. Inspect drivers before tuning."
    return "Signal frequency looks controlled across the current months. No threshold change is justified yet."


def make_report(summary: pd.DataFrame, output_csv: str) -> str:
    lines = [
        "# Cross-month risk behavior",
        "",
        f"Version: {VERSION}",
        f"Table: `{output_csv}`",
        "",
        "## Monthly summary",
        "",
        "| month | rows | mean | median | max | high-risk rows | high-risk share | extreme | top reason |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['label']} | {row['rows']} | {row['mean_risk_score']} | "
            f"{row['median_risk_score']} | {row['max_risk_score']} | "
            f"{row['high_risk_rows']} | {row['high_risk_share']} | "
            f"{row['extreme_rows']} | {row['top_reason']} |"
        )

    lines += [
        "",
        "## Readout",
        "",
        readout(summary),
        "",
        "## Decision",
        "",
        "Keep the current rules unchanged.",
        "",
        "The next useful step is not threshold tuning. The next useful step is adding a price layer, because without prices we still cannot say whether these stress hours mattered economically.",
        "",
    ]

    return "\n".join(lines)


def build_cross_month_review(
    *,
    market: str,
    output_csv: str,
    output_report: str,
    output_json: str,
) -> None:
    months = [
        ("May 2024", "2024-05-01", "2024-05-31"),
        ("June 2024", "2024-06-01", "2024-06-30"),
        ("July 2024", "2024-07-01", "2024-07-31"),
        ("August 2024", "2024-08-01", "2024-08-31"),
    ]

    summary = build_summary(months, market)

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
                "months": summary.to_dict("records"),
                "readout": readout(summary),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | cross-month review written: {output_report}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    build_cross_month_review(
        market=args.market_label,
        output_csv=args.output_csv,
        output_report=args.output_report,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
