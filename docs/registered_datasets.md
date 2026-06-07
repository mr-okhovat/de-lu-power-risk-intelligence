# Registered datasets

The adapter registry now includes the core monthly signal-price evaluation datasets:

- May 2024
- June 2024
- July 2024
- August 2024

Each dataset follows the same intake path:

    source CSV
    -> signal_price_evaluation_identity adapter
    -> canonical adapted CSV
    -> signal_price_evaluation contract
    -> registry report

This makes the monthly evaluation datasets part of a managed intake layer instead of loose project outputs.
