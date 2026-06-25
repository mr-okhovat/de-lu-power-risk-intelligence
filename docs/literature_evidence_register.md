# Literature Evidence Register: DE-LU Day-Ahead Tail-Risk Research

## Purpose

Separate established German power-market mechanics from a potentially useful,
operational research question before new variables are added.

## Literature verdict

The broad relationship between residual load, renewable generation and German
day-ahead prices is established. It is not the project's novelty claim.

The remaining candidate contribution is operational:

> Can a public, timestamp-audited information set available before the
> day-ahead auction identify price-tail risk more effectively than a
> forecast-residual-load-only baseline?

This is not yet confirmed as an open literature gap. It is the question to
test through a source-vintage and data-eligibility audit.

## Evidence register

### Trebbien et al. (2023)

Trebbien, J., Rydin Gorjao, L., Praktiknjo, A., Schaefer, B. and Witthaut, D.
(2023) 'Understanding electricity prices beyond the merit order principle
using explainable AI', Energy and AI, 13, 100250.
doi: 10.1016/j.egyai.2023.100250.

Use for this project:
- German day-ahead ex-post evidence.
- Load, wind, solar and fuel prices are material price drivers.
- Interaction effects and generation ramps matter in ex-post analysis.

Limitation for this project:
- It does not establish a public, timestamp-audited pre-auction information
  set or an operational price-tail classifier.

### Guertler and Paulsen (2018)

Guertler, M. and Paulsen, T. (2018) 'The effect of wind and solar power
forecasts on day-ahead and intraday electricity prices in Germany',
Energy Economics, 75, pp. 150-162.
doi: 10.1016/j.eneco.2018.07.006.

Use for this project:
- Forecast wind and solar information affects German power prices.
- Fuel technologies and non-linear demand conditions matter.

Limitation for this project:
- Does not solve the current source-vintage question for a reproducible
  2020-2024 public-data tail-risk design.

### Uniejewski and Ziel (2025)

Uniejewski, B. and Ziel, F. (2025) 'Probabilistic Forecasts of Load, Solar
and Wind for Electricity Price Forecasting', arXiv:2501.06180.

Use for this project:
- Forecast uncertainty can improve German electricity-price forecasting.
- A point forecast alone may be insufficient for tail-risk assessment.

Limitation for this project:
- Preprint; not treated as final peer-reviewed evidence.
- Does not remove the need for an event-level publication-time audit.

### NEON (2025)

NEON (2025) 'Price spikes on the German electricity market'.

Use for this project:
- Market-study evidence that scarcity-price hours occur with very low wind/PV
  generation and high residual load.
- Conventional availability and operational restrictions are relevant.

Limitation for this project:
- Market study, not peer-reviewed causal evidence.
- Supports mechanism prioritisation, not a novelty claim.

### ENTSO-E Transparency Data Descriptions (2023)

ENTSO-E (2023) Detailed Data Descriptions, v3r4.

Use for this project:
- Day-ahead wind and solar forecasts may be published no later than D-1
  18:00 Brussels time.
- Planned unit unavailability is published after plan approval.
- Actual unit unavailability is published after the actual availability change.

Implication:
- Publication timing must be audited against the day-ahead auction gate.
- Actual outage data cannot be admitted automatically as a pre-auction feature.

### EPEX SPOT Trading Brochure (2024)

EPEX SPOT (2024) Trading Brochure.

Use for this project:
- Coupled day-ahead order book closes D-1 at 12:00 CET/CEST.

Implication:
- A D-1 18:00 forecast is not automatically eligible as a pre-auction input.

### ACER (2024)

ACER (2024) Capacities for cross-zonal electricity trade and congestion
management.

Use for this project:
- Cross-zonal capacity and congestion management can mitigate price pressure
  and price volatility.

Limitation for this project:
- Requires a separate archived-vintage and publication-time audit before
  inclusion in any model.
