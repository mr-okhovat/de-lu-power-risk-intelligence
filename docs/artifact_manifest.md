# Artifact manifest

The artifact manifest tracks the files that define the current project checkpoint.

It records:

- artifact category
- file path
- required flag
- existence
- size
- SHA-256 hash

This helps keep the project reviewable as the repo grows.

The manifest is not a market validation layer. It is a reproducibility and checkpoint-control layer.
