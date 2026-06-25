from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_market_discovery_robustness import (
    build_states,
    controlled_binary_metric,
)


BASE_STRATA = [
    "year_month",
    "delivery_hour",
    "is_weekend",
]

MONTH_STRATA = [
    "delivery_hour",
    "is_weekend",
]


def number(value: object) -> float | int | None:
    if value is None or pd.isna(value):
        return None

    if isinstance(value, (np.integer, int)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        return float(value)

    return value


def clean_record(record: dict[str, object]) -> dict[str, object]:
    return {key: number(value) for key, value in record.items()}


def controlled_metric(
    frame: pd.DataFrame,
    *,
    exposure: str,
    strata: list[str],
) -> dict[str, object]:
    return controlled_binary_metric(
        frame,
        exposure=exposure,
        outcome="price_high_event",
        strata=strata,
    )


def monthly_effects(
    frame: pd.DataFrame,
    *,
    exposure: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for period, group in frame.groupby("year_month", observed=True, sort=True):
        metric = controlled_metric(
            group,
            exposure=exposure,
            strata=MONTH_STRATA,
        )

        difference_pp = metric["difference_pp"]
        support = metric["weighted_common_support_rows"]

        if difference_pp is None or support is None or support <= 0:
            continue

        rows.append(
            {
                "year_month": str(period),
                "year": int(group["year"].iloc[0]),
                "difference_pp": float(difference_pp),
                "relative_lift": number(metric["relative_lift"]),
                "weighted_common_support_rows": int(support),
                "exposed_rows": int(metric["exposed_rows"]),
                "valid_strata": int(metric["valid_strata"]),
            }
        )

    return pd.DataFrame(rows)


def weighted_effect(monthly: pd.DataFrame) -> float:
    values = monthly["difference_pp"].to_numpy(dtype=float)
    weights = monthly["weighted_common_support_rows"].to_numpy(dtype=float)

    return float(np.average(values, weights=weights))


def bootstrap_month_blocks(
    monthly: pd.DataFrame,
    *,
    repetitions: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, float]]:
    rng = np.random.default_rng(seed)

    values = monthly["difference_pp"].to_numpy(dtype=float)
    weights = monthly["weighted_common_support_rows"].to_numpy(dtype=float)

    draws = np.empty(repetitions, dtype=float)
    count = len(monthly)

    for index in range(repetitions):
        sampled = rng.integers(0, count, size=count)
        draws[index] = np.average(
            values[sampled],
            weights=weights[sampled],
        )

    summary = {
        "point_estimate_pp": weighted_effect(monthly),
        "bootstrap_mean_pp": float(draws.mean()),
        "bootstrap_std_pp": float(draws.std(ddof=1)),
        "bootstrap_ci_025_pp": float(np.quantile(draws, 0.025)),
        "bootstrap_ci_500_pp": float(np.quantile(draws, 0.50)),
        "bootstrap_ci_975_pp": float(np.quantile(draws, 0.975)),
    }

    return draws, summary


def leave_one_year_out(
    monthly: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for year in sorted(monthly["year"].unique()):
        subset = monthly.loc[monthly["year"] != year].copy()

        rows.append(
            {
                "held_out_year": int(year),
                "months_used": int(len(subset)),
                "effect_pp": weighted_effect(subset),
                "min_month_effect_pp": float(subset["difference_pp"].min()),
                "max_month_effect_pp": float(subset["difference_pp"].max()),
            }
        )

    return pd.DataFrame(rows)


def circular_weekly_placebo(
    frame: pd.DataFrame,
    *,
    shift_hours: int,
) -> pd.DataFrame:
    shifted = frame.copy()

    for _, group in shifted.groupby(
        "year_month",
        observed=True,
        sort=False,
    ):
        ordered_index = group.sort_values("timestamp_utc").index
        values = shifted.loc[
            ordered_index,
            "price_high_event",
        ].astype(bool).to_numpy()

        shifted.loc[ordered_index, "price_high_event"] = np.roll(
            values,
            shift_hours,
        )

    return shifted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-panel", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--month-blocks-csv", required=True)
    parser.add_argument("--leave-one-year-out-csv", required=True)
    parser.add_argument("--placebos-csv", required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=5000)
    args = parser.parse_args()

    input_path = Path(args.input_panel)
    summary_path = Path(args.summary_json)
    report_path = Path(args.report)
    month_blocks_path = Path(args.month_blocks_csv)
    loyo_path = Path(args.leave_one_year_out_csv)
    placebos_path = Path(args.placebos_csv)

    source = pd.read_csv(input_path)

    frame = build_states(
        source,
        price_high_q=0.90,
        fundamental_high_q=0.90,
        fundamental_low_q=0.10,
    )

    exposure = "composite_fundamental_stress"

    observed_metric = clean_record(
        controlled_metric(
            frame,
            exposure=exposure,
            strata=BASE_STRATA,
        )
    )

    monthly = monthly_effects(
        frame,
        exposure=exposure,
    )

    if len(monthly) < 24:
        raise RuntimeError(
            "Insufficient valid monthly blocks for confirmation analysis."
        )

    _, bootstrap = bootstrap_month_blocks(
        monthly,
        repetitions=args.bootstrap_repetitions,
        seed=20260625,
    )

    loyo = leave_one_year_out(monthly)

    placebo_rows: list[dict[str, object]] = [
        {
            "alignment": "observed",
            "shift_hours": 0,
            **observed_metric,
        }
    ]

    for shift_hours in [168, 336, 504, -168, -336, -504]:
        shifted = circular_weekly_placebo(
            frame,
            shift_hours=shift_hours,
        )

        metric = clean_record(
            controlled_metric(
                shifted,
                exposure=exposure,
                strata=BASE_STRATA,
            )
        )

        placebo_rows.append(
            {
                "alignment": "weekly_circular_placebo",
                "shift_hours": shift_hours,
                **metric,
            }
        )

    placebos = pd.DataFrame(placebo_rows)

    observed_effect = float(observed_metric["difference_pp"])
    placebo_effects = placebos.loc[
        placebos["alignment"] == "weekly_circular_placebo",
        "difference_pp",
    ].dropna()

    all_loyo_positive = bool((loyo["effect_pp"] > 0).all())
    bootstrap_positive = bool(bootstrap["bootstrap_ci_025_pp"] > 0)
    observed_exceeds_placebos = bool(
        observed_effect > float(placebo_effects.max())
    )

    decision = (
        "CONFIRMATION GATE PASSED"
        if (
            all_loyo_positive
            and bootstrap_positive
            and observed_exceeds_placebos
        )
        else "CONFIRMATION GATE HOLD"
    )

    month_blocks_path.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(month_blocks_path, index=False)
    loyo.to_csv(loyo_path, index=False)
    placebos.to_csv(placebos_path, index=False)

    summary = {
        "status": decision,
        "scope": (
            "Ex-post explanatory association only. No causality, forecasting, "
            "tradability or pre-auction information claim."
        ),
        "input_rows": int(len(source)),
        "analysed_rows": int(len(frame)),
        "excluded_rows": int(len(source) - len(frame)),
        "exposure": exposure,
        "calendar_strata": BASE_STRATA,
        "observed_controlled_metric": observed_metric,
        "monthly_block_count": int(len(monthly)),
        "monthly_block_bootstrap": bootstrap,
        "leave_one_year_out": [
            clean_record(row)
            for row in loyo.to_dict(orient="records")
        ],
        "placebos": [
            clean_record(row)
            for row in placebos.to_dict(orient="records")
        ],
        "checks": {
            "monthly_block_bootstrap_ci_positive": bootstrap_positive,
            "all_leave_one_year_out_effects_positive": all_loyo_positive,
            "observed_effect_exceeds_weekly_placebos": (
                observed_exceeds_placebos
            ),
        },
        "artifacts": {
            "monthly_blocks_csv": str(month_blocks_path.as_posix()),
            "leave_one_year_out_csv": str(loyo_path.as_posix()),
            "placebos_csv": str(placebos_path.as_posix()),
        },
    }

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    lines = [
        "# Market Discovery Confirmation Gate",
        "",
        "## Scope",
        "",
        "This is ex-post explanatory research. It does not establish causality,",
        "forecastability, tradability or pre-auction information availability.",
        "",
        "## Observed Aligned Effect",
        "",
        f"- Controlled high-price difference: `{observed_effect:.3f}` pp",
        f"- Controlled relative lift: "
        f"`{observed_metric['relative_lift']}`",
        f"- Common-support rows: "
        f"`{observed_metric['weighted_common_support_rows']}`",
        "",
        "## Monthly Block Bootstrap",
        "",
        f"- Valid monthly blocks: `{len(monthly)}`",
        f"- Point estimate: `{bootstrap['point_estimate_pp']:.3f}` pp",
        f"- 95% block-bootstrap interval: "
        f"`[{bootstrap['bootstrap_ci_025_pp']:.3f}, "
        f"{bootstrap['bootstrap_ci_975_pp']:.3f}]` pp",
        "",
        "## Leave-One-Year-Out",
        "",
        f"- Lowest retained-year effect: `{loyo['effect_pp'].min():.3f}` pp",
        f"- Highest retained-year effect: `{loyo['effect_pp'].max():.3f}` pp",
        f"- All positive: `{all_loyo_positive}`",
        "",
        "## Weekly Circular Placebos",
        "",
        f"- Observed aligned effect: `{observed_effect:.3f}` pp",
        f"- Maximum placebo effect: `{placebo_effects.max():.3f}` pp",
        f"- Observed exceeds every placebo: `{observed_exceeds_placebos}`",
        "",
        "## Gate Decision",
        "",
        f"- Status: `{decision}`",
        "",
        "A passed gate supports deeper mechanism and literature work. It still",
        "does not turn this result into a trading signal or causal market claim.",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(
        f"OK | confirmation={decision} | "
        f"observed_pp={observed_effect:.3f} | "
        f"bootstrap_ci=[{bootstrap['bootstrap_ci_025_pp']:.3f}, "
        f"{bootstrap['bootstrap_ci_975_pp']:.3f}]"
    )


if __name__ == "__main__":
    main()
