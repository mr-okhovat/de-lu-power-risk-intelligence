# Phase 6A — Pipeline Orchestration and Automation

## Scope

This phase turns the project from separately executed modules into a one-command reproducible pipeline.

## Created files

- config/pipeline_sample.yaml
- src/orchestration/pipeline_steps.py
- src/orchestration/run_all.py
- tests/test_pipeline_steps.py
- scripts/run_sample_pipeline.sh
- scripts/run_quality_gate.sh
- .github/workflows/ci.yml
- docs/automation_runbook.md

## Acceptance

- Tests pass.
- Dry-run pipeline works.
- Full sample pipeline works.
- Pipeline summary report is generated.
- GitHub Actions CI runs tests on push and pull request.
