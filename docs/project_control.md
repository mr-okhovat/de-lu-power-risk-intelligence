# Project Control

## Current Build Strategy

This project is built through gated phases.

Each phase must produce:

1. Limited scope.
2. Controlled file changes.
3. Testable output.
4. Acceptance criteria.
5. Commit message.
6. Clear next step.

## Phase Status

| Phase | Name | Status |
|---|---|---|
| Phase 0 | Project Control and Design Lock | PASS |
| Phase 1A | SMARD Foundation Ingestion | PASS |
| Phase 1B | SMARD Filter Discovery and Safe Multi-Filter Ingestion | PASS |
| Phase 1C | Source Semantics Lock and Project Control | IN PROGRESS |
| Phase 2A | Clean Hourly Staging Table | NOT STARTED |

## Phase Gate Definitions

### PASS

All acceptance criteria are met.

### PASS WITH LIMITATION

The technical step works, but one or more limitations must be documented before the output is used for final claims.

### STOP — NEEDS VERIFICATION

The project must not proceed until the issue is resolved.

## Current Risk Register

| Risk | Severity | Control |
|---|---:|---|
| Generic AI-generated project appearance | High | Maintain real data, tests, source registry, audit docs |
| Mislabeling SMARD series | High | Use semantic status and series registry |
| Raw data bloat in GitHub | Medium | Keep generated raw data ignored |
| Premature dashboarding | Medium | Build dashboard layer only after staging/features |
| Weak reviewer credibility | High | Maintain methodology, limitations, reproducibility |
| Look-ahead bias | High | Enforce no-lookahead policy before features/backtesting |

## Next Required Gate

Before Phase 2A, the project must have:

- source semantics document
- architecture decisions
- project control document
- reviewer notes
- series registry
- registry tests
