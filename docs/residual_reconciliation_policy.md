# Residual Reconciliation Policy

## Purpose

This policy controls persistent endpoint-level differences between the
source-published residual-load series and a residual load recomputed from total
load, onshore wind, solar and offshore wind.

## Signed-error convention

`recomputed_residual_mw - residual_load_official_mw`

## Control rule

A run passes only when every material reconciliation deviation above the
registry materiality threshold exactly matches the documented timestamp and
signed-error profile within the configured match tolerance.

A new timestamp, a missing documented exception, a changed signed error or a
duplicate observed material exception remains a blocking failure.

## Current documented profile

- Policy ID: `de-lu-smard-residual-reconciliation-2021-01`
- Market: `DE-LU`
- Source region: `DE`
- Materiality threshold: `0.1 MW`
- Documented exceptions: `70`
- Local window: 4–6 January 2021 Europe/Berlin

## Scope

The raw source-published residual-load field remains the primary field.
The recomputed residual load and residual gap remain audit/control fields.

The policy does not relax data quality thresholds, alter source values or make
a claim of globally exact reconciliation.

## Evidence

- Exception profile: `reports/residual_reconciliation_exceptions_2020_2024.csv`
- Fresh endpoint recheck:
  `reports/fresh_smard_recheck_2021_01_04_to_06.csv`
- Full-panel sensitivity:
  `reports/residual_input_sensitivity_2020_2024.json`
- Registry:
  `src/config/residual_reconciliation_exceptions.yaml`
