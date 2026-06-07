from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


VERSION = "7B.1"


def read_signals(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], utc=True).dt.tz_convert("Europe/Berlin")
    return df.sort_values("timestamp_utc").reset_index(drop=True)


def split_reasons(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [part for part in str(value).split("|") if part]


def reason_counts(df: pd.DataFrame) -> pd.DataFrame:
    counter: Counter[str] = Counter()

    for value in df["reason_codes"]:
        counter.update(split_reasons(value))

    rows = [
        {"reason_code": key, "count": int(count), "share": count / len(df), "version": VERSION}
        for key, count in counter.most_common()
    ]

    return pd.DataFrame(rows)


def hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["local_hour"] = work["timestamp_local"].dt.hour
    work["is_high_risk"] = work["risk_score"] >= 60

    grouped = (
        work.groupby("local_hour", as_index=False)
        .agg(
            rows=("risk_score", "size"),
            mean_risk_score=("risk_score", "mean"),
            max_risk_score=("risk_score", "max"),
            high_risk_rows=("is_high_risk", "sum"),
        )
    )

    grouped["high_risk_share"] = grouped["high_risk_rows"] / grouped["rows"]
    grouped["version"] = VERSION

    return grouped


def weekday_profile(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["local_weekday"] = work["timestamp_local"].dt.day_name()
    work["is_high_risk"] = work["risk_score"] >= 60

    grouped = (
        work.groupby("local_weekday", as_index=False)
        .agg(
            rows=("risk_score", "size"),
            mean_risk_score=("risk_score", "mean"),
            max_risk_score=("risk_score", "max"),
            high_risk_rows=("is_high_risk", "sum"),
        )
    )

    grouped["high_risk_share"] = grouped["high_risk_rows"] / grouped["rows"]
    grouped["version"] = VERSION

    return grouped


def top_hours(df: pd.DataFrame, n: int) -> pd.DataFrame:
    out = df.sort_values(["risk_score", "timestamp_utc"], ascending=[False, True]).head(n).copy()
    out["version"] = VERSION
    return out


def regime_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["regime_label"].value_counts().rename_axis("regime_label").reset_index(name="count")
    counts["share"] = counts["count"] / len(df)
    counts["version"] = VERSION
    return counts.sort_values("regime_label").reset_index(drop=True)


def make_report(
    *,
    df: pd.DataFrame,
    signal_file: str,
    regime_file: str,
    reasons_file: str,
    hourly_file: str,
    weekday_file: str,
    top_file: str,
) -> str:
    high = df[df["risk_score"] >= 60]
    extreme = df[df["regime_label"] == "EXTREME"]

    lines = [
        "# June 2024 risk behavior review",
        "",
        f"Version: {VERSION}",
        f"Signal input: `{signal_file}`",
        "",
        "## Headline",
        "",
        f"- Rows: {len(df)}",
        f"- Mean risk score: {df['risk_score'].mean():.2f}",
        f"- Median risk score: {df['risk_score'].median():.2f}",
        f"- Max risk score: {df['risk_score'].max():.2f}",
        f"- High-risk rows, score >= 60: {len(high)}",
        f"- Extreme rows: {len(extreme)}",
        "",
        "## Output files",
        "",
        f"- Regime distribution: `{regime_file}`",
        f"- Reason-code summary: `{reasons_file}`",
        f"- Hourly profile: `{hourly_file}`",
        f"- Weekday profile: `{weekday_file}`",
        f"- Top risk hours: `{top_file}`",
        "",
        "## First read",
        "",
    ]

    high_share = len(high) / len(df) if len(df) else 0

    if high_share == 0:
        lines.append("No high-risk rows appeared in this window. The signal is probably too quiet or the sample is calm.")
    elif high_share > 0.25:
        lines.append("More than 25% of rows are high risk. The signal may be too sensitive for a first rule-based layer.")
    else:
        lines.append("High-risk frequency is not obviously excessive for a first diagnostic run.")

    if df["risk_score"].max() == 0:
        lines.append("All scores are zero. The rules are not firing.")
    elif df["risk_score"].median() == 0:
        lines.append("The median score is zero. Stress detection is concentrated in selected hours, not spread everywhere.")

    lines += [
        "",
        "## Boundary",
        "",
        "This is a behavior review, not a performance test. It does not prove predictive value or trading usefulness.",
        "",
    ]

    return "\n".join(lines)


def build_review(
    *,
    signal_file: str,
    report: str,
    json_out: str,
    regime_out: str,
    reasons_out: str,
    hourly_out: str,
    weekday_out: str,
    top_out: str,
    top_n: int,
) -> None:
    df = read_signals(signal_file)

    regime = regime_counts(df)
    reasons = reason_counts(df)
    hourly = hourly_profile(df)
    weekday = weekday_profile(df)
    top = top_hours(df, top_n)

    for path, table in [
        (regime_out, regime),
        (reasons_out, reasons),
        (hourly_out, hourly),
        (weekday_out, weekday),
        (top_out, top),
    ]:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(p, index=False)

    report_text = make_report(
        df=df,
        signal_file=signal_file,
        regime_file=regime_out,
        reasons_file=reasons_out,
        hourly_file=hourly_out,
        weekday_file=weekday_out,
        top_file=top_out,
    )

    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(report_text, encoding="utf-8")

    summary = {
        "version": VERSION,
        "rows": int(len(df)),
        "mean_risk_score": float(df["risk_score"].mean()),
        "median_risk_score": float(df["risk_score"].median()),
        "max_risk_score": float(df["risk_score"].max()),
        "high_risk_rows": int((df["risk_score"] >= 60).sum()),
        "extreme_rows": int((df["regime_label"] == "EXTREME").sum()),
        "outputs": {
            "report": report,
            "regime": regime_out,
            "reasons": reasons_out,
            "hourly": hourly_out,
            "weekday": weekday_out,
            "top": top_out,
        },
    }

    Path(json_out).write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(f"OK | behavior review written: {report}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal-file", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--regime-out", required=True)
    parser.add_argument("--reasons-out", required=True)
    parser.add_argument("--hourly-out", required=True)
    parser.add_argument("--weekday-out", required=True)
    parser.add_argument("--top-out", required=True)
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()

    build_review(
        signal_file=args.signal_file,
        report=args.report,
        json_out=args.json,
        regime_out=args.regime_out,
        reasons_out=args.reasons_out,
        hourly_out=args.hourly_out,
        weekday_out=args.weekday_out,
        top_out=args.top_out,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
