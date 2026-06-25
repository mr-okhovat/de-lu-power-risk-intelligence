# Market Discovery Robustness Screen

## Scope

This is an ex-post association screen. It does not establish causality,
forecastability, trading value or information availability before the
day-ahead auction.

## Input

- Input rows: `43848`
- Rows after explicit raw-input completeness check: `43847`
- Rows excluded for missing raw inputs: `1`

## Base Composite Result

- Controlled high-price difference: `50.81163693471178` pp
- Controlled relative lift: `4.289110474830177`
- Controlled price difference: `58.856850935635094` EUR/MWh
- Valid common-support strata: `632`

## Directional Stability

- Positive years: `5` / `5`
- Positive months: `58` / `60`
- Positive threshold scenarios: `5` / `5`

## Conditional Ramp Check

- Population: hours already meeting high residual load and low
  renewable share conditions.
- Ramp-high exposed event rate: `0.7761102811354069`
- Ramp-low event rate: `0.7241273937253836`
- Incremental ramp difference: `5.198288741002333` pp
- Incremental ramp lift: `1.071786936746847`
- Valid support strata: `65`

## Interpretation Rule

The result is worth deeper mechanism work only when direction remains
stable across threshold choices and supported calendar strata. It is
still not a forecasting or tradability result.
