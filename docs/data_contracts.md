# Dataset contracts

This layer defines schema and quality contracts for datasets before they enter analysis.

A dataset should not be trusted only because it has the right filename.

Current checks:

- required columns
- primary-key duplicates
- null handling
- dtype checks
- numeric ranges
- allowed values

This is the first step toward accepting new datasets through adapters instead of hardcoded assumptions.
