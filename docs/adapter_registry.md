# Adapter registry

The adapter registry defines which datasets can enter the canonical analytics flow.

Each registry entry links:

- source input file
- adapter mapping
- dataset contract
- adapted output path
- adapter report
- contract report

Flow:

    raw/external dataset
    -> adapter
    -> canonical dataset
    -> contract validation
    -> analytics layer

This is the control layer that prevents arbitrary files from entering the analysis without mapping and validation.
