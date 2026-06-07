from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


DASHBOARD_SCHEMA_VERSION = "3B.1"


MARKET_OVERVIEW_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "total_load_mw",
    "residual_load_official_mw",
    "wind_onshore_validated_mw",
    "wind_offshore_validated_mw",
    "solar_validated_mw",
    "wind_total_mw",
    "renewable_generation_mw",
    "renewable_share",
    "wind_share",
    "solar_share",
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
    "local_date",
    "local_hour",
    "local_weekday",
    "is_weekend",
    "feature_schema_version",
]


FEATURE_DICTIONARY_ROWS = [
    ("timestamp_utc", "datetime_utc", "Canonical UTC timestamp."),
    ("timestamp_local", "datetime_local", "Europe/Berlin local market timestamp."),
    ("market_label", "text", "Analytical market label used by the project."),
    ("smard_region", "text", "SMARD endpoint region used for source retrieval."),
    ("total_load_mw", "MW", "Total load from SMARD."),
    ("residual_load_official_mw", "MW", "Official residual load from SMARD."),
    ("wind_onshore_validated_mw", "MW", "Validated wind onshore residual-load component."),
    ("wind_offshore_validated_mw", "MW", "Validated wind offshore residual-load component."),
    ("solar_validated_mw", "MW", "Validated solar residual-load component."),
    ("wind_total_mw", "MW", "Wind onshore plus wind offshore."),
    ("renewable_generation_mw", "MW", "Wind total plus solar."),
    ("renewable_share", "ratio", "Renewable generation divided by total load."),
    ("wind_share", "ratio", "Wind total divided by total load."),
    ("solar_share", "ratio", "Solar generation divided by total load."),
    ("load_ramp_mw", "MW/h", "Current total load minus previous hour total load."),
    ("residual_load_ramp_mw", "MW/h", "Current residual load minus previous hour residual load."),
    ("renewable_generation_ramp_mw", "MW/h", "Current renewable generation minus previous hour renewable generation."),
    ("local_date", "date", "Europe/Berlin local date."),
    ("local_hour", "hour", "Europe/Berlin local hour."),
    ("local_weekday", "text", "Europe/Berlin local weekday name."),
    ("is_weekend", "boolean", "True if local timestamp falls on Saturday or Sunday."),
    ("feature_schema_version", "text", "Feature schema version."),
]


@dataclass(frozen=True)
class DashboardExportQualityResult:
    status: str
    row_count: int
    required_columns_missing: list[str]
    duplicate_timestamp_count: int
    missing_by_column: dict[str, int]
    notes: list[str]


def load_feature_frame(path: str | Path) -> pd.DataFrame:
    feature_path = Path(path)

    if not feature_path.exists():
        raise FileNotFoundError(f"Feature file not found: {feature_path}")

    df = pd.read_csv(feature_path)

    missing = [column for column in MARKET_OVERVIEW_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Feature file is missing dashboard export columns: {missing}")

    return df


def build_market_overview_export(features: pd.DataFrame) -> pd.DataFrame:
    export = features[MARKET_OVERVIEW_COLUMNS].copy()

    export["dashboard_schema_version"] = DASHBOARD_SCHEMA_VERSION

    return export


def build_feature_dictionary() -> pd.DataFrame:
    rows = [
        {
            "column_name": column_name,
            "unit_or_type": unit_or_type,
            "description": description,
            "dashboard_schema_version": DASHBOARD_SCHEMA_VERSION,
        }
        for column_name, unit_or_type, description in FEATURE_DICTIONARY_ROWS
    ]

    return pd.DataFrame(rows)


def validate_dashboard_export(export: pd.DataFrame) -> DashboardExportQualityResult:
    required_columns = MARKET_OVERVIEW_COLUMNS + ["dashboard_schema_version"]

    required_columns_missing = [
        column for column in required_columns if column not in export.columns
    ]

    duplicate_timestamp_count = (
        int(export["timestamp_utc"].duplicated().sum())
        if "timestamp_utc" in export.columns
        else 0
    )

    critical_columns = [
        "timestamp_utc",
        "market_label",
        "total_load_mw",
        "residual_load_official_mw",
        "renewable_generation_mw",
        "renewable_share",
    ]

    missing_by_column = {
        column: int(export[column].isna().sum())
        for column in critical_columns
        if column in export.columns
    }

    notes: list[str] = []

    if required_columns_missing:
        notes.append(f"Missing required dashboard columns: {required_columns_missing}")

    if duplicate_timestamp_count:
        notes.append(f"Duplicate timestamps found: {duplicate_timestamp_count}")

    if sum(missing_by_column.values()) > 0:
        notes.append("Missing values found in critical dashboard columns.")

    if not notes:
        notes.append("Dashboard export passed Phase 3B checks.")

    blocking_issue = (
        bool(required_columns_missing)
        or duplicate_timestamp_count > 0
        or sum(missing_by_column.values()) > 0
    )

    status = "STOP — NEEDS VERIFICATION" if blocking_issue else "PASS"

    return DashboardExportQualityResult(
        status=status,
        row_count=int(len(export)),
        required_columns_missing=required_columns_missing,
        duplicate_timestamp_count=duplicate_timestamp_count,
        missing_by_column=missing_by_column,
        notes=notes,
    )


def render_dashboard_export_report(
    result: DashboardExportQualityResult,
    *,
    feature_input: str | Path,
    market_overview_output: str | Path,
    dictionary_output: str | Path,
    sql_schema_output: str | Path,
) -> str:
    lines = [
        "# SQL / Power BI Export Quality Report — Phase 3B",
        "",
        f"- Feature input: `{feature_input}`",
        f"- Market overview output: `{market_overview_output}`",
        f"- Feature dictionary output: `{dictionary_output}`",
        f"- SQL schema output: `{sql_schema_output}`",
        f"- Status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Dashboard schema version: `{DASHBOARD_SCHEMA_VERSION}`",
        f"- Duplicate timestamps: `{result.duplicate_timestamp_count}`",
        "",
        "## Required Columns Missing",
        "",
    ]

    if result.required_columns_missing:
        for column in result.required_columns_missing:
            lines.append(f"- `{column}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Missing Values in Critical Columns", ""])

    for column, count in result.missing_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Notes", ""])

    for note in result.notes:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This phase creates SQL/Power BI-ready exports from the feature table. It does not create visual dashboards, risk scores, trading signals, or backtests.",
            "",
        ]
    )

    return "\n".join(lines)


