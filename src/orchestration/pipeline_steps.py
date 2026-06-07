from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    run_label: str
    start: str
    end: str
    market_label: str
    smard_region: str
    resolution: str
    filters: list[str]
    min_history: int
    signal_positive_threshold: float
    high_quantile: float
    low_quantile: float
    run_tests_first: bool
    run_tests_last: bool


@dataclass(frozen=True)
class PipelineStep:
    name: str
    command: list[str]
    description: str


def load_pipeline_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_path}")

    payload: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw = payload["pipeline"]

    return PipelineConfig(
        name=str(raw["name"]),
        run_label=str(raw["run_label"]),
        start=str(raw["start"]),
        end=str(raw["end"]),
        market_label=str(raw["market_label"]),
        smard_region=str(raw["smard_region"]),
        resolution=str(raw["resolution"]),
        filters=[str(item) for item in raw["filters"]],
        min_history=int(raw["min_history"]),
        signal_positive_threshold=float(raw["signal_positive_threshold"]),
        high_quantile=float(raw["high_quantile"]),
        low_quantile=float(raw["low_quantile"]),
        run_tests_first=bool(raw.get("run_tests_first", True)),
        run_tests_last=bool(raw.get("run_tests_last", True)),
    )


def output_paths(config: PipelineConfig) -> dict[str, str]:
    suffix = f"{config.market_label}_{config.start}_to_{config.end}"
    report_suffix = f"{config.start}_to_{config.end}"

    return {
        "staging": f"data/staging/clean_hourly_{suffix}.csv",
        "staging_hard_report": f"reports/staging_hard_checks_{report_suffix}.md",
        "staging_hard_json": f"reports/staging_hard_checks_{report_suffix}.json",
        "features": f"data/processed/hourly_features_{suffix}.csv",
        "dashboard_market_overview": f"dashboards/market_overview_{suffix}.csv",
        "dashboard_dictionary": f"dashboards/feature_dictionary_{suffix}.csv",
        "dashboard_report": f"reports/dashboard_export_quality_{report_suffix}.md",
        "sql_schema": "sql/schema_power_market_features.sql",
        "risk_signals": f"data/processed/risk_signals_{suffix}.csv",
        "risk_diagnostics_report": f"reports/risk_diagnostics_{report_suffix}.md",
        "risk_diagnostics_json": f"reports/risk_diagnostics_{report_suffix}.json",
        "risk_regime_distribution": f"dashboards/risk_regime_distribution_{suffix}.csv",
        "risk_reason_code_summary": f"dashboards/risk_reason_code_summary_{suffix}.csv",
        "top_risk_hours": f"dashboards/top_risk_hours_{suffix}.csv",
        "event_labels": f"data/processed/event_labels_{suffix}.csv",
        "event_report": f"reports/event_study_skeleton_{report_suffix}.md",
        "event_json": f"reports/event_study_skeleton_{report_suffix}.json",
        "signal_event_evaluation": f"data/processed/signal_event_evaluation_{suffix}.csv",
        "signal_event_confusion": f"dashboards/signal_event_confusion_{suffix}.csv",
        "signal_event_report": f"reports/signal_event_evaluation_{report_suffix}.md",
        "signal_event_json": f"reports/signal_event_evaluation_{report_suffix}.json",
        "run_summary": f"reports/pipeline_run_summary_{report_suffix}.md",
        "run_summary_json": f"reports/pipeline_run_summary_{report_suffix}.json",
    }


def base_pipeline_args(config: PipelineConfig) -> list[str]:
    return [
        "--start", config.start,
        "--end", config.end,
        "--market-label", config.market_label,
        "--smard-region", config.smard_region,
    ]


def build_pipeline_steps(config: PipelineConfig) -> list[PipelineStep]:
    py = sys.executable
    paths = output_paths(config)

    steps: list[PipelineStep] = []

    if config.run_tests_first:
        steps.append(
            PipelineStep(
                name="tests_start",
                command=[py, "-m", "pytest"],
                description="Run test suite before data pipeline execution.",
            )
        )

    steps.extend(
        [
            PipelineStep(
                name="smard_filter_discovery",
                command=[
                    py,
                    "-m",
                    "src.data_ingestion.smard_filter_discovery",
                    "--smard-region",
                    config.smard_region,
                    "--resolution",
                    config.resolution,
                ],
                description="Verify configured SMARD filter endpoints.",
            ),
            PipelineStep(
                name="smard_ingestion",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "smard-ingest",
                    "--resolution",
                    config.resolution,
                    "--filters",
                    *config.filters,
                ],
                description="Download raw SMARD JSON data and metadata.",
            ),
            PipelineStep(
                name="build_staging",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-staging",
                ],
                description="Build clean hourly staging table.",
            ),
            PipelineStep(
                name="staging_hard_checks",
                command=[
                    py,
                    "-m",
                    "src.data_quality.staging_hard_checks",
                    "--staging-file",
                    paths["staging"],
                    "--report-output",
                    paths["staging_hard_report"],
                    "--json-output",
                    paths["staging_hard_json"],
                ],
                description="Run hard validation checks on staging data.",
            ),
            PipelineStep(
                name="build_features",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-features",
                ],
                description="Build market feature table.",
            ),
            PipelineStep(
                name="build_dashboard_exports",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-dashboard-exports",
                ],
                description="Build SQL/Power BI-ready exports.",
            ),
            PipelineStep(
                name="build_risk_signals",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-risk-signals",
                    "--min-history",
                    str(config.min_history),
                ],
                description="Build rule-based risk signal table.",
            ),
            PipelineStep(
                name="build_risk_diagnostics",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-risk-diagnostics",
                ],
                description="Build risk signal diagnostic outputs.",
            ),
            PipelineStep(
                name="build_event_study_skeleton",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-event-study-skeleton",
                    "--high-quantile",
                    str(config.high_quantile),
                    "--low-quantile",
                    str(config.low_quantile),
                ],
                description="Build ex-post event labels.",
            ),
            PipelineStep(
                name="build_signal_event_evaluation",
                command=[
                    py,
                    "run_pipeline.py",
                    *base_pipeline_args(config),
                    "--phase",
                    "build-signal-event-evaluation",
                    "--signal-positive-threshold",
                    str(config.signal_positive_threshold),
                ],
                description="Compare risk signals with event labels.",
            ),
        ]
    )

    if config.run_tests_last:
        steps.append(
            PipelineStep(
                name="tests_end",
                command=[py, "-m", "pytest"],
                description="Run test suite after full pipeline execution.",
            )
        )

    return steps
