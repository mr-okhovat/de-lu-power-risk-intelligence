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


def as_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def controlled_binary_metric(
    frame: pd.DataFrame,
    *,
    exposure: str,
    outcome: str,
    strata: list[str],
) -> dict[str, object]:
    weighted_exposed_rate = 0.0
    weighted_unexposed_rate = 0.0
    total_weight = 0.0
    valid_strata = 0
    common_support_rows = 0

    for _, group in frame.groupby(strata, sort=False, observed=True):
        exposed = group[group[exposure]]
        unexposed = group[~group[exposure]]

        n_exposed = len(exposed)
        n_unexposed = len(unexposed)

        if n_exposed == 0 or n_unexposed == 0:
            continue

        weight = (n_exposed * n_unexposed) / (n_exposed + n_unexposed)

        weighted_exposed_rate += weight * float(exposed[outcome].mean())
        weighted_unexposed_rate += weight * float(unexposed[outcome].mean())
        total_weight += weight
        valid_strata += 1
        common_support_rows += n_exposed + n_unexposed

    if total_weight == 0:
        exposed_rate = None
        unexposed_rate = None
        difference_pp = None
        relative_lift = None
    else:
        exposed_rate = weighted_exposed_rate / total_weight
        unexposed_rate = weighted_unexposed_rate / total_weight
        difference_pp = (exposed_rate - unexposed_rate) * 100
        relative_lift = (
            None if unexposed_rate == 0 else exposed_rate / unexposed_rate
        )

    return {
        "exposed_event_rate": as_float(exposed_rate),
        "unexposed_event_rate": as_float(unexposed_rate),
        "difference_pp": as_float(difference_pp),
        "relative_lift": as_float(relative_lift),
        "valid_strata": int(valid_strata),
        "weighted_common_support_rows": int(common_support_rows),
        "exposed_rows": int(frame[exposure].sum()),
        "unexposed_rows": int((~frame[exposure]).sum()),
    }


def controlled_price_difference(
    frame: pd.DataFrame,
    *,
    exposure: str,
    strata: list[str],
) -> dict[str, object]:
    weighted_exposed_mean = 0.0
    weighted_unexposed_mean = 0.0
    total_weight = 0.0
    valid_strata = 0

    for _, group in frame.groupby(strata, sort=False, observed=True):
        exposed = group[group[exposure]]
        unexposed = group[~group[exposure]]

        n_exposed = len(exposed)
        n_unexposed = len(unexposed)

        if n_exposed == 0 or n_unexposed == 0:
            continue

        weight = (n_exposed * n_unexposed) / (n_exposed + n_unexposed)

        weighted_exposed_mean += (
            weight * float(exposed["price_eur_per_mwh"].mean())
        )
        weighted_unexposed_mean += (
            weight * float(unexposed["price_eur_per_mwh"].mean())
        )
        total_weight += weight
        valid_strata += 1

    if total_weight == 0:
        exposed_mean = None
        unexposed_mean = None
        difference = None
    else:
        exposed_mean = weighted_exposed_mean / total_weight
        unexposed_mean = weighted_unexposed_mean / total_weight
        difference = exposed_mean - unexposed_mean

    return {
        "exposed_price_mean_eur_per_mwh": as_float(exposed_mean),
        "unexposed_price_mean_eur_per_mwh": as_float(unexposed_mean),
        "difference_eur_per_mwh": as_float(difference),
        "valid_strata": int(valid_strata),
    }


