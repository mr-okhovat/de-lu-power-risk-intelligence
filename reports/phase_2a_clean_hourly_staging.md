# Phase 2A — Clean Hourly Staging Table

## Scope

This phase builds the first clean hourly staging table from raw SMARD JSON files.

## Created/modified files

- src/staging/build_hourly.py
- src/data_quality/staging_validators.py
- tests/test_build_hourly.py
- tests/test_staging_validators.py
- run_pipeline.py

## Key Control

The staging table may include provisional semantic series, but final features cannot use provisional series for final claims until they are validated.

## Commands

```bash
python -m pytest
python run_pipeline.py --start 2024-06-01 --end 2024-06-03 --market-label DE-LU --smard-region DE --phase build-staging
cat reports/data_quality_2024-06-01_to_2024-06-03.md
```

## Acceptance

- Tests pass.
- Staging CSV is created.
- Metadata JSON is created.
- Data quality report is created.
- Report clearly marks limitations caused by provisional semantic columns.
