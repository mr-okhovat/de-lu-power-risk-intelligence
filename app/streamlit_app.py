from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


APP_VERSION = "10C.1"
MARKET = "DE-LU"

MONTHS = {
    "May 2024": ("2024-05-01", "2024-05-31"),
    "June 2024": ("2024-06-01", "2024-06-30"),
    "July 2024": ("2024-07-01", "2024-07-31"),
    "August 2024": ("2024-08-01", "2024-08-31"),
}


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
        "lead_time_aggregate": Path("dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv"),
        "lead_time_monthly": Path("dashboards/lead_time_monthly_DE-LU_2024-05_to_2024-08.csv"),
        "lead_time_report": Path("reports/lead_time_evaluation_2024-05_to_2024-08.md"),
        "reviewer": Path("reports/reviewer_ready_v1.md"),
        "visual_pack": Path("reports/visual_reviewer_pack.md"),
        "readme": Path("README.md"),
    }


def file_status_table(selected_paths: dict[str, Path]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"file": key, "path": str(path), "exists": path.exists()}
            for key, path in selected_paths.items()
        ]
    )


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


def load_lead_time_aggregate() -> pd.DataFrame:
    return read_csv(Path("dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv"))


def load_lead_time_monthly() -> pd.DataFrame:
    return read_csv(Path("dashboards/lead_time_monthly_DE-LU_2024-05_to_2024-08.csv"))


def safe_rate(a: int, b: int) -> float | None:
    if b == 0:
        return None
    return a / b


def kpis(df: pd.DataFrame) -> dict[str, float | int | None]:
    rows = int(len(df))
    signals = int(df["signal_positive"].sum())
    events = int(df["event_positive"].sum())

    tp = int((df["confusion_bucket"] == "TP").sum())
    fp = int((df["confusion_bucket"] == "FP").sum())
    fn = int((df["confusion_bucket"] == "FN").sum())
    tn = int((df["confusion_bucket"] == "TN").sum())

    precision = safe_rate(tp, tp + fp)
    recall = safe_rate(tp, tp + fn)
    base_event_rate = safe_rate(events, rows)
    signal_event_rate = precision

    event_lift = None
    if base_event_rate and signal_event_rate is not None:
        event_lift = signal_event_rate / base_event_rate

    return {
        "rows": rows,
        "signals": signals,
        "events": events,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "base_event_rate": base_event_rate,
        "signal_event_rate": signal_event_rate,
        "event_lift": event_lift,
    }


def fmt(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return f"{value:,}"


def timeline_price(df: pd.DataFrame) -> pd.DataFrame:
    return df[["timestamp_utc", "price_eur_per_mwh"]].set_index("timestamp_utc")


def timeline_risk(df: pd.DataFrame) -> pd.DataFrame:
    return df[["timestamp_utc", "risk_score"]].set_index("timestamp_utc")


def timeline_combined(df: pd.DataFrame) -> pd.DataFrame:
    out = df[["timestamp_utc", "price_eur_per_mwh", "risk_score"]].copy()
    out = out.set_index("timestamp_utc")
    return out


def bucket_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df["confusion_bucket"]
        .value_counts()
        .rename_axis("bucket")
        .reset_index(name="count")
        .sort_values("bucket")
        .reset_index(drop=True)
    )


def split_codes(value: object) -> list[str]:
    if pd.isna(value):
        return []

    return [
        part
        for part in str(value).split("|")
        if part and part not in {"NO_RULE_TRIGGERED", "NO_PRICE_EVENT"}
    ]