def build_states(
    source: pd.DataFrame,
    *,
    price_high_q: float,
    fundamental_high_q: float,
    fundamental_low_q: float,
) -> pd.DataFrame:
    frame = source.copy()

    numeric_columns = [
        "price_eur_per_mwh",
        "residual_load_official_mw",
        "renewable_share",
        "residual_load_ramp_mw",
    ]

    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["timestamp_utc"] = pd.to_datetime(
        frame["timestamp_utc"],
        utc=True,
        errors="coerce",
    )
    frame["timestamp_local"] = frame["timestamp_utc"].dt.tz_convert(
        "Europe/Berlin"
    )

    valid_inputs = [
        "timestamp_utc",
        "price_eur_per_mwh",
        "residual_load_official_mw",
        "renewable_share",
        "residual_load_ramp_mw",
    ]

    frame = frame.loc[frame[valid_inputs].notna().all(axis=1)].copy()

    frame["year"] = frame["timestamp_local"].dt.year
    frame["year_month"] = frame["timestamp_local"].dt.strftime("%Y-%m")
    frame["delivery_hour"] = frame["timestamp_local"].dt.hour
    frame["is_weekend"] = (
        frame["timestamp_local"].dt.dayofweek >= 5
    )

    frame["abs_residual_load_ramp_mw"] = (
        frame["residual_load_ramp_mw"].abs()
    )

    monthly = frame.groupby("year_month", observed=True)

    frame["price_high_threshold"] = monthly["price_eur_per_mwh"].transform(
        lambda values: values.quantile(price_high_q)
    )
    frame["price_low_threshold"] = monthly["price_eur_per_mwh"].transform(
        lambda values: values.quantile(0.10)
    )
    frame["residual_high_threshold"] = monthly[
        "residual_load_official_mw"
    ].transform(lambda values: values.quantile(fundamental_high_q))
    frame["renewable_low_threshold"] = monthly[
        "renewable_share"
    ].transform(lambda values: values.quantile(fundamental_low_q))
    frame["ramp_high_threshold"] = monthly[
        "abs_residual_load_ramp_mw"
    ].transform(lambda values: values.quantile(fundamental_high_q))

    frame["price_high_event"] = (
        frame["price_eur_per_mwh"] >= frame["price_high_threshold"]
    )
    frame["price_low_event"] = (
        frame["price_eur_per_mwh"] <= frame["price_low_threshold"]
    )

    frame["high_residual_load"] = (
        frame["residual_load_official_mw"]
        >= frame["residual_high_threshold"]
    )
    frame["low_renewable_share"] = (
        frame["renewable_share"]
        <= frame["renewable_low_threshold"]
    )
    frame["high_abs_residual_ramp"] = (
        frame["abs_residual_load_ramp_mw"]
        >= frame["ramp_high_threshold"]
    )
    frame["high_residual_and_low_renewable"] = (
        frame["high_residual_load"]
        & frame["low_renewable_share"]
    )

    state_columns = [
        "high_residual_load",
        "low_renewable_share",
        "high_abs_residual_ramp",
    ]

    frame["fundamental_stress_count"] = frame[state_columns].sum(axis=1)
    frame["composite_fundamental_stress"] = (
        frame["fundamental_stress_count"] >= 2
    )

    conditions = [
        (
            frame["high_residual_load"]
            & frame["low_renewable_share"]
            & frame["high_abs_residual_ramp"]
        ),
        (
            frame["high_residual_load"]
            & frame["low_renewable_share"]
        ),
        (
            frame["high_residual_load"]
            & frame["high_abs_residual_ramp"]
        ),
        (
            frame["low_renewable_share"]
            & frame["high_abs_residual_ramp"]
        ),
        frame["high_residual_load"],
        frame["low_renewable_share"],
        frame["high_abs_residual_ramp"],
    ]

    labels = [
        "residual_renewable_ramp",
        "residual_renewable",
        "residual_ramp",
        "renewable_ramp",
        "residual_only",
        "renewable_only",
        "ramp_only",
    ]

    frame["state_combination"] = np.select(
        conditions,
        labels,
        default="no_state",
    )

    return frame


def add_scenario_metrics(
    rows: list[dict[str, object]],
    *,
    frame: pd.DataFrame,
    scenario: str,
    price_high_q: float,
    fundamental_high_q: float,
    fundamental_low_q: float,
) -> None:
    controls = {
        "year_month_x_delivery_hour": ["year_month", "delivery_hour"],
        "year_month_x_delivery_hour_x_weekend": [
            "year_month",
            "delivery_hour",
            "is_weekend",
        ],
    }

    exposures = [
        "high_residual_load",
        "low_renewable_share",
        "high_abs_residual_ramp",
        "high_residual_and_low_renewable",
        "composite_fundamental_stress",
    ]

    for control_name, strata in controls.items():
        for exposure in exposures:
            high = controlled_binary_metric(
                frame,
                exposure=exposure,
                outcome="price_high_event",
                strata=strata,
            )
            low = controlled_binary_metric(
                frame,
                exposure=exposure,
                outcome="price_low_event",
                strata=strata,
            )
            price = controlled_price_difference(
                frame,
                exposure=exposure,
                strata=strata,
            )

            rows.append(
                {
                    "scenario": scenario,
                    "price_high_q": price_high_q,
                    "fundamental_high_q": fundamental_high_q,
                    "fundamental_low_q": fundamental_low_q,
                    "exposure": exposure,
                    "control": control_name,
                    "high_price_exposed_rate": high["exposed_event_rate"],
                    "high_price_unexposed_rate": high[
                        "unexposed_event_rate"
                    ],
                    "high_price_difference_pp": high["difference_pp"],
                    "high_price_relative_lift": high["relative_lift"],
                    "low_price_exposed_rate": low["exposed_event_rate"],
                    "low_price_unexposed_rate": low[
                        "unexposed_event_rate"
                    ],
                    "low_price_difference_pp": low["difference_pp"],
                    "price_difference_eur_per_mwh": price[
                        "difference_eur_per_mwh"
                    ],
                    "valid_strata": high["valid_strata"],
                    "weighted_common_support_rows": high[
                        "weighted_common_support_rows"
                    ],
                    "exposed_rows": high["exposed_rows"],
                    "unexposed_rows": high["unexposed_rows"],
                }
            )


