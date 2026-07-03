# DE-LU hourly features — release-control implementation

I added a release-control gate to the existing DE-LU hourly feature pipeline,
then ran the same SMARD-derived sample through the repository workflow,
Databricks and Snowflake. The sample covers 1–3 June 2024: 72 hourly records
under feature schema `3A.1`.

| Environment | Work completed | Executed result |
|---|---|---|
| Local repository | Added `feature_release_gate.py` after feature engineering. The gate validates schema, timestamp parsing and continuity, analytical completeness, missing-data flags, residual-load reconciliation, share ranges, source labels and metadata alignment. | `READY`; 72 unique hourly timestamps; no continuity break; maximum absolute residual-gap error `0.0 MW`. |
| Databricks | Loaded the feature CSV and metadata into the Unity Catalog volume at `/Volumes/workspace/power_risk_poc/landing/`. Built the path `bronze_hourly_features` → `silver_hourly_features` → `silver_quality_check_results` → `gold_release_status`. | 31 quality checks; 0 failures; `READY`. |
| Snowflake | Loaded the same CSV through `RAW.STG_HOURLY_FEATURES` into `RAW.HOURLY_FEATURES_LANDING`. Built the typed control layer, persisted check-level evidence in `CONTROL.RELEASE_CHECK_RESULTS`, and exposed the decision through `MART.V_RELEASE_STATUS`. | 12 critical checks; 0 failures; `READY`. |

The local gate is also tested against failure cases: a missing ramp value, an
out-of-range share value and a metadata row-count mismatch. Each is expected
to return `BLOCKED`, so the release decision is not based only on a clean
reference run.

## Repository evidence

- Local gate: [implementation](../src/data_quality/feature_release_gate.py),
  [tests](../tests/test_feature_release_gate.py),
  [runner](../scripts/run_feature_release_gate.py), and
  [reference audit output](feature_release_gate_2024-06-01_to_2024-06-03.md).
- Databricks workflow: [Bronze landing](../notebooks/databricks/01_bronze_feature_landing.py),
  [Silver validation](../notebooks/databricks/02_silver_analytical_validation.py),
  and [Gold release status](../notebooks/databricks/03_gold_release_status.py).
- Snowflake workflow: [raw landing and load](../sql/snowflake/01_setup_and_load.sql)
  and [typed control, audit checks and release mart](../sql/snowflake/02_release_control.sql).

Implementation commits: `98794e9`, `50d4af3`, `0027e1e`.