def explode_label_summary(df: pd.DataFrame, source_col: str, label_col: str) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        for label in split_codes(row[source_col]):
            rows.append(
                {
                    label_col: label,
                    "signal_positive": bool(row.get("signal_positive", False)),
                    "event_positive": bool(row.get("event_positive", False)),
                    "price_eur_per_mwh": row.get("price_eur_per_mwh"),
                    "risk_score": row.get("risk_score"),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[label_col, "rows", "signal_rows", "event_rows", "mean_price", "mean_risk_score"]
        )

    work = pd.DataFrame(rows)

    return (
        work.groupby(label_col, as_index=False)
        .agg(
            rows=(label_col, "size"),
            signal_rows=("signal_positive", "sum"),
            event_rows=("event_positive", "sum"),
            mean_price=("price_eur_per_mwh", "mean"),
            mean_risk_score=("risk_score", "mean"),
        )
        .sort_values(["event_rows", "rows"], ascending=[False, False])
        .reset_index(drop=True)
    )


def reason_summary(df: pd.DataFrame) -> pd.DataFrame:
    return explode_label_summary(df, "reason_codes", "reason_code")


def price_event_summary(df: pd.DataFrame) -> pd.DataFrame:
    return explode_label_summary(df, "price_event_labels", "price_event_label")


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


def signal_cases(df: pd.DataFrame) -> pd.DataFrame:
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
        df[df["signal_positive"]][cols]
        .sort_values("timestamp_utc")
        .reset_index(drop=True)
    )


def monthly_lift_frame(cross: pd.DataFrame) -> pd.DataFrame:
    return cross[["month", "event_lift"]].set_index("month")


def monthly_rate_frame(cross: pd.DataFrame) -> pd.DataFrame:
    return cross[["month", "base_event_rate", "signal_event_rate"]].set_index("month")


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def lead_time_lift_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["target_definition", "event_lift"]
    return df[cols].set_index("target_definition")


def lead_time_precision_recall_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["target_definition", "precision", "recall"]
    return df[cols].set_index("target_definition")


def lead_time_core_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "mode",
        "horizon_hours",
        "target_definition",
        "signal_rows",
        "target_event_rows",
        "precision",
        "recall",
        "event_lift",
    ]

    return df[cols].sort_values(["mode", "horizon_hours"]).reset_index(drop=True)


