#!/usr/bin/env bash
set -euo pipefail

python -m src.core.data_contracts   --contract src/config/dataset_contracts/signal_price_evaluation.yaml   --input data/processed/signal_price_evaluation_DE-LU_2024-06-01_to_2024-06-30.csv   --report-output reports/contract_signal_price_evaluation_2024-06.md   --json-output reports/contract_signal_price_evaluation_2024-06.json

python -m src.core.data_contracts   --contract src/config/dataset_contracts/cross_month_price_risk.yaml   --input dashboards/cross_month_price_risk_DE-LU_2024-05_to_2024-08.csv   --report-output reports/contract_cross_month_price_risk_2024-05_to_2024-08.md   --json-output reports/contract_cross_month_price_risk_2024-05_to_2024-08.json

python -m src.core.data_contracts   --contract src/config/dataset_contracts/lead_time_aggregate.yaml   --input dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv   --report-output reports/contract_lead_time_aggregate_2024-05_to_2024-08.md   --json-output reports/contract_lead_time_aggregate_2024-05_to_2024-08.json
