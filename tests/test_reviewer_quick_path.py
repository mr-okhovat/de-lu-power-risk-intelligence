from pathlib import Path


def test_reviewer_quick_path_file_exists_and_has_review_flow() -> None:
    path = Path("reports/reviewer_quick_path.md")
    text = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "# Reviewer quick path" in text
    assert "Review in 5 minutes" in text
    assert "reports/reviewer_ready_v2.md" in text
    assert "reports/active_run_selection.md" in text
    assert "not be described as production trading infrastructure" in text


def test_readme_links_reviewer_quick_path() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "## Reviewer quick path" in text
    assert "reports/reviewer_quick_path.md" in text
    assert "reports/active_run_selection.md" in text


def test_artifact_manifest_registers_reviewer_quick_path() -> None:
    text = Path("src/core/artifact_manifest.py").read_text(encoding="utf-8")

    assert '("reviewer", "reports/reviewer_quick_path.md", True)' in text


def test_dashboard_reviewer_files_include_quick_path() -> None:
    text = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert '"reviewer_quick_path": Path("reports/reviewer_quick_path.md")' in text
    assert '"Reviewer quick path"' in text
    assert 'selected_paths["reviewer_quick_path"]' in text
