#!/usr/bin/env bash
set -euo pipefail

python -m pytest
python -m src.orchestration.run_all --config config/pipeline_sample.yaml --dry-run
