# Dashboard screenshot automation

Dashboard screenshots are captured with Playwright.

Run:

    python scripts/capture_dashboard_screenshots.py

Output files:

    reports/figures/dashboard/dashboard_overview.png
    reports/figures/dashboard/dashboard_selected_month.png
    reports/figures/dashboard/dashboard_diagnostics.png
    reports/figures/dashboard/dashboard_lead_time.png
    reports/figures/dashboard/dashboard_dataset_intake.png
    reports/figures/dashboard/dashboard_data_availability.png
    reports/figures/dashboard/dashboard_run_catalog.png
    reports/figures/dashboard/dashboard_project_health.png
    reports/figures/dashboard/dashboard_reviewer_files.png

The script starts Streamlit locally, opens each dashboard tab and saves a full-page screenshot.
