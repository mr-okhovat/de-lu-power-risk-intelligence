# Dataset adapters

Dataset adapters map external or differently shaped input files into canonical project schemas.

The adapter layer is separate from the contract layer:

1. adapter: maps source columns to canonical columns
2. contract: validates the canonical output
3. analytics: uses only validated canonical datasets

This prevents the pipeline from accepting arbitrary data just because the file loads.

Current adapter examples:

- signal_price_evaluation_identity
- example_external_signal_price

The identity adapter is mainly a reference implementation. The external example shows how a differently named dataset can be mapped into the same canonical schema.
