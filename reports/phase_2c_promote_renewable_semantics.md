# Phase 2C — Promote Renewable Semantics with Evidence

## Scope

This phase promotes the renewable component series from candidate/provisional status to validated feature-eligible status.

## Evidence Used

Phase 2B residual-load reconciliation:

```text
derived_residual_load = total_load - wind_onshore_validated - solar_validated - wind_offshore_validated
```

compared with:

```text
residual_load_official
```

Result:

- Max absolute error MW: 0.0
- Mean absolute error MW: 0.0
- Pass: True

## Created/modified files

- src/config/series_registry.yaml
- src/config/load_series_registry.py
- tests/test_series_registry.py
- docs/source_semantics.md
- docs/project_control.md

## Control

This phase does not claim predictive power or trading usefulness.

It only confirms that the staging series are coherent enough for feature engineering.
