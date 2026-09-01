# Operational Risk Diagnostic Report

- Input: `data/processed/operational_risk_DE-LU_2024-08-01_to_2024-08-31.csv`
- Status: `PASS`
- Rows: `744`
- Schema version: `1.0`

## Operational Readout

- Critical rows: `0`
- Immediate-attention rows: `0`
- Multi-driver rows: `87`
- Zero-driver rows: `538`
- Duplicate timestamps: `0`

## Coverage

- Operational states: `['CONSTRAINED', 'HEIGHTENED', 'STABLE']`
- Attention levels: `['ACTIVE', 'MONITOR', 'ROUTINE']`
- Dominant drivers: `['HIGH_LOAD_RAMP', 'HIGH_RENEWABLE_GENERATION_RAMP', 'HIGH_RESIDUAL_LOAD', 'HIGH_RESIDUAL_LOAD_RAMP', 'LOW_RENEWABLE_SHARE', 'NONE']`

## Output Tables

- State distribution: `dashboards/operational_state_distribution_DE-LU_2024-08-01_to_2024-08-31.csv`
- Attention distribution: `dashboards/operational_attention_distribution_DE-LU_2024-08-01_to_2024-08-31.csv`
- Dominant-driver summary: `dashboards/operational_dominant_driver_DE-LU_2024-08-01_to_2024-08-31.csv`
- Driver-count distribution: `dashboards/operational_driver_count_DE-LU_2024-08-01_to_2024-08-31.csv`

## Notes

- No CRITICAL operational states were observed in this window.

## Interpretation Boundary

This layer translates existing rule-based risk signals into operational categories and diagnostic summaries.

Recommended actions are controlled decision-support labels. They do not represent automated trading instructions, dispatch commands, or validated financial recommendations.
