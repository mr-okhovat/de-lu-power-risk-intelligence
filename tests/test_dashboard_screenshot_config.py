from scripts.capture_dashboard_screenshots import SHOTS


def test_dashboard_screenshot_targets() -> None:
    names = [item[0] for item in SHOTS]
    outputs = [item[1] for item in SHOTS]

    assert "Overview" in names
    assert "Lead time" in names
    assert "Reviewer files" in names
    assert "reports/figures/dashboard/dashboard_lead_time.png" in outputs
