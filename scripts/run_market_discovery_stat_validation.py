from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "timestamp_utc",
    "price_eur_per_mwh",
    "residual_load_official_mw",
    "renewable_share",
    "residual_load_ramp_mw",
}


def as_float(value: float | int | None) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def two_sided_normal_pvalue(z_score: float | None) -> float | None:
    if z_score is None:
        return None

    return float(math.erfc(abs(z_score) / math.sqrt(2.0)))


def prepare_frame(source: pd.DataFrame) -> pd.DataFrame:
    frame = source.copy()

    for column in [
        "price_eur_per_mwh",
        "residual_load_official_mw",
        "renewable_share",
        "residual_load_ramp_mw",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["timestamp_utc"] = pd.to_datetime(
        frame["timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    required_raw = [
        "timestamp_utc",
        "price_eur_per_mwh",
        "residual_load_official_mw",
        "renewable_share",
        "residual_load_ramp_mw",
    ]

    frame = frame.loc[frame[required_raw].notna().all(axis=1)].copy()

    frame["timestamp_local"] = frame["timestamp_utc"].dt.tz_convert(
        "Europe/Berlin"
    )
    frame["year"] = frame["timestamp_local"].dt.year
    frame["year_month"] = frame["timestamp_local"].dt.strftime("%Y-%m")
    frame["delivery_hour"] = frame["timestamp_local"].dt.hour
    frame["is_weekend"] = frame["timestamp_local"].dt.dayofweek >= 5
    frame["abs_residual_load_ramp_mw"] = frame[
        "residual_load_ramp_mw"
    ].abs()

    monthly = frame.groupby("year_month", observed=True)

    frame["price_high_threshold"] = monthly["price_eur_per_mwh"].transform(
        lambda values: values.quantile(0.90)
    )
    frame["price_low_threshold"] = monthly["price_eur_per_mwh"].transform(
        lambda values: values.quantile(0.10)
    )
    frame["residual_high_threshold"] = monthly[
        "residual_load_official_mw"
    ].transform(lambda values: values.quantile(0.90))
    frame["renewable_low_threshold"] = monthly[
        "renewable_share"
    ].transform(lambda values: values.quantile(0.10))
    frame["ramp_high_threshold"] = monthly[
        "abs_residual_load_ramp_mw"
    ].transform(lambda values: values.quantile(0.90))

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
        frame["high_residual_load"] & frame["low_renewable_share"]
    )

    frame["composite_fundamental_stress"] = (
        frame[
            [
                "high_residual_load",
                "low_renewable_share",
                "high_abs_residual_ramp",
            ]
        ]
        .astype(int)
        .sum(axis=1)
        >= 2
    )

    conditions = [
        frame["high_residual_load"] & frame["low_renewable_share"],
        frame["high_residual_load"] & ~frame["low_renewable_share"],
        ~frame["high_residual_load"] & frame["low_renewable_share"],
    ]

    frame["residual_renewable_state"] = pd.Series(
        pd.NA,
        index=frame.index,
        dtype="string",
    )

    frame.loc[conditions[0], "residual_renewable_state"] = "both"
    frame.loc[conditions[1], "residual_renewable_state"] = "residual_only"
    frame.loc[conditions[2], "residual_renewable_state"] = "renewable_only"
    frame["residual_renewable_state"] = frame[
        "residual_renewable_state"
    ].fillna("neither")

    return frame


def stratified_association(
    frame: pd.DataFrame,
    *,
    exposure_column: str,
    outcome_column: str,
    strata_columns: list[str],
) -> dict[str, object]:
    observed_exposed_events = 0.0
    expected_exposed_events = 0.0
    variance_sum = 0.0

    mh_numerator = 0.0
    mh_denominator = 0.0

    weighted_exposed_rate = 0.0
    weighted_unexposed_rate = 0.0
    weight_sum = 0.0

    strata_with_both_groups = 0
    informative_strata = 0
    common_support_rows = 0

    exposed_rows = int(frame[exposure_column].sum())
    unexposed_rows = int((~frame[exposure_column]).sum())

    for _, group in frame.groupby(
        strata_columns,
        observed=True,
        sort=False,
    ):
        exposure = group[exposure_column].astype(bool)
        outcome = group[outcome_column].astype(bool)

        n_exposed = int(exposure.sum())
        n_unexposed = int((~exposure).sum())

        if n_exposed == 0 or n_unexposed == 0:
            continue

        strata_with_both_groups += 1
        common_support_rows += n_exposed + n_unexposed

        a = int((exposure & outcome).sum())
        b = int((exposure & ~outcome).sum())
        c = int((~exposure & outcome).sum())
        d = int((~exposure & ~outcome).sum())

        n_total = n_exposed + n_unexposed
        event_total = a + c

        harmonic_weight = (
            n_exposed * n_unexposed
        ) / n_total

        weighted_exposed_rate += harmonic_weight * (a / n_exposed)
        weighted_unexposed_rate += harmonic_weight * (c / n_unexposed)
        weight_sum += harmonic_weight

        expected = n_exposed * event_total / n_total

        if n_total > 1:
            variance = (
                n_exposed
                * n_unexposed
                * event_total
                * (n_total - event_total)
                / ((n_total**2) * (n_total - 1))
            )
        else:
            variance = 0.0

        observed_exposed_events += a
        expected_exposed_events += expected
        variance_sum += variance

        if variance > 0:
            informative_strata += 1

        mh_numerator += (a * d) / n_total
        mh_denominator += (b * c) / n_total

    if weight_sum == 0:
        exposed_rate = None
        unexposed_rate = None
        difference_pp = None
        relative_lift = None
    else:
        exposed_rate = weighted_exposed_rate / weight_sum
        unexposed_rate = weighted_unexposed_rate / weight_sum
        difference_pp = (exposed_rate - unexposed_rate) * 100
        relative_lift = (
            None if unexposed_rate == 0 else exposed_rate / unexposed_rate
        )

    cmh_z_score = (
        None
        if variance_sum <= 0
        else (observed_exposed_events - expected_exposed_events)
        / math.sqrt(variance_sum)
    )

    mh_common_odds_ratio = (
        None
        if mh_denominator == 0
        else mh_numerator / mh_denominator
    )

    return {
        "exposure": exposure_column,
        "outcome": outcome_column,
        "strata": "_x_".join(strata_columns),
        "exposed_rows": exposed_rows,
        "unexposed_rows": unexposed_rows,
        "strata_with_both_groups": int(strata_with_both_groups),
        "informative_strata": int(informative_strata),
        "weighted_common_support_rows": int(common_support_rows),
        "exposed_event_rate": as_float(exposed_rate),
        "unexposed_event_rate": as_float(unexposed_rate),
        "event_rate_difference_pp": as_float(difference_pp),
        "relative_lift": as_float(relative_lift),
        "mantel_haenszel_common_odds_ratio": as_float(
            mh_common_odds_ratio
        ),
        "cmh_z_score": as_float(cmh_z_score),
        "cmh_two_sided_p_value": as_float(
            two_sided_normal_pvalue(cmh_z_score)
        ),
    }


def pairwise_state_association(
    frame: pd.DataFrame,
    *,
    exposed_state: str,
    reference_state: str,
    outcome_column: str,
    strata_columns: list[str],
) -> dict[str, object]:
    subset = frame.loc[
        frame["residual_renewable_state"].isin(
            [exposed_state, reference_state]
        )
    ].copy()

    subset["pair_exposure"] = (
        subset["residual_renewable_state"] == exposed_state
    )

    result = stratified_association(
        subset,
        exposure_column="pair_exposure",
        outcome_column=outcome_column,
        strata_columns=strata_columns,
    )

    result["comparison"] = f"{exposed_state}_vs_{reference_state}"
    result["subset_rows"] = int(len(subset))

    return result


def write_markdown_report(
    *,
    output_path: Path,
    summary: dict[str, object],
) -> None:
    composite_high = summary["composite_high_price"]
    composite_low = summary["composite_low_price"]
    joint = summary["joint_state_vs_neither"]
    ramp = summary["conditional_ramp_increment"]

    lines = [
        "# Market Discovery Statistical Validation",
        "",
        "## Boundary",
        "",
        "This is a conditional ex-post association analysis. It does not",
        "demonstrate causality, forecastability, tradability or data",
        "availability before the day-ahead auction.",
        "",
        "## Composite Fundamental Stress",
        "",
        f"- High-price event-rate difference: "
        f"`{composite_high['event_rate_difference_pp']}` pp",
        f"- High-price relative lift: "
        f"`{composite_high['relative_lift']}`",
        f"- Mantel-Haenszel common odds ratio: "
        f"`{composite_high['mantel_haenszel_common_odds_ratio']}`",
        f"- CMH z-score: `{composite_high['cmh_z_score']}`",
        f"- CMH two-sided p-value: "
        f"`{composite_high['cmh_two_sided_p_value']}`",
        f"- Informative calendar strata: "
        f"`{composite_high['informative_strata']}`",
        "",
        "## Low-Price Sanity Check",
        "",
        f"- Low-price event-rate difference: "
        f"`{composite_low['event_rate_difference_pp']}` pp",
        f"- Low-price relative lift: "
        f"`{composite_low['relative_lift']}`",
        f"- Mantel-Haenszel common odds ratio: "
        f"`{composite_low['mantel_haenszel_common_odds_ratio']}`",
        "",
        "## Joint Residual / Renewable State",
        "",
        f"- Comparison: `{joint['comparison']}`",
        f"- High-price event-rate difference: "
        f"`{joint['event_rate_difference_pp']}` pp",
        f"- Mantel-Haenszel common odds ratio: "
        f"`{joint['mantel_haenszel_common_odds_ratio']}`",
        f"- CMH z-score: `{joint['cmh_z_score']}`",
        "",
        "## Conditional Ramp Increment",
        "",
        "- Population: high residual load and low renewable share hours only.",
        f"- High-price event-rate difference: "
        f"`{ramp['event_rate_difference_pp']}` pp",
        f"- Mantel-Haenszel common odds ratio: "
        f"`{ramp['mantel_haenszel_common_odds_ratio']}`",
        f"- CMH z-score: `{ramp['cmh_z_score']}`",
        f"- Informative strata: `{ramp['informative_strata']}`",
        "",
        "## Reading Rule",
        "",
        "Statistical evidence here validates conditional association under",
        "the specified strata. It does not establish a causal mechanism or",
        "an executable price-trading signal.",
        "",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-panel", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-report", required=True)
    parser.add_argument("--metrics-csv", required=True)
    parser.add_argument("--mechanism-csv", required=True)
    args = parser.parse_args()

    input_path = Path(args.input_panel)
    output_json = Path(args.output_json)
    output_report = Path(args.output_report)
    metrics_csv = Path(args.metrics_csv)
    mechanism_csv = Path(args.mechanism_csv)

    source = pd.read_csv(input_path)

    missing_columns = sorted(REQUIRED_COLUMNS - set(source.columns))
    if missing_columns:
        raise ValueError(
            f"Input panel is missing required columns: {missing_columns}"
        )

    frame = prepare_frame(source)

    strata = [
        "year_month",
        "delivery_hour",
        "is_weekend",
    ]

    exposures = [
        "high_residual_load",
        "low_renewable_share",
        "high_abs_residual_ramp",
        "high_residual_and_low_renewable",
        "composite_fundamental_stress",
    ]

    metric_rows: list[dict[str, object]] = []

    for outcome in ["price_high_event", "price_low_event"]:
        for exposure in exposures:
            metric_rows.append(
                stratified_association(
                    frame,
                    exposure_column=exposure,
                    outcome_column=outcome,
                    strata_columns=strata,
                )
            )

    metrics = pd.DataFrame(metric_rows)
    metrics_csv.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(metrics_csv, index=False)

    mechanism_rows = []

    for exposed_state, reference_state in [
        ("residual_only", "neither"),
        ("renewable_only", "neither"),
        ("both", "neither"),
        ("both", "residual_only"),
        ("both", "renewable_only"),
    ]:
        mechanism_rows.append(
            pairwise_state_association(
                frame,
                exposed_state=exposed_state,
                reference_state=reference_state,
                outcome_column="price_high_event",
                strata_columns=strata,
            )
        )

    pair_population = frame.loc[
        frame["high_residual_and_low_renewable"]
    ].copy()

    ramp_increment = stratified_association(
        pair_population,
        exposure_column="high_abs_residual_ramp",
        outcome_column="price_high_event",
        strata_columns=strata,
    )
    ramp_increment["comparison"] = (
        "ramp_high_vs_ramp_low_within_high_residual_and_low_renewable"
    )
    ramp_increment["subset_rows"] = int(len(pair_population))

    mechanism_rows.append(ramp_increment)

    mechanism = pd.DataFrame(mechanism_rows)
    mechanism.to_csv(mechanism_csv, index=False)

    def select_metric(
        exposure: str,
        outcome: str,
    ) -> dict[str, object]:
        selection = metrics.loc[
            (metrics["exposure"] == exposure)
            & (metrics["outcome"] == outcome)
        ]

        if len(selection) != 1:
            raise RuntimeError(
                f"Expected exactly one metric for {exposure} / {outcome}."
            )

        return selection.iloc[0].to_dict()

    joint = mechanism.loc[
        mechanism["comparison"] == "both_vs_neither"
    ].iloc[0].to_dict()

    summary = {
        "status": "STATISTICAL VALIDATION SCREEN COMPLETE",
        "scope": (
            "Conditional ex-post association only. No causality, forecasting, "
            "tradability or pre-auction information claim."
        ),
        "input_panel": str(input_path.as_posix()),
        "input_rows": int(len(source)),
        "analysed_rows": int(len(frame)),
        "excluded_rows": int(len(source) - len(frame)),
        "calendar_strata": strata,
        "composite_high_price": select_metric(
            "composite_fundamental_stress",
            "price_high_event",
        ),
        "composite_low_price": select_metric(
            "composite_fundamental_stress",
            "price_low_event",
        ),
        "joint_state_vs_neither": joint,
        "conditional_ramp_increment": ramp_increment,
        "metrics_csv": str(metrics_csv.as_posix()),
        "mechanism_csv": str(mechanism_csv.as_posix()),
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    write_markdown_report(
        output_path=output_report,
        summary=summary,
    )

    composite = summary["composite_high_price"]

    print(
        "OK | statistical validation complete | "
        f"rows={len(frame)} | "
        f"composite_mh_or="
        f"{composite['mantel_haenszel_common_odds_ratio']} | "
        f"composite_cmh_z={composite['cmh_z_score']}"
    )


if __name__ == "__main__":
    main()
