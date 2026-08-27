DE-LU Power Risk Intelligence

A reproducible public-data analytics project for the German/Luxembourg power market.

I built this project to answer a practical question: can public market and system data be turned into a transparent, reviewable risk-intelligence layer that helps explain when the power market is under stress — without pretending to be a trading bot or a black-box forecasting model?

The project focuses on data quality, market-state diagnostics, residual-load and renewable stress, price-event analysis, and reviewer-ready evidence. The goal is not to claim a profitable strategy. The goal is to build a technically disciplined framework that can be inspected, challenged, extended, and eventually connected to richer market and operational data.

What the project does

The current framework covers several layers:

Public-data ingestion and staging

SMARD-based electricity-market and system data

hourly DE-LU market tables

reproducible staging and metadata handling

Data quality and release control

hard staging checks

residual-load reconciliation policy

feature-quality checks

release-gate logic

dataset provenance and availability controls

Market-risk feature engineering

load and renewable share

residual load

load / renewable / residual-load ramps

percentile-based stress indicators

explainable multi-factor risk scores

rule-based signal logic

Price and event diagnostics

same-hour signal / price-event evaluation

cross-month diagnostics

lead-time aggregates

event-lift, precision and recall diagnostics

explicit separation between diagnostic usefulness and forecast-skill claims

Review and downstream outputs

reviewer packs and evidence notes

run catalog and active-run selection

SQL-ready exports

Power BI-ready outputs

Streamlit review dashboard

project-health and artifact tracking

Current validated development baseline

The latest validated working baseline includes:

189 automated tests passing

a policy-driven Market Data Admission layer with the decisions:

ACCEPT

ACCEPT_WITH_WARNINGS

QUARANTINE

REJECT

explainable reliability scoring

coverage, gap, provenance and contract-status checks

fail-fast orchestration for rejected datasets

an end-to-end August 2024 validation sample that returned:

decision: ACCEPT

reliability score: 100.0

The project should still be read as a research / analytics prototype, not as production trading infrastructure.

Repository-status note

Some validation and admission-control work has been developed and tested in working / feature snapshots before full consolidation into main. The README reflects the latest validated project baseline available to me, while individual files on main may temporarily lag the newest working snapshot.

That distinction is intentional: I would rather state the repository status clearly than imply that every working-build artifact is already merged and productionized.

Reviewer quick path

If you only have a few minutes, start here:

reports/reviewer_quick_path.md

reports/senior_reviewer_note.md

reports/reviewer_ready_v2.md

reports/market_month_run_catalog.md

reports/active_run_selection.md

Streamlit dashboard:

streamlit run app/streamlit_app.py

For the newer admission-control work, also inspect the relevant feature branch and validation evidence before drawing conclusions from main alone.

How I think about the pipeline

At a high level:

public market data
    ↓
raw ingestion
    ↓
hourly staging
    ↓
hard quality checks
    ↓
feature engineering
    ↓
market-data admission / release controls
    ↓
risk and stress diagnostics
    ↓
price-event and lead-time analysis
    ↓
reviewer / SQL / BI outputs

The important design choice is that analytics should not silently proceed when the input data is unreliable. The quality and admission layers are therefore treated as part of the analytical system, not as an afterthought.

Signal logic

The explainable stress logic currently uses combinations of:

residual load

renewable share

load ramp

residual-load ramp

renewable-generation ramp

percentile / regime thresholds

These signals are deliberately simple enough to inspect.

They are best understood as stress proxies and diagnostic features, not as finished desk signals.

Price-event diagnostics

The reviewer-ready checkpoint includes both same-hour and lead-time diagnostics.

Current reviewer readout includes:

same-hour aggregate event lift: 1.770

aggregate precision: 0.463

aggregate recall: 0.025

The interpretation matters more than the raw numbers:

same-hour event lift can be useful as a diagnostic

low recall means the current rule set is selective and incomplete

some forward-window event concentration appears within the next few hours

this is not yet evidence of forecast skill

The relevant reviewer file is:

reports/reviewer_ready_v2.md

Running the project

Install dependencies:

pip install -r requirements.txt

Run tests:

python -m pytest

Run the sample pipeline:

bash scripts/run_sample_pipeline.sh

Or, if make is available:

make sample

Dry-run the orchestration plan:

python -m src.orchestration.run_all --config config/pipeline_sample.yaml --dry-run

A higher-level project checkpoint/orchestration layer is also available in the newer development work.

Dashboard

The Streamlit dashboard is intended as a review surface, not as the core model.

Current panels include:

cross-month overview

selected-month KPI cards

market / price and risk timelines

event-lift diagnostics

confusion buckets

signal-positive hours

reason-code diagnostics

lead-time views

dataset-intake views

reviewer-file checklist

Run it locally with:

streamlit run app/streamlit_app.py

Dashboard screenshots are stored under:

reports/figures/dashboard/

What this project does not claim

To keep the project useful, I try to be explicit about what it is not.

It is not:

a live trading system

an execution engine

a proven alpha model

a P&L backtest claiming profitability

a grid-control / SCADA / EMS / redispatch application

a replacement for proprietary desk data

a production forecast of balancing or intraday prices

Those would require additional data, validation and operational context.

Main limitations / next research questions

The next useful extensions are not “more features for the sake of features.” They are mainly about stronger evidence.

Priority areas include:

longer-window validation

forecast-error data

balancing-market data

outages and cross-border flows

weather and renewable forecasts

stronger regime calibration

separation of structural versus event-driven stress

richer portfolio / exposure mapping

clearer testing of whether signals add information beyond simple market baselines

I am especially interested in feedback on which parts of the framework are directionally useful for real market-risk / trading-analytics work, and which parts remain too simple or too research-like for a desk environment.

Why this project exists

The project is also a portfolio of how I work:

evidence before claims

data quality before modelling

explicit limitations

reproducible pipelines

reviewer-oriented outputs

market logic that can be explained rather than hidden

My broader interest is at the intersection of European power markets, market / portfolio risk, data analytics, and decision support.

If you are reviewing this from an energy company, research group, or trading / risk team, practical criticism is very welcome.