def render_kpis(metrics: dict[str, float | int | None]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", fmt(metrics["rows"]))
    c2.metric("Signals", fmt(metrics["signals"]))
    c3.metric("Price events", fmt(metrics["events"]))
    c4.metric("Event lift", fmt(metrics["event_lift"]))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Precision", fmt(metrics["precision"]))
    c6.metric("Recall", fmt(metrics["recall"]))
    c7.metric("Base event rate", fmt(metrics["base_event_rate"]))
    c8.metric("Signal event rate", fmt(metrics["signal_event_rate"]))


def render_sidebar(selected_paths: dict[str, Path]) -> None:
    st.sidebar.markdown("### Project")
    st.sidebar.write(f"Market: {MARKET}")
    st.sidebar.write(f"App version: {APP_VERSION}")
    st.sidebar.write("Mode: local analyst dashboard")

    status = file_status_table(selected_paths)
    missing = int((~status["exists"]).sum())

    if missing:
        st.sidebar.warning(f"{missing} expected files missing")
    else:
        st.sidebar.success("Required files available")


def render_overview(cross: pd.DataFrame) -> None:
    st.subheader("Cross-month overview")

    cols = [
        "month",
        "rows",
        "signal_rows",
        "price_event_rows",
        "precision",
        "recall",
        "event_lift",
    ]

    st.dataframe(cross[cols], use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.markdown("#### Monthly event lift")
        st.line_chart(monthly_lift_frame(cross))

    with right:
        st.markdown("#### Event rates")
        st.line_chart(monthly_rate_frame(cross))

    st.caption(
        "Signal-positive hours beat the monthly base event rate in all reviewed months. The signal is still conservative and low-recall."
    )

    st.download_button(
        "Download cross-month table",
        data=csv_bytes(cross),
        file_name="cross_month_price_risk.csv",
        mime="text/csv",
    )


def render_month(df: pd.DataFrame, metrics: dict[str, float | int | None], month_label: str) -> None:
    st.subheader(f"{month_label} snapshot")
    render_kpis(metrics)

    st.markdown("#### Price and risk timeline")
    st.line_chart(timeline_combined(df))

    left, right = st.columns(2)

    with left:
        st.markdown("#### Day-ahead price")
        st.line_chart(timeline_price(df))

    with right:
        st.markdown("#### Risk score")
        st.line_chart(timeline_risk(df))

    st.markdown("#### Confusion buckets")
    buckets = bucket_counts(df)
    st.bar_chart(buckets, x="bucket", y="count")

    signals = signal_cases(df)
    st.markdown("#### Signal-positive hours")
    st.dataframe(signals, use_container_width=True)

    st.download_button(
        "Download selected month evaluation",
        data=csv_bytes(df),
        file_name=f"{month_label.lower().replace(' ', '_')}_evaluation.csv",
        mime="text/csv",
    )


def render_diagnostics(df: pd.DataFrame) -> None:
    st.subheader("Diagnostics")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Risk reason codes")
        st.dataframe(reason_summary(df), use_container_width=True)

    with right:
        st.markdown("#### Price-event labels")
        st.dataframe(price_event_summary(df), use_container_width=True)

    st.markdown("#### Top risk cases")
    st.dataframe(top_cases(df), use_container_width=True)


def render_lead_time(aggregate_df: pd.DataFrame, monthly_df: pd.DataFrame) -> None:
    st.subheader("Lead-time evaluation")

    st.write(
        "This panel checks whether the current signal has any relationship with future price events. It is still a diagnostic test, not a trading backtest."
    )

    st.markdown("#### Aggregate lead-time table")
    core = lead_time_core_table(aggregate_df)
    st.dataframe(core, use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.markdown("#### Event lift by target")
        st.bar_chart(lead_time_lift_frame(aggregate_df))

    with right:
        st.markdown("#### Precision and recall by target")
        st.line_chart(lead_time_precision_recall_frame(aggregate_df))

    st.markdown("#### Monthly lead-time detail")
    st.dataframe(monthly_df, use_container_width=True)

    st.download_button(
        "Download aggregate lead-time table",
        data=csv_bytes(aggregate_df),
        file_name="lead_time_aggregate.csv",
        mime="text/csv",
    )

    st.caption(
        "Use this panel to distinguish same-hour diagnostic alignment from forward-looking early-warning behavior."
    )


def render_reports(selected_paths: dict[str, Path]) -> None:
    st.subheader("Reviewer files")

    rows = [
        {"file": "README", "path": selected_paths["readme"]},
        {"file": "Reviewer-ready v1", "path": selected_paths["reviewer"]},
        {"file": "Visual reviewer pack", "path": selected_paths["visual_pack"]},
        {"file": "Monthly behavior report", "path": selected_paths["behavior"]},
        {"file": "Lead-time report", "path": selected_paths["lead_time_report"]},
        {"file": "Lead-time aggregate table", "path": selected_paths["lead_time_aggregate"]},
        {"file": "Cross-month table", "path": selected_paths["cross_month"]},
    ]

    out = pd.DataFrame(
        [
            {
                "file": item["file"],
                "path": str(item["path"]),
                "exists": item["path"].exists(),
            }
            for item in rows
        ]
    )

    st.dataframe(out, use_container_width=True)

    st.markdown("#### Current interpretation")
    st.write(
        "This dashboard reads already-built CSV/report outputs. It does not rebuild ingestion or change the model. The current signal is a conservative diagnostic layer. It is useful for review, not for trading claims."
    )


def render() -> None:
    st.set_page_config(
        page_title="DE-LU Power Risk Intelligence",
        layout="wide",
    )

    st.title("DE-LU Power Risk Intelligence")
    st.caption("Public-data analyst prototype. No forecast, P&L, execution, or trading claim.")

    month_label = st.sidebar.selectbox("Month", list(MONTHS.keys()), index=1)
    start, end = MONTHS[month_label]
    selected_paths = paths(start, end)

    render_sidebar(selected_paths)

    df = load_month(start, end)
    cross = load_cross_month()
    metrics = kpis(df)

    tabs = st.tabs(["Overview", "Selected month", "Diagnostics", "Lead time", "Reviewer files"])

    with tabs[0]:
        render_overview(cross)

    with tabs[1]:
        render_month(df, metrics, month_label)

    with tabs[2]:
        render_diagnostics(df)

    with tabs[3]:
        render_lead_time(load_lead_time_aggregate(), load_lead_time_monthly())

    with tabs[4]:
        render_reports(selected_paths)


if __name__ == "__main__":
    render()