def build_stability(
    frame: pd.DataFrame,
    *,
    period_column: str,
    period_type: str,
    strata: list[str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for period, group in frame.groupby(period_column, sort=True, observed=True):
        metric = controlled_binary_metric(
            group,
            exposure="composite_fundamental_stress",
            outcome="price_high_event",
            strata=strata,
        )

        rows.append(
            {
                "period_type": period_type,
                "period": str(period),
                "rows": int(len(group)),
                "exposed_rows": metric["exposed_rows"],
                "high_price_exposed_rate": metric["exposed_event_rate"],
                "high_price_unexposed_rate": metric[
                    "unexposed_event_rate"
                ],
                "high_price_difference_pp": metric["difference_pp"],
                "high_price_relative_lift": metric["relative_lift"],
                "valid_strata": metric["valid_strata"],
                "weighted_common_support_rows": metric[
                    "weighted_common_support_rows"
                ],
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-panel", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--scenario-metrics-csv", required=True)
    parser.add_argument("--stability-csv", required=True)
    parser.add_argument("--combination-csv", required=True)
    args = parser.parse_args()

    input_path = Path(args.input_panel)
    summary_path = Path(args.summary_json)
    report_path = Path(args.report)
    scenario_path = Path(args.scenario_metrics_csv)
    stability_path = Path(args.stability_csv)
    combination_path = Path(args.combination_csv)

    source = pd.read_csv(input_path)
    missing = sorted(REQUIRED_COLUMNS - set(source.columns))

    if missing:
        raise ValueError(f"Missing required input columns: {missing}")

    scenarios = [
        ("base_p90", 0.90, 0.90, 0.10),
        ("price_p85", 0.85, 0.90, 0.10),
        ("price_p95", 0.95, 0.90, 0.10),
        ("states_p85_p15", 0.90, 0.85, 0.15),
        ("states_p95_p05", 0.90, 0.95, 0.05),
    ]

    scenario_rows: list[dict[str, object]] = []
    frames: dict[str, pd.DataFrame] = {}

    for scenario, price_q, high_q, low_q in scenarios:
        frame = build_states(
            source,
            price_high_q=price_q,
            fundamental_high_q=high_q,
            fundamental_low_q=low_q,
        )
        frames[scenario] = frame

        add_scenario_metrics(
            scenario_rows,
            frame=frame,
            scenario=scenario,
            price_high_q=price_q,
            fundamental_high_q=high_q,
            fundamental_low_q=low_q,
        )

    metrics = pd.DataFrame(scenario_rows)
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(scenario_path, index=False)

    base = frames["base_p90"]

    stability_rows = []
    stability_rows.extend(
        build_stability(
            base,
            period_column="year",
            period_type="year",
            strata=["year_month", "delivery_hour"],
        )
    )
    stability_rows.extend(
        build_stability(
            base,
            period_column="year_month",
            period_type="year_month",
            strata=["delivery_hour"],
        )
    )

    stability = pd.DataFrame(stability_rows)
    stability.to_csv(stability_path, index=False)

    combinations = (
        base.groupby("state_combination", observed=True)
        .agg(
            rows=("state_combination", "size"),
            high_price_event_rate=("price_high_event", "mean"),
            low_price_event_rate=("price_low_event", "mean"),
            mean_price_eur_per_mwh=("price_eur_per_mwh", "mean"),
            median_price_eur_per_mwh=("price_eur_per_mwh", "median"),
        )
        .reset_index()
        .sort_values("rows", ascending=False)
    )
    combinations.to_csv(combination_path, index=False)

    pair_frame = base.loc[
        base["high_residual_and_low_renewable"]
    ].copy()

    ramp_increment = controlled_binary_metric(
        pair_frame,
        exposure="high_abs_residual_ramp",
        outcome="price_high_event",
        strata=["year_month", "delivery_hour"],
    )

    selected = metrics[
        (
            metrics["control"]
            == "year_month_x_delivery_hour"
        )
        & (
            metrics["exposure"]
            == "composite_fundamental_stress"
        )
    ].copy()

    base_composite = selected[
        selected["scenario"] == "base_p90"
    ].iloc[0].to_dict()

    annual = stability[stability["period_type"] == "year"].copy()
    monthly = stability[stability["period_type"] == "year_month"].copy()

    annual_positive = int(
        (annual["high_price_difference_pp"].fillna(0) > 0).sum()
    )
    monthly_positive = int(
        (monthly["high_price_difference_pp"].fillna(0) > 0).sum()
    )

    scenario_positive = int(
        (selected["high_price_difference_pp"].fillna(0) > 0).sum()
    )

    summary = {
        "status": "ROBUSTNESS SCREEN COMPLETE",
        "scope": (
            "Ex-post association only. No causality, forecasting, tradability "
            "or pre-auction information claim."
        ),
        "input_rows": int(len(source)),
        "base_rows_after_explicit_non_null_filter": int(len(base)),
        "base_rows_excluded_for_missing_raw_inputs": int(
            len(source) - len(base)
        ),
        "base_composite": base_composite,
        "annual_positive_controlled_lift_years": annual_positive,
        "annual_years_available": int(len(annual)),
        "monthly_positive_controlled_lift_months": monthly_positive,
        "monthly_months_available": int(len(monthly)),
        "positive_composite_threshold_scenarios": scenario_positive,
        "composite_threshold_scenarios_available": int(len(selected)),
        "ramp_increment_within_high_residual_and_low_renewable": ramp_increment,
        "scenario_metrics_csv": str(scenario_path.as_posix()),
        "stability_csv": str(stability_path.as_posix()),
        "combination_csv": str(combination_path.as_posix()),
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Market Discovery Robustness Screen",
        "",
        "## Scope",
        "",
        "This is an ex-post association screen. It does not establish causality,",
        "forecastability, trading value or information availability before the",
        "day-ahead auction.",
        "",
        "## Input",
        "",
        f"- Input rows: `{summary['input_rows']}`",
        f"- Rows after explicit raw-input completeness check: "
        f"`{summary['base_rows_after_explicit_non_null_filter']}`",
        f"- Rows excluded for missing raw inputs: "
        f"`{summary['base_rows_excluded_for_missing_raw_inputs']}`",
        "",
        "## Base Composite Result",
        "",
        f"- Controlled high-price difference: "
        f"`{base_composite['high_price_difference_pp']}` pp",
        f"- Controlled relative lift: "
        f"`{base_composite['high_price_relative_lift']}`",
        f"- Controlled price difference: "
        f"`{base_composite['price_difference_eur_per_mwh']}` EUR/MWh",
        f"- Valid common-support strata: "
        f"`{base_composite['valid_strata']}`",
        "",
        "## Directional Stability",
        "",
        f"- Positive years: `{annual_positive}` / `{len(annual)}`",
        f"- Positive months: `{monthly_positive}` / `{len(monthly)}`",
        f"- Positive threshold scenarios: `{scenario_positive}` / "
        f"`{len(selected)}`",
        "",
        "## Conditional Ramp Check",
        "",
        "- Population: hours already meeting high residual load and low",
        "  renewable share conditions.",
        f"- Ramp-high exposed event rate: "
        f"`{ramp_increment['exposed_event_rate']}`",
        f"- Ramp-low event rate: "
        f"`{ramp_increment['unexposed_event_rate']}`",
        f"- Incremental ramp difference: "
        f"`{ramp_increment['difference_pp']}` pp",
        f"- Incremental ramp lift: `{ramp_increment['relative_lift']}`",
        f"- Valid support strata: `{ramp_increment['valid_strata']}`",
        "",
        "## Interpretation Rule",
        "",
        "The result is worth deeper mechanism work only when direction remains",
        "stable across threshold choices and supported calendar strata. It is",
        "still not a forecasting or tradability result.",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(
        "OK | robustness screen complete | "
        f"base_composite_lift_pp="
        f"{base_composite['high_price_difference_pp']} | "
        f"positive_years={annual_positive}/{len(annual)} | "
        f"positive_months={monthly_positive}/{len(monthly)}"
    )


if __name__ == "__main__":
    main()
