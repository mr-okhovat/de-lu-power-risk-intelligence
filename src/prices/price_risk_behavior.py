from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


VERSION = "8F.1"

REQUIRED = [
    "timestamp_utc",
    "price_eur_per_mwh",
    "price_ramp_eur_per_mwh",
    "risk_score",
    "regime_label",
    "reason_codes",
    "is_price_event",
    "price_event_labels",
    "signal_positive",
    "event_positive",
    "confusion_bucket",
]


def read_eval(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing evaluation file: {p}")

    df = pd.read_csv(p)
    missing = [col for col in REQUIRED if col not in df.columns]
    if missing:
        raise ValueError(f"{p} is missing columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    for col in ["is_price_event", "signal_positive", "event_positive"]:
        if df[col].dtype != bool:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def split_codes(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [part for part in str(value).split("|") if part and part != "NO_RULE_TRIGGERED"]


def bucket_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for bucket, group in df.groupby("confusion_bucket"):
        rows.append(
            {
                "bucket": bucket,
                "rows": int(len(group)),
                "mean_price": float(group["price_eur_per_mwh"].mean()),
                "median_price": float(group["price_eur_per_mwh"].median()),
                "max_price": float(group["price_eur_per_mwh"].max()),
                "min_price": float(group["price_eur_per_mwh"].min()),
                "mean_abs_price_ramp": float(group["price_ramp_eur_per_mwh"].abs().mean()),
                "mean_risk_score": float(group["risk_score"].mean()),
                "max_risk_score": float(group["risk_score"].max()),
                "version": VERSION,
            }
        )

    return pd.DataFrame(rows).sort_values("bucket").reset_index(drop=True)


def regime_price_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for regime, group in df.groupby("regime_label"):
        rows.append(
            {
                "regime_label": regime,
                "rows": int(len(group)),
                "price_event_rows": int(group["is_price_event"].sum()),
                "price_event_share": float(group["is_price_event"].mean()),
                "mean_price": float(group["price_eur_per_mwh"].mean()),
                "median_price": float(group["price_eur_per_mwh"].median()),
                "max_price": float(group["price_eur_per_mwh"].max()),
                "mean_abs_price_ramp": float(group["price_ramp_eur_per_mwh"].abs().mean()),
                "version": VERSION,
            }
        )

    return pd.DataFrame(rows).sort_values("regime_label").reset_index(drop=True)


def reason_price_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    all_codes = sorted({code for value in df["reason_codes"] for code in split_codes(value)})

    for code in all_codes:
        mask = df["reason_codes"].fillna("").str.contains(code, regex=False)
        group = df[mask]

        rows.append(
            {
                "reason_code": code,
                "rows": int(len(group)),
                "signal_positive_rows": int(group["signal_positive"].sum()),
                "price_event_rows": int(group["is_price_event"].sum()),
                "price_event_share": float(group["is_price_event"].mean()) if len(group) else 0.0,
                "mean_price": float(group["price_eur_per_mwh"].mean()) if len(group) else None,
                "median_price": float(group["price_eur_per_mwh"].median()) if len(group) else None,
                "mean_risk_score": float(group["risk_score"].mean()) if len(group) else None,
                "version": VERSION,
            }
        )

    return pd.DataFrame(rows).sort_values(["price_event_share", "rows"], ascending=[False, False]).reset_index(drop=True)


def event_lift(df: pd.DataFrame) -> dict[str, float | int | None]:
    base_event_rate = float(df["is_price_event"].mean())
    signal = df[df["signal_positive"]]

    signal_event_rate = float(signal["is_price_event"].mean()) if len(signal) else None
    lift = None

    if signal_event_rate is not None and base_event_rate > 0:
        lift = float(signal_event_rate / base_event_rate)

    return {
        "rows": int(len(df)),
        "signal_rows": int(df["signal_positive"].sum()),
        "price_event_rows": int(df["is_price_event"].sum()),
        "base_event_rate": base_event_rate,
        "signal_event_rate": signal_event_rate,
        "event_lift_when_signal_positive": lift,
    }


def price_quantile_table(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["risk_score_bin"] = pd.cut(
        work["risk_score"],
        bins=[-1, 0, 30, 60, 90, 100],
        labels=["0", "1-30", "31-60", "61-90", "91-100"],
    )

    rows = []

    for bucket, group in work.groupby("risk_score_bin", observed=False):
        if len(group) == 0:
            continue

        rows.append(
            {
                "risk_score_bin": str(bucket),
                "rows": int(len(group)),
                "price_q10": float(group["price_eur_per_mwh"].quantile(0.10)),
                "price_q50": float(group["price_eur_per_mwh"].quantile(0.50)),
                "price_q90": float(group["price_eur_per_mwh"].quantile(0.90)),
                "price_event_share": float(group["is_price_event"].mean()),
                "version": VERSION,
            }
        )

    return pd.DataFrame(rows)


def top_cases(df: pd.DataFrame, n: int) -> pd.DataFrame:
    cols = [
        "timestamp_utc",
        "price_eur_per_mwh",
        "price_ramp_eur_per_mwh",
        "risk_score",
        "regime_label",
        "reason_codes",
        "price_event_labels",
        "confusion_bucket",
    ]

    return df.sort_values(
        ["risk_score", "price_eur_per_mwh"],
        ascending=[False, False],
    )[cols].head(n).copy()


def make_report(
    *,
    lift: dict[str, float | int | None],
    bucket_csv: str,
    regime_csv: str,
    reason_csv: str,
    quantile_csv: str,
    top_csv: str,
) -> str:
    lines = [
        "# Price-risk behavior",
        "",
        f"Version: {VERSION}",
        "",
        "## Headline",
        "",
        f"- Rows: {lift['rows']}",
        f"- Signal-positive rows: {lift['signal_rows']}",
        f"- Price-event rows: {lift['price_event_rows']}",
        f"- Base price-event rate: {lift['base_event_rate']}",
        f"- Price-event rate when signal-positive: {lift['signal_event_rate']}",
        f"- Event lift when signal-positive: {lift['event_lift_when_signal_positive']}",
        "",
        "## Output tables",
        "",
        f"- Bucket profile: `{bucket_csv}`",
        f"- Regime price profile: `{regime_csv}`",
        f"- Reason-code price profile: `{reason_csv}`",
        f"- Price quantiles by risk-score bin: `{quantile_csv}`",
        f"- Top cases: `{top_csv}`",
        "",
        "## Readout",
        "",
    ]

    lift_value = lift["event_lift_when_signal_positive"]

    if lift_value is None:
        lines.append("No signal-positive rows were available for lift calculation.")
    elif lift_value >= 2:
        lines.append("Signal-positive hours have a materially higher price-event rate than the base rate.")
    elif lift_value > 1:
        lines.append("Signal-positive hours have a higher price-event rate than the base rate, but the sample is still small.")
    else:
        lines.append("Signal-positive hours do not show better-than-base event concentration in this window.")

    lines += [
        "",
        "This is a diagnostic report. It does not prove forecast skill, tradability or P&L.",
        "",
    ]

    return "\n".join(lines)


def build(
    *,
    input_file: str,
    output_report: str,
    output_json: str,
    bucket_csv: str,
    regime_csv: str,
    reason_csv: str,
    quantile_csv: str,
    top_csv: str,
    top_n: int,
) -> None:
    df = read_eval(input_file)

    bucket = bucket_profile(df)
    regime = regime_price_profile(df)
    reason = reason_price_profile(df)
    quantiles = price_quantile_table(df)
    top = top_cases(df, top_n)
    lift = event_lift(df)

    outputs = [
        (bucket_csv, bucket),
        (regime_csv, regime),
        (reason_csv, reason),
        (quantile_csv, quantiles),
        (top_csv, top),
    ]

    for path, table in outputs:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(path, index=False)

    Path(output_report).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)

    Path(output_report).write_text(
        make_report(
            lift=lift,
            bucket_csv=bucket_csv,
            regime_csv=regime_csv,
            reason_csv=reason_csv,
            quantile_csv=quantile_csv,
            top_csv=top_csv,
        ),
        encoding="utf-8",
    )

    Path(output_json).write_text(
        json.dumps(
            {
                "version": VERSION,
                "input_file": input_file,
                "lift": lift,
                "outputs": {
                    "bucket": bucket_csv,
                    "regime": regime_csv,
                    "reason": reason_csv,
                    "quantiles": quantile_csv,
                    "top": top_csv,
                    "report": output_report,
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | price-risk behavior report={output_report}")
    print(f"OK | event lift={lift['event_lift_when_signal_positive']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--bucket-csv", required=True)
    parser.add_argument("--regime-csv", required=True)
    parser.add_argument("--reason-csv", required=True)
    parser.add_argument("--quantile-csv", required=True)
    parser.add_argument("--top-csv", required=True)
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()

    build(
        input_file=args.input_file,
        output_report=args.output_report,
        output_json=args.output_json,
        bucket_csv=args.bucket_csv,
        regime_csv=args.regime_csv,
        reason_csv=args.reason_csv,
        quantile_csv=args.quantile_csv,
        top_csv=args.top_csv,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
