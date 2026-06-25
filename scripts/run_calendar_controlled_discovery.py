from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "timestamp_utc",
    "price_eur_per_mwh",
    "residual_load_official_mw",
    "renewable_share",
    "residual_load_ramp_mw",
}


def safe_rate(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator / denominator)


def metric_row(
    df: pd.DataFrame,
    *,
    exposure_column: str,
    period_label: str,
    control: str,
) -> dict[str, object]:
    exposed = df[df[exposure_column]]
    unexposed = df[~df[exposure_column]]

    exposed_rate = safe_rate(
        float(exposed["price_high_event"].sum()),
        float(len(exposed)),
    )
    unexposed_rate = safe_rate(
        float(unexposed["price_high_event"].sum()),
        float(len(unexposed)),
    )

    diff_pp = (
        None
        if exposed_rate is None or unexposed_rate is None
        else float((exposed_rate - unexposed_rate) * 100)
    )

    relative_lift = (
        None
        if (
            exposed_rate is None
            or unexposed_rate is None
            or unexposed_rate == 0
        )
        else float(exposed_rate / unexposed_rate)
    )

    return {
        "period": period_label,
        "exposure": exposure_column,
        "control": control,
        "rows": int(len(df)),
        "exposed_rows": int(len(exposed)),
        "unexposed_rows": int(len(unexposed)),
        "exposed_price_event_rows": int(exposed["price_high_event"].sum()),
        "unexposed_price_event_rows": int(
            unexposed["price_high_event"].sum()
        ),
        "exposed_event_rate": exposed_rate,
        "unexposed_event_rate": unexposed_rate,
        "event_rate_difference_pp": diff_pp,
        "relative_lift": relative_lift,
        "valid_strata": None,
        "weighted_common_support_rows": None,
    }


