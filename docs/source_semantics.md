# Source Semantics

## Purpose

This document locks the current interpretation status of each SMARD series used in the project.

A working endpoint is not enough. A series can only be used for analytics when its technical availability and business meaning are both controlled.

## Semantic Status Levels

- `endpoint_verified_semantics_locked`
- `endpoint_verified_semantics_provisional`
- `not_verified`
- `deprecated`

## Validation Status Levels

- `source_endpoint_and_staging_validated`
- `validated_by_residual_load_reconciliation`
- `not_yet_validated`

## Current SMARD Series

| Filter ID | Internal Name | Unit | Category | Semantic Status | Validation Status | Use in Project |
|---|---|---:|---|---|---|---|
| 410 | total_load | MW | consumption | endpoint_verified_semantics_locked | source_endpoint_and_staging_validated | Core load signal |
| 4359 | residual_load_official | MW | consumption | endpoint_verified_semantics_locked | source_endpoint_and_staging_validated | Official residual-load reference |
| 4067 | wind_onshore_validated | MW | generation | endpoint_verified_semantics_locked | validated_by_residual_load_reconciliation | Renewable component for staging and features |
| 4068 | solar_validated | MW | generation | endpoint_verified_semantics_locked | validated_by_residual_load_reconciliation | Renewable component for staging and features |
| 1225 | wind_offshore_validated | MW | generation | endpoint_verified_semantics_locked | validated_by_residual_load_reconciliation | Renewable component for staging and features |

## Validation Evidence

Phase 2B produced a hard-check report with:

- 72 staging rows.
- 72 expected hourly timestamps.
- 0 duplicate timestamps.
- 0 hourly continuity breaks.
- 0 missing values in required value columns.
- 0 range violations.
- residual-load reconciliation passed.
- max absolute residual reconciliation error: 0.0 MW.
- mean absolute residual reconciliation error: 0.0 MW.

The reconciliation equation was:

```text
derived_residual_load = total_load - wind_onshore_validated - solar_validated - wind_offshore_validated
```

This was compared against:

```text
residual_load_official
```

## DE vs DE-LU Label

The project uses:

- `smard_region: DE`
- `market_label: DE-LU`

This is intentional.

`smard_region` refers to the region code used in the SMARD endpoint.

`market_label` refers to the analytical market/bidding-zone label used by this project.

Reports must clearly state this distinction.

## Interpretation Control

The renewable component series are now allowed for final features because they reconcile exactly against the official residual-load series for the tested window.

This does not mean the project claims predictive power yet.

It only means the staging layer is coherent enough for feature engineering.
