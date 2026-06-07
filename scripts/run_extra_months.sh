#!/usr/bin/env bash
set -euo pipefail

python -m src.orchestration.run_all --config config/pipeline_may_2024.yaml
python -m src.orchestration.run_all --config config/pipeline_july_2024.yaml
python -m src.orchestration.run_all --config config/pipeline_august_2024.yaml
