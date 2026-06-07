# Dashboard screenshot guide

Use this guide when preparing a private review or a later LinkedIn post.

## Run the dashboard

    streamlit run app/streamlit_app.py

In GitHub Codespaces, open the forwarded Streamlit port in the browser.

## Screenshots to capture

Capture these views:

1. Overview tab
   - cross-month table
   - monthly event lift chart
   - event-rate chart

2. Selected month tab
   - KPI cards
   - price/risk timeline
   - signal-positive hours table

3. Diagnostics tab
   - reason-code table
   - price-event label table
   - top risk cases

4. Reviewer files tab
   - file checklist showing the main reviewer reports

## Suggested filenames

Save screenshots locally as:

    reports/figures/dashboard_overview.png
    reports/figures/dashboard_selected_month.png
    reports/figures/dashboard_diagnostics.png
    reports/figures/dashboard_reviewer_files.png

Only commit screenshots if they are clean, readable and do not include private browser/account information.

## Current positioning

The dashboard is a local analyst prototype.

Do not describe it as:

- a production web app
- a trading system
- a forecasting tool
- a P&L backtest
- a desk-grade system

Acceptable wording:

A lightweight local dashboard for reviewing the current DE-LU public-data price-risk analytics outputs.
