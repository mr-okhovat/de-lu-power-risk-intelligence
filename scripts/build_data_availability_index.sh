#!/usr/bin/env bash
set -euo pipefail

python -m src.core.data_availability_index \
  --registry src/config/dataset_adapter_registry.yaml \
  --intake-summary dashboards/dataset_intake_summary.csv \
  --processed-dir data/processed \
  --output-csv dashboards/data_availability_index.csv \
  --output-report reports/data_availability_index.md \
  --output-json reports/data_availability_index.json
