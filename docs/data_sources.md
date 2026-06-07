# Data Sources

## Policy

Use only public, official, or explicitly licensed data.

Do not fabricate market data or real results.

## SMARD / Bundesnetzagentur

Primary source for German/Luxembourg electricity market data.

Use cases:

- load
- generation
- residual load
- prices
- imports/exports where available

Status: required for Phase 1.

## ENTSO-E Transparency Platform

Use cases:

- forecasts
- load/generation
- cross-border flows
- balancing-related transparency data

Status: future module. API token required.

Credentials must be stored as environment variables.

## Regelleistung.net / German TSOs

Use cases:

- FCR
- aFRR
- mFRR
- balancing market context

Status: future module. CSV/manual fallback may be required.

## DWD / Bright Sky

Use cases:

- wind speed
- solar radiation
- temperature

Status: future weather driver module.

## GIE AGSI/ALSI

Use cases:

- gas storage context
- LNG context

Status: optional future module.

## EPEX SPOT

Use as market reference.

Do not assume licensed EPEX data is freely available.

## Required Metadata

Every raw dataset must include source, source URL or endpoint, retrieval timestamp, market/region, unit, resolution, original timestamp, normalized timestamp, timezone, transformation history, and license or access note.
