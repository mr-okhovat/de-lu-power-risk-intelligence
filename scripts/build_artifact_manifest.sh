#!/usr/bin/env bash
set -euo pipefail

python -m src.core.artifact_manifest \
  --output-csv dashboards/project_artifact_manifest.csv \
  --output-report reports/project_artifact_manifest.md \
  --output-json reports/project_artifact_manifest.json
