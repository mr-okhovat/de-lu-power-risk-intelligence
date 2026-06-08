from __future__ import annotations

from pathlib import Path
import json

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
        "intake_summary": Path("dashboards/dataset_intake_summary.csv"),
        "intake_report": Path("reports/dataset_intake_summary.md"),
        "project_checkpoint_report": Path("reports/project_checkpoint_run.md"),
        "project_checkpoint_json": Path("reports/project_checkpoint_run.json"),
        "artifact_manifest": Path("dashboards/project_artifact_manifest.csv"),
        "artifact_manifest_report": Path("reports/project_artifact_manifest.md"),
        "data_availability_index": Path("dashboards/data_availability_index.csv"),
        "data_availability_report": Path("reports/data_availability_index.md"),
        "run_catalog": Path("dashboards/market_month_run_catalog.csv"),
        "run_catalog_report": Path("reports/market_month_run_catalog.md"),
        "active_selection": Path("dashboards/active_run_selection.csv"),
        "active_selection_report": Path("reports/active_run_selection.md"),
        "reviewer": Path("reports/reviewer_ready_v1.md"),
        "reviewer_quick_path": Path("reports/reviewer_quick_path.md"),
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


def load_intake_summary() -> pd.DataFrame:
    return read_csv(Path("dashboards/dataset_intake_summary.csv"))


def load_artifact_manifest() -> pd.DataFrame:
    return read_csv(Path("dashboards/project_artifact_manifest.csv"))


def load_data_availability_index() -> pd.DataFrame:
    return read_csv(Path("dashboards/data_availability_index.csv"))


def load_run_catalog() -> pd.DataFrame:
    return read_csv(Path("dashboards/market_month_run_catalog.csv"))


def load_active_selection() -> pd.DataFrame:
    return read_csv(Path("dashboards/active_run_selection.csv"))


def load_checkpoint_payload() -> dict:
    path = Path("reports/project_checkpoint_run.json")

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


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


def as_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series

    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def data_availability_metrics(df: pd.DataFrame) -> dict[str, int | bool | str]:
    if df.empty:
        return {
            "datasets": 0,
            "registered": 0,
            "analytics_ready": 0,
            "unregistered": 0,
            "markets": 0,
            "period": "",
        }

    registered = as_bool_series(df["registered"]) if "registered" in df.columns else pd.Series(False, index=df.index)
    ready = as_bool_series(df["analytics_ready"]) if "analytics_ready" in df.columns else pd.Series(False, index=df.index)

    starts = df["start"].replace("", pd.NA).dropna() if "start" in df.columns else pd.Series(dtype="object")
    ends = df["end"].replace("", pd.NA).dropna() if "end" in df.columns else pd.Series(dtype="object")

    period = ""
    if not starts.empty and not ends.empty:
        period = f"{starts.min()} to {ends.max()}"

    return {
        "datasets": int(len(df)),
        "registered": int(registered.sum()),
        "analytics_ready": int(ready.sum()),
        "unregistered": int((~registered).sum()),
        "markets": int(df["market"].replace("", pd.NA).dropna().nunique()) if "market" in df.columns else 0,
        "period": period,
    }


def data_availability_status_counts(df: pd.DataFrame) -> pd.DataFrame:
    if "analytics_ready" not in df.columns:
        return pd.DataFrame({"status": [], "count": []})

    ready = as_bool_series(df["analytics_ready"])
    work = pd.DataFrame(
        {
            "status": ready.map({True: "analytics_ready", False: "not_ready"}),
        }
    )

    return (
        work["status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
        .sort_values("status")
        .reset_index(drop=True)
    )


def data_availability_core_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "dataset_id",
        "market",
        "start",
        "end",
        "registered",
        "analytics_ready",
        "intake_status",
        "source_rows",
        "adapted_rows",
        "source_file",
        "adapted_file",
    ]

    available = [col for col in cols if col in df.columns]
    return df[available].reset_index(drop=True)


