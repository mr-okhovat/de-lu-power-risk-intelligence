from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VERSION = "6B.1"


def paths(start: str, end: str, market: str) -> dict[str, str]:
    tag = f"{market}_{start}_to_{end}"
    rtag = f"{start}_to_{end}"

    return {
        "staging": f"data/staging/clean_hourly_{tag}.csv",
        "features": f"data/processed/hourly_features_{tag}.csv",
        "market_export": f"dashboards/market_overview_{tag}.csv",
        "risk_signals": f"data/processed/risk_signals_{tag}.csv",
        "regime_distribution": f"dashboards/risk_regime_distribution_{tag}.csv",
        "reason_codes": f"dashboards/risk_reason_code_summary_{tag}.csv",
        "top_risk_hours": f"dashboards/top_risk_hours_{tag}.csv",
        "pipeline_summary": f"reports/pipeline_run_summary_{rtag}.md",
        "data_quality": f"reports/data_quality_{rtag}.md",
        "staging_checks": f"reports/staging_hard_checks_{rtag}.md",
        "feature_quality": f"reports/feature_quality_{rtag}.md",
        "risk_quality": f"reports/risk_signal_quality_{rtag}.md",
        "risk_diagnostics": f"reports/risk_diagnostics_{rtag}.md",
        "sql_schema": "sql/schema_power_market_features.sql",
    }


def exists(path: str) -> bool:
    return Path(path).exists()


def row_count(path: str) -> int | None:
    p = Path(path)
    if not p.exists():
        return None
    return len(pd.read_csv(p))


def report_status(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return "missing"

    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("- Status:"):
            return line.split(":", 1)[1].strip().strip("`")

    return "not stated"


def make_markdown(
    *,
    start: str,
    end: str,
    market: str,
    region: str,
    files: dict[str, str],
    checks: dict[str, bool],
    counts: dict[str, int | None],
    statuses: dict[str, str],
) -> str:
    missing = [name for name, ok in checks.items() if not ok]

    status = "PASS" if not missing else "CHECK NEEDED"

    lines = [
        "# Project review note",
        "",
        f"Version: {VERSION}",
        f"Status: {status}",
        f"Window: {start} to {end}",
        f"Market label: {market}",
        f"SMARD region: {region}",
        "",
        "This repo is a small public-data pipeline for DE-LU power market risk intelligence. It starts from SMARD data, builds a clean hourly table, derives a few market features, exports dashboard-ready tables, and creates a first rule-based stress signal.",
        "",
        "It is not a trading strategy. There is no P&L, execution logic, price forecast, or claim that the signal is profitable.",
        "",
        "## What is implemented",
        "",
        "- SMARD filter discovery and raw data ingestion",
        "- clean hourly staging table",
        "- staging validation and residual-load reconciliation",
        "- feature table: load, residual load, renewables, shares, ramps",
        "- SQL / Power BI-ready market export",
        "- rule-based risk signal",
        "- risk diagnostics: regimes, reason codes, top risk hours",
        "- one-command sample pipeline",
        "",
        "## Main files",
        "",
    ]

    for name, path in files.items():
        mark = "ok" if checks[name] else "missing"
        lines.append(f"- {name}: `{path}` ({mark})")

    lines += [
        "",
        "## Row counts",
        "",
    ]

    for name, count in counts.items():
        lines.append(f"- {name}: {count}")

    lines += [
        "",
        "## Report statuses",
        "",
    ]

    for name, value in statuses.items():
        lines.append(f"- {name}: {value}")

    lines += [
        "",
        "## How to rerun",
        "",
        "```bash",
        "bash scripts/run_sample_pipeline.sh",
        "```",
        "",
        "For a non-executing plan:",
        "",
        "```bash",
        "python -m src.orchestration.run_all --config config/pipeline_sample.yaml --dry-run",
        "```",
        "",
        "## What I would ask a reviewer",
        "",
        "Is this feature framing directionally useful for a power trading analytics context, or is the rule logic still too simple compared with how a desk would actually look at residual load, renewables and ramps?",
        "",
        "## Current weak spots",
        "",
        "- the sample window is only three days",
        "- no price data yet",
        "- no forecast error data yet",
        "- no balancing, weather, outage or cross-border flow layer yet",
        "- risk score is explainable but still basic",
        "- backtesting is not part of the automated pipeline yet",
        "",
    ]

    if missing:
        lines += ["## Missing files", ""]
        for item in missing:
            lines.append(f"- {item}: `{files[item]}`")

    return "\n".join(lines)


def build_pack(start: str, end: str, market: str, region: str, report: str, json_out: str) -> None:
    files = paths(start, end, market)

    required = [
        "staging",
        "features",
        "market_export",
        "risk_signals",
        "risk_diagnostics",
        "pipeline_summary",
        "sql_schema",
    ]

    checks = {name: exists(path) for name, path in files.items()}

    counts = {
        "staging": row_count(files["staging"]),
        "features": row_count(files["features"]),
        "market_export": row_count(files["market_export"]),
        "risk_signals": row_count(files["risk_signals"]),
        "regime_distribution": row_count(files["regime_distribution"]),
        "reason_codes": row_count(files["reason_codes"]),
        "top_risk_hours": row_count(files["top_risk_hours"]),
    }

    statuses = {
        "pipeline_summary": report_status(files["pipeline_summary"]),
        "data_quality": report_status(files["data_quality"]),
        "staging_checks": report_status(files["staging_checks"]),
        "feature_quality": report_status(files["feature_quality"]),
        "risk_quality": report_status(files["risk_quality"]),
        "risk_diagnostics": report_status(files["risk_diagnostics"]),
    }

    missing_required = [name for name in required if not checks[name]]
    pack_status = "PASS" if not missing_required else "CHECK NEEDED"

    markdown = make_markdown(
        start=start,
        end=end,
        market=market,
        region=region,
        files=files,
        checks=checks,
        counts=counts,
        statuses=statuses,
    )

    report_path = Path(report)
    json_path = Path(json_out)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    report_path.write_text(markdown, encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "version": VERSION,
                "status": pack_status,
                "start": start,
                "end": end,
                "market": market,
                "region": region,
                "files": files,
                "checks": checks,
                "row_counts": counts,
                "report_statuses": statuses,
                "missing_required": missing_required,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"OK | reviewer note status={pack_status} | report={report_path}")

    if missing_required:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--market-label", default="DE-LU")
    parser.add_argument("--smard-region", default="DE")
    parser.add_argument("--report", required=True)
    parser.add_argument("--json", required=True)
    args = parser.parse_args()

    build_pack(
        start=args.start,
        end=args.end,
        market=args.market_label,
        region=args.smard_region,
        report=args.report,
        json_out=args.json,
    )


if __name__ == "__main__":
    main()
