# Dashboard runbook

The local dashboard is a lightweight Streamlit app for reviewing the current analytics outputs.

Run:

    streamlit run app/streamlit_app.py

The dashboard reads existing CSV outputs. It does not run ingestion or rebuild the pipeline.

Current panels:

- month selector
- KPI cards
- price/risk timeline
- confusion bucket chart
- cross-month price-risk table
- top risk cases

This is an analyst dashboard prototype, not a production web app.
