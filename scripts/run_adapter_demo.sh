#!/usr/bin/env bash
set -euo pipefail

python -m src.core.dataset_adapters   --adapter src/config/dataset_adapters/signal_price_evaluation_identity.yaml   --input data/processed/signal_price_evaluation_DE-LU_2024-06-01_to_2024-06-30.csv   --output data/adapted/signal_price_evaluation_DE-LU_2024-06_adapted.csv   --report-output reports/adapter_signal_price_evaluation_2024-06.md   --json-output reports/adapter_signal_price_evaluation_2024-06.json

python -m src.core.data_contracts   --contract src/config/dataset_contracts/signal_price_evaluation.yaml   --input data/adapted/signal_price_evaluation_DE-LU_2024-06_adapted.csv   --report-output reports/contract_adapted_signal_price_evaluation_2024-06.md   --json-output reports/contract_adapted_signal_price_evaluation_2024-06.json
