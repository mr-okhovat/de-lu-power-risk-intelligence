# Phase 3B — SQL / Power BI Ready Feature Export Contract

## Scope

This phase creates dashboard-ready exports and a SQL schema contract from the Phase 3A feature table.

## Created/modified files

- src/reporting/dashboard_exports.py
- tests/test_dashboard_exports.py
- run_pipeline.py
- docs/sql_powerbi_export_contract.md
- sql/schema_power_market_features.sql
- dashboards/market_overview_*.csv
- dashboards/feature_dictionary_*.csv
- reports/dashboard_export_quality_*.md

## Acceptance

- Tests pass.
- Market overview CSV is created.
- Feature dictionary CSV is created.
- SQL schema file is created.
- Dashboard export quality report is PASS.
- No risk scoring or backtesting is added in this phase.
