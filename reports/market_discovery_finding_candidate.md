# DE-LU Market Discovery Finding Candidate

## Candidate statement

Within the 2020–2024 DE-LU public-data panel, the joint realised state of
high residual load and low renewable share is conditionally associated with
higher same-delivery-hour day-ahead price stress than high residual load alone.

This is an ex-post association finding. It is not a causal claim, a forecast,
a tradable signal or evidence that realised fundamentals were available before
the day-ahead auction.

## Data and design

- Panel: 43,848 hourly observations, 2020-01-01 to 2024-12-31.
- Price source: SMARD / Bundesnetzagentur, filter `4169`, region `DE-LU`.
- Price panel quality: no missing hours, duplicate timestamps or missing prices.
- High-price target: monthly 90th percentile of day-ahead price.
- Core control strata: local `year-month × delivery-hour × weekend`.

## Core evidence

### Composite state

- Controlled high-price difference: `+46.33 pp`
- Controlled relative lift: `3.34x`
- Monthly block-bootstrap 95% interval: `[+42.45, +53.01] pp`
- Leave-one-year-out range: `[+45.79, +49.39] pp`
- Weekly circular placebos: `-0.93 pp` to `-5.01 pp`

### Direct residual / renewable contrast

- `high residual + low renewable` versus `high residual only`:
  `+14.10 pp`
- Mantel-Haenszel common odds ratio: `2.32`
- Direct stratified screen p-value: approximately `5.0e-19`

The direct p-value is an unclustered screen only. Serial dependence means it
must not be treated as standalone inferential proof.

### Ramp finding

Residual-load ramp does not show a reliable incremental contribution within
the joint high-residual / low-renewable state:

- Incremental difference: `+2.95 pp`
- Conditional ramp p-value: `0.56`

## Interpretation

The evidence supports a candidate joint-state amplification pattern:
high residual load is the principal price-stress state, while low renewable
share appears to add conditional explanatory information beyond residual load.

No risk-engine recalibration is justified yet. The next step is a targeted
literature and mechanism scan to determine whether this result is already
well-established, unresolved, or operationally under-specified.
