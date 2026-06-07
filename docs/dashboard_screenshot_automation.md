# Dashboard screenshot automation

The dashboard screenshots can be captured automatically with Playwright.

Run:

    python -m playwright install chromium
    python scripts/capture_dashboard_screenshots.py

Output files:

    reports/figures/dashboard/dashboard_overview.png
    reports/figures/dashboard/dashboard_selected_month.png
    reports/figures/dashboard/dashboard_diagnostics.png
    reports/figures/dashboard/dashboard_reviewer_files.png

The script starts Streamlit locally, opens each dashboard tab and saves a full-page screenshot.
