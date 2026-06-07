from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.data_ingestion.smard_client import SmardClient, load_smard_settings
from src.staging.build_hourly import build_staging_hourly
from src.features.market_features import build_market_features
from src.reporting.dashboard_exports import build_dashboard_exports
from src.signals.risk_engine import build_risk_signal_table
from src.reporting.risk_diagnostics import build_risk_diagnostics


def setup_logging() -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/pipeline.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DE-LU Power Risk Intelligence pipeline entrypoint."
    )

    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--smard-region", default="DE")
    parser.add_argument("--phase", default="smard-ingest", choices=["smard-ingest", "build-staging", "build-features", "build-dashboard-exports", "build-risk-signals", "build-risk-diagnostics"])
    parser.add_argument("--filters", nargs="+", default=["410"])
    parser.add_argument("--resolution", default="hour")
    parser.add_argument("--config", default="src/config/sources.yaml")
    parser.add_argument("--staging-output", default=None)
    parser.add_argument("--quality-report-output", default=None)
    parser.add_argument("--registry", default="src/config/series_registry.yaml")
    parser.add_argument("--staging-file", default=None)
    parser.add_argument("--features-output", default=None)
    parser.add_argument("--feature-report-output", default=None)
    parser.add_argument("--market-overview-output", default=None)
    parser.add_argument("--dictionary-output", default=None)
    parser.add_argument("--dashboard-report-output", default=None)
    parser.add_argument("--sql-schema-output", default=None)
    parser.add_argument("--risk-output", default=None)
    parser.add_argument("--risk-report-output", default=None)
    parser.add_argument("--min-history", type=int, default=24)
    parser.add_argument("--regime-distribution-output", default=None)
    parser.add_argument("--reason-code-summary-output", default=None)
    parser.add_argument("--top-risk-hours-output", default=None)
    parser.add_argument("--risk-diagnostic-report-output", default=None)
    parser.add_argument("--risk-diagnostic-json-output", default=None)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue ingestion when one configured filter fails.",
    )

    return parser.parse_args()


def run_smard_ingestion(args: argparse.Namespace) -> None:
    settings = load_smard_settings(args.config)
    client = SmardClient(settings)

    succeeded: list[str] = []
    failed: list[str] = []

    for filter_id in args.filters:
        try:
            manifest = client.download_filter(
                filter_id=str(filter_id),
                start=args.start,
                end=args.end,
                market_label=args.market_label,
                smard_region=args.smard_region,
                resolution=args.resolution,
            )

            succeeded.append(str(filter_id))

            print(
                f"OK | SMARD filter={filter_id} | raw_files={len(manifest['files'])} | "
                f"run_id={manifest['run_id']}"
            )

        except Exception as exc:
            failed.append(str(filter_id))
            logging.exception("SMARD ingestion failed for filter=%s", filter_id)

            if not args.continue_on_error:
                raise

            print(f"FAIL | SMARD filter={filter_id} | error={exc}")

    print(f"SUMMARY | succeeded={succeeded} | failed={failed}")

    if failed and not succeeded:
        raise SystemExit(1)


def main() -> None:
    setup_logging()
    args = parse_args()

    if args.phase == "smard-ingest":
        run_smard_ingestion(args)
        return

    if args.phase == "build-staging":
        build_staging_hourly(
            start=args.start,
            end=args.end,
            market_label=args.market_label,
            smard_region=args.smard_region,
            resolution=args.resolution,
            output_path=args.staging_output,
            quality_report_path=args.quality_report_output,
            registry_path=args.registry,
        )
        return

    if args.phase == "build-features":
        staging_file = args.staging_file or (
            f"data/staging/clean_hourly_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        features_output = args.features_output or (
            f"data/processed/hourly_features_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        feature_report_output = args.feature_report_output or (
            f"reports/feature_quality_{args.start}_to_{args.end}.md"
        )

        build_market_features(
            staging_path=staging_file,
            output_path=features_output,
            report_path=feature_report_output,
        )
        return

    if args.phase == "build-dashboard-exports":
        feature_input = args.features_output or (
            f"data/processed/hourly_features_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        market_overview_output = args.market_overview_output or (
            f"dashboards/market_overview_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        dictionary_output = args.dictionary_output or (
            f"dashboards/feature_dictionary_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        dashboard_report_output = args.dashboard_report_output or (
            f"reports/dashboard_export_quality_{args.start}_to_{args.end}.md"
        )

        sql_schema_output = args.sql_schema_output or (
            "sql/schema_power_market_features.sql"
        )

        build_dashboard_exports(
            feature_input=feature_input,
            market_overview_output=market_overview_output,
            dictionary_output=dictionary_output,
            report_output=dashboard_report_output,
            sql_schema_output=sql_schema_output,
        )
        return

    if args.phase == "build-risk-signals":
        feature_input = args.features_output or (
            f"data/processed/hourly_features_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        risk_output = args.risk_output or (
            f"data/processed/risk_signals_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        risk_report_output = args.risk_report_output or (
            f"reports/risk_signal_quality_{args.start}_to_{args.end}.md"
        )

        build_risk_signal_table(
            feature_input=feature_input,
            signal_output=risk_output,
            report_output=risk_report_output,
            min_history=args.min_history,
        )
        return

    if args.phase == "build-risk-diagnostics":
        risk_signal_input = args.risk_output or (
            f"data/processed/risk_signals_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        regime_distribution_output = args.regime_distribution_output or (
            f"dashboards/risk_regime_distribution_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        reason_code_summary_output = args.reason_code_summary_output or (
            f"dashboards/risk_reason_code_summary_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        top_risk_hours_output = args.top_risk_hours_output or (
            f"dashboards/top_risk_hours_{args.market_label}_{args.start}_to_{args.end}.csv"
        )

        risk_diagnostic_report_output = args.risk_diagnostic_report_output or (
            f"reports/risk_diagnostics_{args.start}_to_{args.end}.md"
        )

        risk_diagnostic_json_output = args.risk_diagnostic_json_output or (
            f"reports/risk_diagnostics_{args.start}_to_{args.end}.json"
        )

        build_risk_diagnostics(
            risk_signal_input=risk_signal_input,
            regime_distribution_output=regime_distribution_output,
            reason_code_summary_output=reason_code_summary_output,
            top_risk_hours_output=top_risk_hours_output,
            report_output=risk_diagnostic_report_output,
            json_output=risk_diagnostic_json_output,
            top_n=args.top_n,
        )
        return

    raise ValueError(f"Unsupported phase: {args.phase}")


if __name__ == "__main__":
    main()