def controlled_metric_row(
    df: pd.DataFrame,
    *,
    exposure_column: str,
    period_label: str,
) -> dict[str, object]:
    weighted_exposed_rate = 0.0
    weighted_unexposed_rate = 0.0
    total_weight = 0.0
    valid_strata = 0
    common_support_rows = 0

    for _, group in df.groupby(["year_month", "delivery_hour"], sort=False):
        exposed = group[group[exposure_column]]
        unexposed = group[~group[exposure_column]]

        n_exposed = len(exposed)
        n_unexposed = len(unexposed)

        if n_exposed == 0 or n_unexposed == 0:
            continue

        exposed_rate = float(exposed["price_high_event"].mean())
        unexposed_rate = float(unexposed["price_high_event"].mean())

        # Harmonic-style weight: strata with both groups represented contribute,
        # while a one-observation minority group cannot dominate the aggregate.
        weight = float(
            (n_exposed * n_unexposed) / (n_exposed + n_unexposed)
        )

        weighted_exposed_rate += weight * exposed_rate
        weighted_unexposed_rate += weight * unexposed_rate
        total_weight += weight
        valid_strata += 1
        common_support_rows += n_exposed + n_unexposed

    if total_weight == 0:
        exposed_rate = None
        unexposed_rate = None
        diff_pp = None
        relative_lift = None
    else:
        exposed_rate = float(weighted_exposed_rate / total_weight)
        unexposed_rate = float(weighted_unexposed_rate / total_weight)
        diff_pp = float((exposed_rate - unexposed_rate) * 100)
        relative_lift = (
            None
            if unexposed_rate == 0
            else float(exposed_rate / unexposed_rate)
        )

    return {
        "period": period_label,
        "exposure": exposure_column,
        "control": "year_month_x_delivery_hour",
        "rows": int(len(df)),
        "exposed_rows": int(df[exposure_column].sum()),
        "unexposed_rows": int((~df[exposure_column]).sum()),
        "exposed_price_event_rows": int(
            df.loc[df[exposure_column], "price_high_event"].sum()
        ),
        "unexposed_price_event_rows": int(
            df.loc[~df[exposure_column], "price_high_event"].sum()
        ),
        "exposed_event_rate": exposed_rate,
        "unexposed_event_rate": unexposed_rate,
        "event_rate_difference_pp": diff_pp,
        "relative_lift": relative_lift,
        "valid_strata": valid_strata,
        "weighted_common_support_rows": common_support_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-panel", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--metrics-csv", required=True)
    parser.add_argument("--state-summary-csv", required=True)
    args = parser.parse_args()

    input_path = Path(args.input_panel)
    summary_path = Path(args.summary_json)
    report_path = Path(args.report)
    metrics_path = Path(args.metrics_csv)
    state_path = Path(args.state_summary_csv)

    df = pd.read_csv(input_path)

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(
            f"Input panel is missing required columns: {missing_columns}"
        )

    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    df["timestamp_local"] = df["timestamp_utc"].dt.tz_convert(
        "Europe/Berlin"
    )
    df["year"] = df["timestamp_local"].dt.year
    df["year_month"] = df["timestamp_local"].dt.strftime("%Y-%m")
    df["delivery_hour"] = df["timestamp_local"].dt.hour

    required_numeric = [
        "price_eur_per_mwh",
        "residual_load_official_mw",
        "renewable_share",
        "residual_load_ramp_mw",
    ]

    for column in required_numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df["abs_residual_load_ramp_mw"] = (
        df["residual_load_ramp_mw"].abs()
    )

    month_groups = df.groupby("year_month", observed=True)

    df["price_high_threshold"] = month_groups[
        "price_eur_per_mwh"
    ].transform(lambda values: values.quantile(0.90))

    df["residual_high_threshold"] = month_groups[
        "residual_load_official_mw"
    ].transform(lambda values: values.quantile(0.90))

    df["renewable_low_threshold"] = month_groups[
        "renewable_share"
    ].transform(lambda values: values.quantile(0.10))

    df["residual_ramp_high_threshold"] = month_groups[
        "abs_residual_load_ramp_mw"
    ].transform(lambda values: values.quantile(0.90))

    df["price_high_event"] = (
        df["price_eur_per_mwh"] >= df["price_high_threshold"]
    )

    df["high_residual_load"] = (
        df["residual_load_official_mw"] >= df["residual_high_threshold"]
    )

    df["low_renewable_share"] = (
        df["renewable_share"] <= df["renewable_low_threshold"]
    )

    df["high_abs_residual_ramp"] = (
        df["abs_residual_load_ramp_mw"]
        >= df["residual_ramp_high_threshold"]
    )

    state_columns = [
        "high_residual_load",
        "low_renewable_share",
        "high_abs_residual_ramp",
    ]

    valid_mask = (
        df[
            [
                "price_high_event",
                *state_columns,
            ]
        ]
        .notna()
        .all(axis=1)
    )

    analysis = df.loc[valid_mask].copy()

    analysis["fundamental_stress_count"] = analysis[
        state_columns
    ].astype(int).sum(axis=1)

    analysis["composite_fundamental_stress"] = (
        analysis["fundamental_stress_count"] >= 2
    )

    exposure_columns = [
        *state_columns,
        "composite_fundamental_stress",
    ]

    metrics: list[dict[str, object]] = []

    for exposure_column in exposure_columns:
        metrics.append(
            metric_row(
                analysis,
                exposure_column=exposure_column,
                period_label="overall",
                control="uncontrolled",
            )
        )
        metrics.append(
            controlled_metric_row(
                analysis,
                exposure_column=exposure_column,
                period_label="overall",
            )
        )

        for year, year_frame in analysis.groupby("year", sort=True):
            metrics.append(
                controlled_metric_row(
                    year_frame,
                    exposure_column=exposure_column,
                    period_label=str(year),
                )
            )

    metrics_df = pd.DataFrame(metrics)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(metrics_path, index=False)

    state_summary = (
        analysis.groupby("year", observed=True)[
            [
                "price_high_event",
                "high_residual_load",
                "low_renewable_share",
                "high_abs_residual_ramp",
                "composite_fundamental_stress",
            ]
        ]
        .mean()
        .reset_index()
    )

    state_summary.to_csv(state_path, index=False)

    overall_composite = metrics_df[
        (metrics_df["period"] == "overall")
        & (
            metrics_df["exposure"]
            == "composite_fundamental_stress"
        )
        & (
            metrics_df["control"]
            == "year_month_x_delivery_hour"
        )
    ].iloc[0].to_dict()

    annual_composite = metrics_df[
        (metrics_df["exposure"] == "composite_fundamental_stress")
        & (
            metrics_df["control"]
            == "year_month_x_delivery_hour"
        )
        & (metrics_df["period"] != "overall")
    ].copy()

    annual_positive_years = int(
        (
            annual_composite["event_rate_difference_pp"]
            .fillna(0)
            > 0
        ).sum()
    )

    summary = {
        "status": "DISCOVERY SCREEN COMPLETE",
        "scope": (
            "Ex-post association screen only. No causality, forecasting, "
            "tradability or pre-auction availability claim."
        ),
        "input_panel": str(input_path.as_posix()),
        "rows_input": int(len(df)),
        "rows_analysed": int(len(analysis)),
        "rows_excluded": int(len(df) - len(analysis)),
        "price_high_event_rate": float(
            analysis["price_high_event"].mean()
        ),
        "calendar_control": "year_month_x_delivery_hour",
        "fundamental_state_definition": (
            "Within-month percentile states: residual top decile, renewable "
            "share bottom decile, absolute residual ramp top decile; "
            "composite means at least two states."
        ),
        "overall_composite_controlled": overall_composite,
        "annual_composite_positive_lift_years": annual_positive_years,
        "annual_composite_years_available": int(len(annual_composite)),
        "metrics_csv": str(metrics_path.as_posix()),
        "state_summary_csv": str(state_path.as_posix()),
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Calendar-Controlled Market Discovery Screen",
        "",
        "## Scope",
        "",
        "This is an ex-post exploratory association screen. It does not show",
        "causality, forecastability, tradability or information availability",
        "before the day-ahead auction.",
        "",
        "## Analysis Input",
        "",
        f"- Input rows: `{summary['rows_input']}`",
        f"- Analysed rows: `{summary['rows_analysed']}`",
        f"- Excluded rows: `{summary['rows_excluded']}`",
        f"- High-price event rate: `{summary['price_high_event_rate']:.4f}`",
        f"- Calendar control: `{summary['calendar_control']}`",
        "",
        "## Composite Fundamental Stress",
        "",
        f"- Controlled exposed event rate: "
        f"`{overall_composite['exposed_event_rate']}`",
        f"- Controlled unexposed event rate: "
        f"`{overall_composite['unexposed_event_rate']}`",
        f"- Controlled event-rate difference (pp): "
        f"`{overall_composite['event_rate_difference_pp']}`",
        f"- Controlled relative lift: "
        f"`{overall_composite['relative_lift']}`",
        f"- Valid common-support strata: "
        f"`{overall_composite['valid_strata']}`",
        f"- Years with positive controlled lift: "
        f"`{annual_positive_years}` / "
        f"`{summary['annual_composite_years_available']}`",
        "",
        "## Reading Rule",
        "",
        "A positive result is only a candidate for robustness work. The next",
        "step is to inspect annual stability, exposure counts, concentration",
        "and alternative calendar controls before making any market claim.",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(
        "OK | discovery screen complete | "
        f"rows={len(analysis)} | "
        f"composite_controlled_lift_pp="
        f"{overall_composite['event_rate_difference_pp']}"
    )


if __name__ == "__main__":
    main()
