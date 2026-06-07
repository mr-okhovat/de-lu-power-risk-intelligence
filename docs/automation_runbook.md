# Automation Runbook

## Purpose

This document explains how to reproduce the current DE-LU Power Risk Intelligence pipeline.

## One-Command Sample Run

From the repository root:

```bash
bash scripts/run_sample_pipeline.sh
```

This executes:

1. tests
2. SMARD filter discovery
3. SMARD ingestion
4. staging build
5. staging hard checks
6. feature engineering
7. SQL/Power BI exports
8. risk signal generation
9. risk diagnostics
10. event labels
11. signal-vs-event evaluation
12. final tests

## Dry Run

```bash
python -m src.orchestration.run_all --config config/pipeline_sample.yaml --dry-run
```

## Quality Gate

```bash
bash scripts/run_quality_gate.sh
```

## Configuration

Sample configuration:

```text
config/pipeline_sample.yaml
```

Change this file to adjust:

- start date
- end date
- market label
- SMARD region
- filters
- minimum history
- signal-positive threshold

## Current Boundary

The automated pipeline is not a trading bot.

It does not make P&L claims.

It reproduces a public-data analytics workflow for DE-LU power market risk intelligence.
