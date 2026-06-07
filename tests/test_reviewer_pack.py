from pathlib import Path

from src.reporting.reviewer_pack import paths, report_status, row_count


def test_paths_use_market_and_dates() -> None:
    result = paths("2024-06-01", "2024-06-03", "DE-LU")

    assert result["staging"].endswith("clean_hourly_DE-LU_2024-06-01_to_2024-06-03.csv")
    assert result["risk_signals"].endswith("risk_signals_DE-LU_2024-06-01_to_2024-06-03.csv")


def test_report_status_reads_status_line(tmp_path: Path) -> None:
    p = tmp_path / "report.md"
    p.write_text("# Test\n\n- Status: `PASS`\n", encoding="utf-8")

    assert report_status(str(p)) == "PASS"


def test_row_count(tmp_path: Path) -> None:
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

    assert row_count(str(p)) == 2
