#!/usr/bin/env bash
set -euo pipefail

python -m src.core.run_catalog \
  --availability-csv dashboards/data_availability_index.csv \
  --cross-month-csv dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv \
  --lead-monthly-csv dashboards/lead_time_monthly_DE-LU_2024-05_to_2024-08.csv \
  --output-csv dashboards/market_month_run_catalog.csv \
  --output-report reports/market_month_run_catalog.md \
  --output-json reports/market_month_run_catalog.json
