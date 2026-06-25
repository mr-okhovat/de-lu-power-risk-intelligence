# Initial Literature and Market-Evidence Scan

## Purpose

This note separates established market mechanics from potential open research
questions before new variables or external feedback requests are introduced.

## What is already established

### Residual load and merit-order logic

SMARD explains that wholesale-price patterns track forecast residual load:
when a higher share of grid load is covered by wind and solar generation,
prices are lower through the merit-order mechanism.

Relevant source:
- SMARD, *The electricity market in 2023*.

### Fuel-price and cross-border influences

The Bundesnetzagentur monitoring report states that wholesale price trends
largely mirror natural-gas prices because gas plants can set spot prices during
peak demand. It also highlights the role of coupled markets and cross-border
electricity trade.

Relevant source:
- Bundesnetzagentur/Bundeskartellamt, *Monitoring Report 2024*.

### Scarcity-price conditions

A NEON analysis of German price spikes from 2015 to 2024 reports that its
defined scarcity-price hours occurred only with very low wind/PV output and
high residual load. It additionally points to conventional availability and
technical constraints as relevant for the peak-price mechanism.

Relevant source:
- NEON, *Price spikes on the German electricity market*, 2025.

### Multivariate price drivers

Ex-post explainable-AI research on German day-ahead prices identifies load,
wind, solar and fuel prices as important drivers, with meaningful interactions.
It also reports associations between generation ramps and high prices.

Relevant source:
- Trebbien et al., *Understanding electricity prices beyond the merit order
  principle using explainable AI*, 2022.

## Implication for this project

The broad result that high residual load and low renewable generation are
associated with higher prices is not sufficient as a novel public claim.

The project should instead test whether public, pre-auction observable
variables can distinguish:

1. ordinary high-price hours;
2. high-residual / low-renewable pressure hours; and
3. scarcity-like tail-price hours.

## Evidence needed before any external industry question

- Full-text review of academic work on German residual-load price functions.
- Review of price-tail and scarcity-price definitions used in the literature.
- Review of public availability/outage data and publication timing.
- Review of cross-zonal capacity and coupled-market constraints.
- Verification that the proposed distinction is not already operationalised
  in an accessible academic or industry model.