def render_sql_schema() -> str:
    return """-- Phase 3B SQL schema contract
-- Table: power_market_features
-- Purpose: SQL/Power BI-ready feature table for DE-LU public-data analytics.
-- This schema is a contract, not a database migration yet.

CREATE TABLE IF NOT EXISTS power_market_features (
    timestamp_utc TIMESTAMP PRIMARY KEY,
    timestamp_local TIMESTAMP,
    market_label TEXT NOT NULL,
    smard_region TEXT NOT NULL,
    total_load_mw DOUBLE PRECISION,
    residual_load_official_mw DOUBLE PRECISION,
    wind_onshore_validated_mw DOUBLE PRECISION,
    wind_offshore_validated_mw DOUBLE PRECISION,
    solar_validated_mw DOUBLE PRECISION,
    wind_total_mw DOUBLE PRECISION,
    renewable_generation_mw DOUBLE PRECISION,
    renewable_share DOUBLE PRECISION,
    wind_share DOUBLE PRECISION,
    solar_share DOUBLE PRECISION,
    load_ramp_mw DOUBLE PRECISION,
    residual_load_ramp_mw DOUBLE PRECISION,
    renewable_generation_ramp_mw DOUBLE PRECISION,
    local_date DATE,
    local_hour INTEGER,
    local_weekday TEXT,
    is_weekend BOOLEAN,
    feature_schema_version TEXT,
    dashboard_schema_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_power_market_features_market_time
ON power_market_features (market_label, timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_power_market_features_local_date
ON power_market_features (local_date);
"""


def build_dashboard_exports(
    *,
    feature_input: str | Path,
    market_overview_output: str | Path,
    dictionary_output: str | Path,
    report_output: str | Path,
    sql_schema_output: str | Path,
    metadata_output: str | Path | None = None,
) -> pd.DataFrame:
    features = load_feature_frame(feature_input)

    market_overview = build_market_overview_export(features)
    feature_dictionary = build_feature_dictionary()

    quality_result = validate_dashboard_export(market_overview)

    market_overview_output = Path(market_overview_output)
    dictionary_output = Path(dictionary_output)
    report_output = Path(report_output)
    sql_schema_output = Path(sql_schema_output)

    market_overview_output.parent.mkdir(parents=True, exist_ok=True)
    dictionary_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    sql_schema_output.parent.mkdir(parents=True, exist_ok=True)

    market_overview.to_csv(market_overview_output, index=False)
    feature_dictionary.to_csv(dictionary_output, index=False)

    sql_schema_output.write_text(render_sql_schema(), encoding="utf-8")

    report_output.write_text(
        render_dashboard_export_report(
            quality_result,
            feature_input=feature_input,
            market_overview_output=market_overview_output,
            dictionary_output=dictionary_output,
            sql_schema_output=sql_schema_output,
        ),
        encoding="utf-8",
    )

    if metadata_output is None:
        metadata_output = market_overview_output.with_suffix(".metadata.json")

    metadata_output = Path(metadata_output)

    metadata_payload = {
        "stage": "dashboard_exports",
        "dashboard_schema_version": DASHBOARD_SCHEMA_VERSION,
        "feature_input": str(Path(feature_input).as_posix()),
        "market_overview_output": str(market_overview_output.as_posix()),
        "feature_dictionary_output": str(dictionary_output.as_posix()),
        "sql_schema_output": str(sql_schema_output.as_posix()),
        "quality_report": str(report_output.as_posix()),
        "quality_result": asdict(quality_result),
        "notes": [
            "No Power BI .pbix file is generated in Phase 3B.",
            "No risk score is generated in Phase 3B.",
            "No backtest is generated in Phase 3B.",
        ],
    }

    metadata_output.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | dashboard rows={len(market_overview)} | output={market_overview_output}")
    print(f"OK | dashboard export status={quality_result.status} | report={report_output}")

    if quality_result.status == "STOP — NEEDS VERIFICATION":
        raise SystemExit(1)

    return market_overview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SQL/Power BI-ready dashboard exports.")

    parser.add_argument("--feature-input", required=True)
    parser.add_argument("--market-overview-output", required=True)
    parser.add_argument("--dictionary-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--sql-schema-output", required=True)
    parser.add_argument("--metadata-output", default=None)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_dashboard_exports(
        feature_input=args.feature_input,
        market_overview_output=args.market_overview_output,
        dictionary_output=args.dictionary_output,
        report_output=args.report_output,
        sql_schema_output=args.sql_schema_output,
        metadata_output=args.metadata_output,
    )


if __name__ == "__main__":
    main()
