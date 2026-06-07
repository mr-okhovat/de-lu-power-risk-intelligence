# Dashboard runbook

The local dashboard is a Streamlit app for reviewing the current analytics outputs.

Run:

    streamlit run app/streamlit_app.py

The dashboard reads existing CSV and report outputs. It does not run ingestion and does not rebuild the model.

Current panels:

- cross-month overview
- selected month snapshot
- KPI cards
- price and risk timelines
- confusion bucket chart
- signal-positive hours
- reason-code table
- price-event label table
- top risk cases
- reviewer file checklist

This is an analyst dashboard prototype, not a production web app.
