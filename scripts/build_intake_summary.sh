#!/usr/bin/env bash
set -euo pipefail

python -m src.core.intake_summary \
  --registry src/config/dataset_adapter_registry.yaml \
  --registry-run-json reports/dataset_adapter_registry_run.json \
  --summary-csv dashboards/dataset_intake_summary.csv \
  --output-report reports/dataset_intake_summary.md \
  --output-json reports/dataset_intake_summary.json