def run_catalog_metrics(df: pd.DataFrame) -> dict[str, int | float]:
    if df.empty:
        return {
            "runs": 0,
            "ready_runs": 0,
            "check_needed_runs": 0,
            "markets": 0,
            "mean_same_hour_lift": 0.0,
            "mean_next_3h_lift": 0.0,
        }

    ready = df["run_status"].astype(str).eq("READY") if "run_status" in df.columns else pd.Series(False, index=df.index)

    same = 0.0
    if "same_hour_event_lift" in df.columns:
        same = float(pd.to_numeric(df["same_hour_event_lift"], errors="coerce").mean())

    next_3h = 0.0
    if "window_next_3h_event_lift" in df.columns:
        next_3h = float(pd.to_numeric(df["window_next_3h_event_lift"], errors="coerce").mean())

    return {
        "runs": int(len(df)),
        "ready_runs": int(ready.sum()),
        "check_needed_runs": int((~ready).sum()),
        "markets": int(df["market"].nunique()) if "market" in df.columns else 0,
        "mean_same_hour_lift": same,
        "mean_next_3h_lift": next_3h,
    }


def run_catalog_core_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "run_id",
        "market",
        "start",
        "end",
        "run_status",
        "source_rows",
        "same_hour_event_lift",
        "exact_next_1h_event_lift",
        "window_next_3h_event_lift",
        "window_next_6h_event_lift",
        "evaluation_file",
        "behavior_report",
    ]

    available = [col for col in cols if col in df.columns]
    return df[available].reset_index(drop=True)


def run_catalog_lift_frame(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "run_id",
        "same_hour_event_lift",
        "exact_next_1h_event_lift",
        "window_next_3h_event_lift",
        "window_next_6h_event_lift",
    ]

    available = [col for col in cols if col in df.columns]
    out = df[available].copy()

    if "run_id" in out.columns:
        out = out.set_index("run_id")

    return out


def checkpoint_stage_table(payload: dict) -> pd.DataFrame:
    rows = []

    for item in payload.get("results", []):
        rows.append(
            {
                "stage": item.get("name"),
                "status": item.get("status"),
                "return_code": item.get("return_code"),
                "missing_outputs": ", ".join(item.get("missing_outputs", [])),
            }
        )

    return pd.DataFrame(rows)


def checkpoint_metrics(payload: dict) -> dict[str, int | str | bool]:
    rows = payload.get("results", [])
    failed = [item for item in rows if item.get("status") != "PASS"]

    return {
        "status": payload.get("status", "UNKNOWN"),
        "stages": len(rows),
        "failed_stages": len(failed),
        "include_screenshots": bool(payload.get("include_screenshots", False)),
    }


def artifact_manifest_metrics(df: pd.DataFrame) -> dict[str, int | bool]:
    required = df[df["required"] == True] if "required" in df.columns else pd.DataFrame()
    missing = required[required["exists"] == False] if "exists" in df.columns else required

    return {
        "artifacts": int(len(df)),
        "required": int(len(required)),
        "missing_required": int(len(missing)),
        "all_required_present": int(len(missing)) == 0,
    }


def artifact_manifest_core_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["category", "path", "required", "exists", "size_bytes", "sha256"]
    available = [col for col in cols if col in df.columns]

    out = df[available].copy()

    if "sha256" in out.columns:
        out["sha256"] = out["sha256"].astype(str).str.slice(0, 12)

    return out.reset_index(drop=True)


def intake_status_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df["status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
        .sort_values("status")
        .reset_index(drop=True)
    )


def intake_core_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "dataset_id",
        "status",
        "row_count",
        "adapted_output",
        "contract_report",
    ]

    available = [col for col in cols if col in df.columns]
    return df[available].reset_index(drop=True)


def intake_metrics(df: pd.DataFrame) -> dict[str, int | bool]:
    total = int(len(df))
    passed = int((df["status"] == "PASS").sum()) if "status" in df.columns else 0
    failed = total - passed
    rows = int(df.loc[df["status"] == "PASS", "row_count"].sum()) if {"status", "row_count"}.issubset(df.columns) else 0

    return {
        "datasets": total,
        "passed": passed,
        "failed": failed,
        "canonical_rows": rows,
        "all_passed": failed == 0 and total > 0,
    }


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


