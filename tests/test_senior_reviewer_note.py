from pathlib import Path


def test_senior_reviewer_note_exists_and_states_limits() -> None:
    path = Path("reports/senior_reviewer_note.md")
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "# Senior reviewer note" in text
    assert "not a live trading system" in text
    assert "does not claim P&L" in text
    assert "portfolio-grade market analytics" in text
    assert "production-grade trading infrastructure" in text


def test_readme_links_senior_reviewer_note() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "reports/senior_reviewer_note.md" in text
    assert "reports/reviewer_quick_path.md" in text


def test_artifact_manifest_registers_senior_reviewer_note() -> None:
    text = Path("src/core/artifact_manifest.py").read_text(encoding="utf-8")

    assert '("reviewer", "reports/senior_reviewer_note.md", True)' in text


def test_dashboard_reviewer_files_include_senior_note() -> None:
    text = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert '"senior_reviewer_note": Path("reports/senior_reviewer_note.md")' in text
    assert '"Senior reviewer note"' in text
    assert 'selected_paths["senior_reviewer_note"]' in text
