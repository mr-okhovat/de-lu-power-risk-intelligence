from pathlib import Path

import pandas as pd


def test_dashboard_registers_active_selection_tab() -> None:
    text = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert '"Active selection"' in text
    assert "def load_active_selection()" in text
    assert "def render_active_selection(" in text
    assert "render_active_selection(load_active_selection())" in text


def test_artifact_manifest_registers_active_selection_outputs() -> None:
    text = Path("src/core/artifact_manifest.py").read_text(encoding="utf-8")

    assert '("active_selection", "reports/active_run_selection.md", True)' in text
    assert '("active_selection", "reports/active_run_selection.json", True)' in text
    assert '("active_selection", "dashboards/active_run_selection.csv", True)' in text


def test_active_selection_output_is_reviewer_ready() -> None:
    csv_path = Path("dashboards/active_run_selection.csv")
    report_path = Path("reports/active_run_selection.md")
    payload_path = Path("reports/active_run_selection.json")

    assert csv_path.exists()
    assert report_path.exists()
    assert payload_path.exists()

    df = pd.read_csv(csv_path)

    assert len(df) == 4
    assert set(df["run_status"]) == {"READY"}
    assert set(df["market"]) == {"DE-LU"}
    assert {"run_id", "start", "end", "same_hour_event_lift", "window_next_3h_event_lift"}.issubset(df.columns)

    report = report_path.read_text(encoding="utf-8")
    assert "# Active run selection" in report
    assert "Selected runs" in report
