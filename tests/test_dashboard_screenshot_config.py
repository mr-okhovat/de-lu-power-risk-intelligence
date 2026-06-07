from scripts.capture_dashboard_screenshots import SHOTS


def test_dashboard_screenshot_targets() -> None:
    names = [item[0] for item in SHOTS]
    outputs = [item[1] for item in SHOTS]

    assert "Overview" in names
    assert "Lead time" in names
    assert "Dataset intake" in names
    assert "Data availability" in names
    assert "Run catalog" in names
    assert "Project health" in names
    assert "Reviewer files" in names
    assert "reports/figures/dashboard/dashboard_data_availability.png" in outputs
    assert "reports/figures/dashboard/dashboard_run_catalog.png" in outputs
    assert "reports/figures/dashboard/dashboard_project_health.png" in outputs
