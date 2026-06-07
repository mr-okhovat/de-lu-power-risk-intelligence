# Source Semantics

## Purpose

This document locks the current interpretation status of each SMARD series used in the project.

A working endpoint is not enough. A series can only be used for analytics when its technical availability and business meaning are both controlled.

## Current Principle

Each configured series has one of the following semantic statuses:

- `endpoint_verified_semantics_locked`
- `endpoint_verified_semantics_provisional`
- `not_verified`
- `deprecated`

A series marked as `endpoint_verified_semantics_provisional` can be downloaded and stored, but it must not be used for final claims without a limitation note.

## Current SMARD Series

| Filter ID | Internal Name | Unit | Category | Status | Use in Project |
|---|---|---:|---|---|---|
| 410 | Total Load | MW | consumption | endpoint_verified_semantics_locked | Core load signal |
| 4359 | Residual Load | MW | consumption | endpoint_verified_semantics_locked | Validation reference and core stress signal |
| 4067 | Wind Candidate | MW | generation | endpoint_verified_semantics_provisional | Candidate renewable component |
| 4068 | Solar Candidate | MW | generation | endpoint_verified_semantics_provisional | Candidate renewable component |
| 1225 | Wind Offshore Candidate | MW | generation | endpoint_verified_semantics_provisional | Candidate renewable component |

## Why Some Series Are Provisional

Phase 1B verified that the endpoints exist and return chunk timestamps. That proves technical availability. It does not fully prove business semantics.

Before final feature engineering, provisional series must be checked against:

1. SMARD UI labels.
2. Download metadata where available.
3. Plausible value ranges.
4. Cross-checks against residual load.
5. Documentation notes in this repository.

## DE vs DE-LU Label

The project uses:

- `smard_region: DE`
- `market_label: DE-LU`

This is intentional.

`smard_region` refers to the region code used in the SMARD endpoint.

`market_label` refers to the analytical market/bidding-zone label used by this project.

Any report must clearly state this distinction to avoid overstating what the source directly provides.

## Analytics Rule

Do not build final market features from provisional series unless the report includes an explicit limitation.

## Reviewer Note

A professional reviewer should be able to trace each feature back to:

1. Source.
2. Filter ID.
3. Unit.
4. Semantic status.
5. Raw file.
6. Transformation logic.
