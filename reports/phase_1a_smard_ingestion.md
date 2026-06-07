# Phase 1A — SMARD Foundation Ingestion

## Scope

This phase adds the first real data ingestion layer for SMARD.

## Created files

- src/config/sources.yaml
- src/data_ingestion/smard_client.py
- run_pipeline.py
- tests/test_smard_client.py

## Smoke test

```bash
python run_pipeline.py --start 2024-06-01 --end 2024-06-03 --market-label DE-LU --smard-region DE --phase smard-ingest --filters 410
```

## Expected output

Raw files:

```text
data/raw/smard/410/*.json
data/raw/smard/410/*.metadata.json
data/raw/smard/410/manifest_*.json
```

Log file:

```text
logs/pipeline.log
```

## Acceptance

- pytest passes.
- At least one raw SMARD JSON file is created.
- At least one metadata JSON file is created.
- Manifest file is created.
- Metadata includes source, attribution, license note, unit, resolution, market label, SMARD region, timestamp policy, and SHA256 hash.
