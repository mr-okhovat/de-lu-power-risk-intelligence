from __future__ import annotations

import argparse
from pathlib import Path

from src.prices.price_table import build as build_price_table
from src.prices.price_risk_panel import build as build_panel
from src.prices.price_events import build as build_events
from src.prices.signal_price_evaluation import build as build_evaluation
from src.prices.price_risk_behavior import build as build_behavior


def paths(start: str, end: str, market: str) -> dict[str, str]:
    tag = f"{market}_{start}_to_{end}"
    rtag = f"{start}_to_{end}"

    return {
        "features": f"data/processed/hourly_features_{tag}.csv",
        "prices": f"data/processed/hourly_prices_{tag}.csv",
        "risk": f"data/processed/risk_signals_{tag}.csv",
        "panel": f"data/processed/price_risk_panel_{tag}.csv",
        "events": f"data/processed/price_events_{tag}.csv",
        "evaluation": f"data/processed/signal_price_evaluation_{tag}.csv",

        "price_quality_report": f"reports/price_quality_{rtag}.md",
        "price_quality_json": f"reports/price_quality_{rtag}.json",
        "panel_quality_report": f"reports/price_risk_panel_quality_{rtag}.md",
        "panel_quality_json": f"reports/price_risk_panel_quality_{rtag}.json",
        "events_report": f"reports/price_events_{rtag}.md",
        "events_json": f"reports/price_events_{rtag}.json",
        "evaluation_report": f"reports/signal_price_evaluation_{rtag}.md",
        "evaluation_json": f"reports/signal_price_evaluation_{rtag}.json",
        "behavior_report": f"reports/price_risk_behavior_{rtag}.md",
        "behavior_json": f"reports/price_risk_behavior_{rtag}.json",

        "confusion": f"dashboards/signal_price_confusion_{tag}.csv",
        "event_summary": f"dashboards/signal_price_event_summary_{tag}.csv",
        "bucket": f"dashboards/price_risk_bucket_profile_{tag}.csv",
        "regime": f"dashboards/price_risk_regime_profile_{tag}.csv",
        "reason": f"dashboards/price_risk_reason_profile_{tag}.csv",
        "quantiles": f"dashboards/price_risk_quantiles_{tag}.csv",
        "top": f"dashboards/price_risk_top_cases_{tag}.csv",
    }


def ensure_inputs(p: dict[str, str]) -> None:
    required = ["features", "risk"]

    missing = [item for item in required if not Path(p[item]).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required inputs: {missing}")


def run_month(
    *,
    start: str,
    end: str,
    market: str,
    region: str,
    filter_id: str,
    resolution: str,
    signal_threshold: float,
    high_q: float,
    low_q: float,
    ramp_q: float,
    top_n: int,
) -> None:
    p = paths(start, end, market)
    ensure_inputs(p)

    build_price_table(
        start=start,
        end=end,
        market_label=market,
        region=region,
        filter_id=filter_id,
        resolution=resolution,
        output_csv=p["prices"],
        output_report=p["price_quality_report"],
        output_json=p["price_quality_json"],
    )

    build_panel(
        feature_file=p["features"],
        price_file=p["prices"],
        risk_file=p["risk"],
        output_csv=p["panel"],
        output_report=p["panel_quality_report"],
        output_json=p["panel_quality_json"],
    )

    build_events(
        panel_file=p["panel"],
        output_csv=p["events"],
        output_report=p["events_report"],
        output_json=p["events_json"],
        high_q=high_q,
        low_q=low_q,
        ramp_q=ramp_q,
    )

    build_evaluation(
        input_file=p["events"],
        output_csv=p["evaluation"],
        output_report=p["evaluation_report"],
        output_json=p["evaluation_json"],
        confusion_csv=p["confusion"],
        event_summary_csv=p["event_summary"],
        signal_threshold=signal_threshold,
    )

    build_behavior(
        input_file=p["evaluation"],
        output_report=p["behavior_report"],
        output_json=p["behavior_json"],
        bucket_csv=p["bucket"],
        regime_csv=p["regime"],
        reason_csv=p["reason"],
        quantile_csv=p["quantiles"],
        top_csv=p["top"],
        top_n=top_n,
    )

    print(f"OK | price stack completed | {start} to {end}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--region", default="DE-LU")
    parser.add_argument("--filter-id", default="4169")
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--signal-threshold", type=float, default=60.0)
    parser.add_argument("--high-q", type=float, default=0.90)
    parser.add_argument("--low-q", type=float, default=0.10)
    parser.add_argument("--ramp-q", type=float, default=0.90)
    parser.add_argument("--top-n", type=int, default=30)
    args = parser.parse_args()

    run_month(
        start=args.start,
        end=args.end,
        market=args.market_label,
        region=args.region,
        filter_id=args.filter_id,
        resolution=args.resolution,
        signal_threshold=args.signal_threshold,
        high_q=args.high_q,
        low_q=args.low_q,
        ramp_q=args.ramp_q,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
