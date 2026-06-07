#!/usr/bin/env bash
set -euo pipefail

python -m src.core.project_orchestrator   --output-report reports/project_checkpoint_run.md   --output-json reports/project_checkpoint_run.json
