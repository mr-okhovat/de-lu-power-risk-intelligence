# Market Discovery Methods

## Question

Do realised DE-LU fundamentals show an ex-post association with high same-hour
day-ahead price stress after controlling for broad calendar structure?

## Scope

This is a discovery screen, not a causal model, trading signal or forecast.

## Price-stress target

Within each local delivery month, an hour is labelled `price_high_event` when
its day-ahead price is at or above that month's 90th percentile.

This keeps the target relative to the prevailing monthly price regime rather
than allowing structural differences across years to dominate the result.

## Fundamental states

Each state is computed within the same local delivery month:

- high residual load: top decile of official residual load;
- low renewable share: bottom decile of renewable share;
- high absolute residual ramp: top decile of absolute residual-load ramp;
- composite stress: at least two of the three states are active.

## Calendar-controlled comparison

The screen compares exposed and non-exposed observations within common
`year-month × delivery-hour` strata. Only strata containing both exposure
states contribute to the controlled comparison.

## Interpretation

A positive result is only a candidate for deeper robustness analysis. It does
not establish causality, forecasting value, tradability or information
availability before the day-ahead auction.
