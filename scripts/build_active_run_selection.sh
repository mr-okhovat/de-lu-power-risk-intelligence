#!/usr/bin/env bash
set -euo pipefail

python -m src.core.run_selector \
  --catalog-csv dashboards/market_month_run_catalog.csv \
  --output-csv dashboards/active_run_selection.csv \
  --output-report reports/active_run_selection.md \
  --output-json reports/active_run_selection.json
