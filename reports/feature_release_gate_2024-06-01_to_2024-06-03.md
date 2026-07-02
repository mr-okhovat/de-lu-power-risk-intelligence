# Analytical Dataset Release Gate

- Feature dataset: `data/processed/hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv`
- Metadata file: `data/processed/hourly_features_DE-LU_2024-06-01_to_2024-06-03.metadata.json`
- Release status: `READY`
- Row count: `72`
- Expected hour count: `72`
- Invalid timestamps: `0`
- Duplicate timestamps: `0`
- Hourly continuity breaks: `0`
- Residual-gap tolerance MW: `1.0`
- Residual-gap max absolute MW: `0.0`
- Residual-gap pass: `True`

## Metadata Checks

- `metadata_file_exists`: `True`
- `metadata_is_valid_json_object`: `True`
- `feature_output_matches`: `True`
- `metadata_row_count_matches`: `True`
- `metadata_quality_status_pass`: `True`
- `feature_schema_version_matches`: `True`

## Blocking Reasons

- None

## Release Policy

Only datasets with `READY` status may feed downstream risk signals, dashboards, or reviewer-facing reports.
