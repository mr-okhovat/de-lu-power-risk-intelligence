from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


MONTHS = {
    "May 2024": ("2024-05-01", "2024-05-31"),
    "June 2024": ("2024-06-01", "2024-06-30"),
    "July 2024": ("2024-07-01", "2024-07-31"),
    "August 2024": ("2024-08-01", "2024-08-31"),
}

MARKET = "DE-LU"


def month_tag(start: str, end: str) -> str:
    return f"{MARKET}_{start}_to_{end}"


def report_tag(start: str, end: str) -> str:
    return f"{start}_to_{end}"


def paths(start: str, end: str) -> dict[str, Path]:
    tag = month_tag(start, end)
    rtag = report_tag(start, end)

    return {
        "evaluation": Path(f"data/processed/signal_price_evaluation_{tag}.csv"),
        "price_events": Path(f"data/processed/price_events_{tag}.csv"),
        "behavior": Path(f"reports/price_risk_behavior_{rtag}.md"),
        "cross_month": Path("dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv"),
        "reviewer": Path("reports/reviewer_ready_v1.md"),
    }


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path)

    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)

    for col in ["signal_positive", "event_positive", "is_price_event"]:
        if col in df.columns and df[col].dtype != bool:
            df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])

    return df


def load_month(start: str, end: str) -> pd.DataFrame:
    return read_csv(paths(start, end)["evaluation"])


def load_cross_month() -> pd.DataFrame:
    return read_csv(Path("dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv"))


def kpis(df: pd.DataFrame) -> dict[str, float | int | None]:
    rows = int(len(df))
    signals = int(df["signal_positive"].sum())
    events = int(df["event_positive"].sum())

    tp = int((df["confusion_bucket"] == "TP").sum())
    fp = int((df["confusion_bucket"] == "FP").sum())
    fn = int((df["confusion_bucket"] == "FN").sum())

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    base_event_rate = events / rows if rows else None
    signal_event_rate = precision

    event_lift = None
    if base_event_rate and signal_event_rate is not None:
        event_lift = signal_event_rate / base_event_rate

    return {
        "rows": rows,
        "signals": signals,
        "events": events,
        "precision": precision,
        "recall": recall,
        "event_lift": event_lift,
    }


def format_rate(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def prepare_timeline(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["timestamp_utc", "price_eur_per_mwh", "risk_score"]
    out = df[cols].copy()
    out = out.set_index("timestamp_utc")
    return out


def top_cases(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    cols = [
        "timestamp_utc",
        "price_eur_per_mwh",
        "risk_score",
        "regime_label",
        "reason_codes",
        "price_event_labels",
        "confusion_bucket",
    ]

    return (
        df[cols]
        .sort_values(["risk_score", "price_eur_per_mwh"], ascending=[False, False])
        .head(n)
        .reset_index(drop=True)
    )


def render() -> None:
    st.set_page_config(
        page_title="DE-LU Power Risk Intelligence",
        layout="wide",
    )

    st.title("DE-LU Power Risk Intelligence")
    st.caption("Public-data analytics prototype. Not a trading system, not a forecast model, not a P&L backtest.")

    month_label = st.sidebar.selectbox("Month", list(MONTHS.keys()), index=1)
    start, end = MONTHS[month_label]

    df = load_month(start, end)
    metrics = kpis(df)

    st.subheader(f"{month_label} snapshot")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rows", f"{metrics['rows']:,}")
    c2.metric("Signals", f"{metrics['signals']:,}")
    c3.metric("Price events", f"{metrics['events']:,}")
    c4.metric("Precision", format_rate(metrics["precision"]))
    c5.metric("Event lift", format_rate(metrics["event_lift"]))

    st.markdown("### Price and risk timeline")
    st.line_chart(prepare_timeline(df))

    st.markdown("### Signal/event buckets")
    bucket_counts = (
        df["confusion_bucket"]
        .value_counts()
        .rename_axis("bucket")
        .reset_index(name="count")
        .sort_values("bucket")
    )
    st.bar_chart(bucket_counts, x="bucket", y="count")

    st.markdown("### Cross-month price-risk comparison")
    cross = load_cross_month()
    st.dataframe(cross, use_container_width=True)

    st.markdown("### Top risk cases")
    st.dataframe(top_cases(df), use_container_width=True)

    with st.expander("Current interpretation"):
        st.write(
            "The signal is conservative. It fires rarely, but signal-positive hours show higher ex-post price-event concentration than the monthly base rate across May to August 2024. Recall remains low, so this is a diagnostic layer rather than a forecasting model."
        )

    with st.expander("Reviewer entry files"):
        st.write("- reports/reviewer_ready_v1.md")
        st.write("- reports/visual_reviewer_pack.md")
        st.write("- reports/cross_month_price_risk_2024-05_to_2024-08.md")
        st.write("- src/signals/risk_engine.py")


if __name__ == "__main__":
    render()
