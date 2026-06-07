# Phase 1C — Source Semantics Lock and Project Control

## Scope

This phase adds source semantics, architecture decisions, reviewer notes, and a machine-readable series registry.

The goal is to prevent the project from becoming a generic AI-generated data project.

## Created files

- docs/source_semantics.md
- docs/architecture_decisions.md
- docs/project_control.md
- docs/reviewer_notes.md
- src/config/series_registry.yaml
- src/config/load_series_registry.py
- tests/test_series_registry.py

## Key Principle

Endpoint availability is not the same as business semantic certainty.

## Current Gate

- Total Load and Residual Load are allowed for final features.
- Candidate renewable generation series are allowed for staging.
- Candidate renewable generation series are not yet allowed for final feature claims.

## Acceptance

- Registry loads successfully.
- Filter IDs are unique.
- Provisional series cannot be used for final feature claims.
- Final feature series must have locked semantics.
- Tests pass.
