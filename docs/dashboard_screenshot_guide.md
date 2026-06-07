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

4. Lead time tab
   - aggregate lead-time table
   - event lift by target
   - precision/recall by target

5. Reviewer files tab
   - file checklist showing the main reviewer reports

## Suggested filenames

    reports/figures/dashboard/dashboard_overview.png
    reports/figures/dashboard/dashboard_selected_month.png
    reports/figures/dashboard/dashboard_diagnostics.png
    reports/figures/dashboard/dashboard_lead_time.png
    reports/figures/dashboard/dashboard_reviewer_files.png

Only commit screenshots if they are clean, readable and do not include private browser/account information.
