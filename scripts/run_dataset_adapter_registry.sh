#!/usr/bin/env bash
set -euo pipefail

python -m src.core.adapter_registry   --registry src/config/dataset_adapter_registry.yaml   --report-output reports/dataset_adapter_registry_run.md   --json-output reports/dataset_adapter_registry_run.json