def render_intake(intake_df: pd.DataFrame) -> None:
    st.subheader("Dataset intake")

    st.write(
        "This panel shows which registered datasets passed adapter mapping and contract validation before entering analytics."
    )

    metric = intake_metrics(intake_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registered datasets", fmt(metric["datasets"]))
    c2.metric("Passed", fmt(metric["passed"]))
    c3.metric("Failed", fmt(metric["failed"]))
    c4.metric("Canonical rows", fmt(metric["canonical_rows"]))

    if metric["all_passed"]:
        st.success("All registered datasets passed adapter and contract validation.")
    else:
        st.warning("One or more registered datasets need attention before analytics use.")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Intake status")
        st.bar_chart(intake_status_counts(intake_df), x="status", y="count")

    with right:
        st.markdown("#### Intake rule")
        st.write("External or regenerated datasets should enter through adapter mapping first, then contract validation.")

    st.markdown("#### Registered datasets")
    st.dataframe(intake_core_table(intake_df), use_container_width=True)

    st.download_button(
        "Download intake summary",
        data=csv_bytes(intake_df),
        file_name="dataset_intake_summary.csv",
        mime="text/csv",
    )


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


def render_data_availability(index_df: pd.DataFrame) -> None:
    st.subheader("Data availability")

    st.write(
        "This panel shows which datasets are present, registered, adapted, contract-checked and analytics-ready."
    )

    metric = data_availability_metrics(index_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Datasets", fmt(metric["datasets"]))
    c2.metric("Registered", fmt(metric["registered"]))
    c3.metric("Analytics-ready", fmt(metric["analytics_ready"]))
    c4.metric("Markets", fmt(metric["markets"]))

    if metric["unregistered"] == 0 and metric["datasets"] == metric["analytics_ready"]:
        st.success("All indexed datasets are registered and analytics-ready.")
    elif metric["unregistered"] > 0:
        st.warning("Some discovered datasets are not registered.")
    else:
        st.warning("Some registered datasets are not analytics-ready yet.")

    if metric["period"]:
        st.caption(f"Indexed period: {metric['period']}")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Availability status")
        st.bar_chart(data_availability_status_counts(index_df), x="status", y="count")

    with right:
        st.markdown("#### Control rule")
        st.write("A dataset should be used by analytics only after it is registered, adapted and contract-validated.")

    st.markdown("#### Data availability index")
    st.dataframe(data_availability_core_table(index_df), use_container_width=True)

    st.download_button(
        "Download data availability index",
        data=csv_bytes(index_df),
        file_name="data_availability_index.csv",
        mime="text/csv",
    )



def active_selection_metrics(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "selected_runs": 0,
            "markets": 0,
            "period": "n/a",
            "mean_same_hour_lift": None,
            "mean_next_3h_lift": None,
        }

    same_hour = pd.to_numeric(df.get("same_hour_event_lift"), errors="coerce").mean()
    next_3h = pd.to_numeric(df.get("window_next_3h_event_lift"), errors="coerce").mean()

    return {
        "selected_runs": int(len(df)),
        "markets": int(df["market"].nunique()) if "market" in df.columns else 0,
        "period": f"{df['start'].min()} to {df['end'].max()}" if {"start", "end"}.issubset(df.columns) else "n/a",
        "mean_same_hour_lift": same_hour,
        "mean_next_3h_lift": next_3h,
    }


def active_selection_core_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "run_id",
        "market",
        "start",
        "end",
        "run_status",
        "source_rows",
        "same_hour_event_lift",
        "window_next_3h_event_lift",
    ]
    available = [col for col in cols if col in df.columns]
    return df[available].copy()


def render_active_selection(selection_df: pd.DataFrame) -> None:
    st.subheader("Active run selection")

    if selection_df.empty:
        st.warning("No active run selection file is available.")
        return

    metric = active_selection_metrics(selection_df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Selected runs", metric["selected_runs"])
    col2.metric("Markets", metric["markets"])
    col3.metric("Same-hour lift", f"{metric['mean_same_hour_lift']:.3f}")
    col4.metric("Next-3h lift", f"{metric['mean_next_3h_lift']:.3f}")

    st.caption(f"Active period: {metric['period']}")
    st.dataframe(active_selection_core_table(selection_df), use_container_width=True)

    st.download_button(
        "Download active selection CSV",
        data=selection_df.to_csv(index=False),
        file_name="active_run_selection.csv",
        mime="text/csv",
    )

def render_run_catalog(catalog_df: pd.DataFrame) -> None:
    st.subheader("Run catalog")

    st.write(
        "This panel indexes completed market/month analysis runs and links readiness, same-hour metrics, lead-time metrics and output files."
    )

    metric = run_catalog_metrics(catalog_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Runs", fmt(metric["runs"]))
    c2.metric("Ready runs", fmt(metric["ready_runs"]))
    c3.metric("Check needed", fmt(metric["check_needed_runs"]))
    c4.metric("Markets", fmt(metric["markets"]))

    c5, c6 = st.columns(2)
    c5.metric("Mean same-hour lift", fmt(metric["mean_same_hour_lift"]))
    c6.metric("Mean next-3h lift", fmt(metric["mean_next_3h_lift"]))

    if metric["check_needed_runs"] == 0 and metric["runs"] > 0:
        st.success("All cataloged market/month runs are ready.")
    else:
        st.warning("Some runs need attention before downstream use.")

    st.markdown("#### Lift profile by run")
    st.line_chart(run_catalog_lift_frame(catalog_df))

    st.markdown("#### Run catalog")
    st.dataframe(run_catalog_core_table(catalog_df), use_container_width=True)

    st.download_button(
        "Download run catalog",
        data=csv_bytes(catalog_df),
        file_name="market_month_run_catalog.csv",
        mime="text/csv",
    )


def render_project_health(manifest_df: pd.DataFrame, checkpoint_payload: dict) -> None:
    st.subheader("Project health")

    st.write(
        "This panel shows whether the current checkpoint outputs exist and whether the rebuild stages passed."
    )

    checkpoint = checkpoint_metrics(checkpoint_payload)
    manifest = artifact_manifest_metrics(manifest_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Checkpoint status", str(checkpoint["status"]))
    c2.metric("Stages", fmt(checkpoint["stages"]))
    c3.metric("Failed stages", fmt(checkpoint["failed_stages"]))
    c4.metric("Missing required artifacts", fmt(manifest["missing_required"]))

    if checkpoint["status"] == "PASS" and manifest["all_required_present"]:
        st.success("Checkpoint and artifact manifest are healthy.")
    else:
        st.warning("One or more checkpoint or artifact checks need attention.")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Checkpoint stages")
        st.dataframe(checkpoint_stage_table(checkpoint_payload), use_container_width=True)

    with right:
        st.markdown("#### Artifact manifest")
        st.dataframe(artifact_manifest_core_table(manifest_df), use_container_width=True)

    st.download_button(
        "Download artifact manifest",
        data=csv_bytes(manifest_df),
        file_name="project_artifact_manifest.csv",
        mime="text/csv",
    )


def render_reports(selected_paths: dict[str, Path]) -> None:
    st.subheader("Reviewer files")

    rows = [
        {"file": "README", "path": selected_paths["readme"]},
        {"file": "Reviewer quick path", "path": selected_paths["reviewer_quick_path"]},
        {"file": "Reviewer-ready v1", "path": selected_paths["reviewer"]},
        {"file": "Visual reviewer pack", "path": selected_paths["visual_pack"]},
        {"file": "Monthly behavior report", "path": selected_paths["behavior"]},
        {"file": "Lead-time report", "path": selected_paths["lead_time_report"]},
        {"file": "Lead-time aggregate table", "path": selected_paths["lead_time_aggregate"]},
        {"file": "Dataset intake report", "path": selected_paths["intake_report"]},
        {"file": "Dataset intake summary", "path": selected_paths["intake_summary"]},
        {"file": "Project checkpoint report", "path": selected_paths["project_checkpoint_report"]},
        {"file": "Artifact manifest report", "path": selected_paths["artifact_manifest_report"]},
        {"file": "Data availability report", "path": selected_paths["data_availability_report"]},
        {"file": "Data availability index", "path": selected_paths["data_availability_index"]},
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

    tabs = st.tabs(["Overview", "Selected month", "Diagnostics", "Lead time", "Dataset intake", "Data availability", "Run catalog", "Active selection", "Project health", "Reviewer files"])

    with tabs[0]:
        render_overview(cross)

    with tabs[1]:
        render_month(df, metrics, month_label)

    with tabs[2]:
        render_diagnostics(df)

    with tabs[3]:
        render_lead_time(load_lead_time_aggregate(), load_lead_time_monthly())

    with tabs[4]:
        render_intake(load_intake_summary())

    with tabs[5]:
        render_data_availability(load_data_availability_index())

    with tabs[6]:
        render_run_catalog(load_run_catalog())

    with tabs[7]:
        render_active_selection(load_active_selection())

    with tabs[8]:
        render_project_health(load_artifact_manifest(), load_checkpoint_payload())

    with tabs[9]:
        render_reports(selected_paths)


if __name__ == "__main__":
    render()
