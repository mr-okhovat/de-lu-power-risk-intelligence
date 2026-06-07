# Dashboard runbook

The local dashboard is a Streamlit app for reviewing current analytics outputs.

Run:

    streamlit run app/streamlit_app.py

The dashboard reads existing CSV and report outputs. It does not run ingestion and does not rebuild the model.

Current panels:

- cross-month overview
- monthly event lift
- base event rate versus signal-positive event rate
- selected month snapshot
- KPI cards
- price and risk timelines
- confusion bucket chart
- signal-positive hours
- reason-code table
- price-event label table
- top risk cases
- lead-time evaluation panel
- reviewer file checklist
- CSV download buttons

This is an analyst dashboard prototype, not a production web app.
