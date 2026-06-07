from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


RISK_DIAGNOSTIC_SCHEMA_VERSION = "4B.1"


REQUIRED_RISK_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "risk_score",
    "regime_label",
    "reason_codes",
    "risk_schema_version",
]


REGIME_ORDER = ["NORMAL", "WATCH", "STRESSED", "EXTREME"]


@dataclass(frozen=True)
class RiskDiagnosticResult:
    status: str
    row_count: int
    min_risk_score: float
    max_risk_score: float
    mean_risk_score: float
    median_risk_score: float
    unique_regimes: list[str]
    unique_reason_codes: list[str]
    no_rule_triggered_count: int
    high_risk_count: int
    extreme_count: int
    required_columns_missing: list[str]
    duplicate_timestamp_count: int
    notes: list[str]


def load_risk_signals(path: str | Path) -> pd.DataFrame:
    signal_path = Path(path)

    if not signal_path.exists():
        raise FileNotFoundError(f"Risk signal file not found: {signal_path}")

    df = pd.read_csv(signal_path)

    missing = [column for column in REQUIRED_RISK_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Risk signal file is missing required columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], utc=True).dt.tz_convert(
        "Europe/Berlin"
    )

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def split_reason_codes(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []

    return [item.strip() for item in str(value).split("|") if item.strip()]


def build_regime_distribution(signals: pd.DataFrame) -> pd.DataFrame:
    counts = signals["regime_label"].value_counts().to_dict()
    total = len(signals)

    rows: list[dict[str, object]] = []

    for regime in REGIME_ORDER:
        count = int(counts.get(regime, 0))
        share = count / total if total else 0.0

        rows.append(
            {
                "regime_label": regime,
                "count": count,
                "share": share,
                "risk_diagnostic_schema_version": RISK_DIAGNOSTIC_SCHEMA_VERSION,
            }
        )

    return pd.DataFrame(rows)


def build_reason_code_summary(signals: pd.DataFrame) -> pd.DataFrame:
    counter: Counter[str] = Counter()

    for value in signals["reason_codes"]:
        counter.update(split_reason_codes(value))

    rows = [
        {
            "reason_code": reason_code,
            "count": int(count),
            "share_of_rows": float(count / len(signals)) if len(signals) else 0.0,
            "risk_diagnostic_schema_version": RISK_DIAGNOSTIC_SCHEMA_VERSION,
        }
        for reason_code, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]

    return pd.DataFrame(rows)


def build_top_risk_hours(signals: pd.DataFrame, *, top_n: int = 20) -> pd.DataFrame:
    top = (
        signals.sort_values(
            ["risk_score", "timestamp_utc"],
            ascending=[False, True],
        )
        .head(top_n)
        .copy()
    )

    top["risk_diagnostic_schema_version"] = RISK_DIAGNOSTIC_SCHEMA_VERSION

    return top


def diagnose_risk_signals(signals: pd.DataFrame) -> RiskDiagnosticResult:
    required_columns_missing = [
        column for column in REQUIRED_RISK_COLUMNS if column not in signals.columns
    ]

    duplicate_timestamp_count = (
        int(signals["timestamp_utc"].duplicated().sum())
        if "timestamp_utc" in signals.columns
        else 0
    )

    unique_regimes = (
        sorted(str(item) for item in signals["regime_label"].dropna().unique())
        if "regime_label" in signals.columns
        else []
    )

    reason_counter: Counter[str] = Counter()

    if "reason_codes" in signals.columns:
        for value in signals["reason_codes"]:
            reason_counter.update(split_reason_codes(value))

    unique_reason_codes = sorted(reason_counter.keys())

    no_rule_triggered_count = int(reason_counter.get("NO_RULE_TRIGGERED", 0))

    high_risk_count = int((signals["risk_score"] >= 60).sum()) if "risk_score" in signals.columns else 0
    extreme_count = int((signals["regime_label"] == "EXTREME").sum()) if "regime_label" in signals.columns else 0

    min_risk_score = float(signals["risk_score"].min()) if "risk_score" in signals.columns else float("nan")
    max_risk_score = float(signals["risk_score"].max()) if "risk_score" in signals.columns else float("nan")
    mean_risk_score = float(signals["risk_score"].mean()) if "risk_score" in signals.columns else float("nan")
    median_risk_score = float(signals["risk_score"].median()) if "risk_score" in signals.columns else float("nan")

    notes: list[str] = []

    if required_columns_missing:
        notes.append(f"Missing required risk diagnostic columns: {required_columns_missing}")

    if duplicate_timestamp_count:
        notes.append(f"Duplicate timestamps found: {duplicate_timestamp_count}")

    if max_risk_score == 0:
        notes.append(
            "Risk scores are all zero for this window. This can be acceptable for a calm/short sample, but it limits diagnostic usefulness."
        )

    if len(unique_regimes) == 1:
        notes.append(
            "Only one risk regime appears in this sample. This may be normal for a short window but should be reviewed on longer history."
        )

    if no_rule_triggered_count == len(signals):
        notes.append(
            "Every row has NO_RULE_TRIGGERED. This indicates the sample does not contain rule-detected stress after minimum-history constraints."
        )

    if high_risk_count == 0:
        notes.append(
            "No STRESSED or EXTREME rows found in this sample. This is not a failure; it means the short window does not contain high rule-based stress."
        )

    if not notes:
        notes.append("Risk diagnostics passed Phase 4B checks.")

    blocking_issue = bool(required_columns_missing) or duplicate_timestamp_count > 0

    status = "STOP — NEEDS VERIFICATION" if blocking_issue else "PASS"

    return RiskDiagnosticResult(
        status=status,
        row_count=int(len(signals)),
        min_risk_score=min_risk_score,
        max_risk_score=max_risk_score,
        mean_risk_score=mean_risk_score,
        median_risk_score=median_risk_score,
        unique_regimes=unique_regimes,
        unique_reason_codes=unique_reason_codes,
        no_rule_triggered_count=no_rule_triggered_count,
        high_risk_count=high_risk_count,
        extreme_count=extreme_count,
        required_columns_missing=required_columns_missing,
        duplicate_timestamp_count=duplicate_timestamp_count,
        notes=notes,
    )


def render_risk_diagnostic_report(
    *,
    result: RiskDiagnosticResult,
    risk_signal_input: str | Path,
    regime_distribution_output: str | Path,
    reason_code_summary_output: str | Path,
    top_risk_hours_output: str | Path,
) -> str:
    lines = [
        "# Risk Signal Diagnostic Report — Phase 4B",
        "",
        f"- Risk signal input: `{risk_signal_input}`",
        f"- Regime distribution output: `{regime_distribution_output}`",
        f"- Reason-code summary output: `{reason_code_summary_output}`",
        f"- Top-risk-hours output: `{top_risk_hours_output}`",
        f"- Status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Diagnostic schema version: `{RISK_DIAGNOSTIC_SCHEMA_VERSION}`",
        "",
        "## Score Summary",
        "",
        f"- Min risk score: `{result.min_risk_score}`",
        f"- Max risk score: `{result.max_risk_score}`",
        f"- Mean risk score: `{result.mean_risk_score}`",
        f"- Median risk score: `{result.median_risk_score}`",
        "",
        "## Coverage Summary",
        "",
        f"- Unique regimes: `{result.unique_regimes}`",
        f"- Unique reason codes: `{result.unique_reason_codes}`",
        f"- NO_RULE_TRIGGERED count: `{result.no_rule_triggered_count}`",
        f"- STRESSED/EXTREME count: `{result.high_risk_count}`",
        f"- EXTREME count: `{result.extreme_count}`",
        f"- Duplicate timestamps: `{result.duplicate_timestamp_count}`",
        "",
        "## Required Columns Missing",
        "",
    ]

    if result.required_columns_missing:
        for column in result.required_columns_missing:
            lines.append(f"- `{column}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Notes", ""])

    for note in result.notes:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This diagnostic layer checks risk-signal distribution and reason-code coverage. It does not evaluate predictive skill, market profitability, or backtest performance.",
            "",
            "A calm short sample can legitimately produce mostly NORMAL or NO_RULE_TRIGGERED rows. Longer windows are required before judging usefulness.",
            "",
        ]
    )

    return "\n".join(lines)


def build_risk_diagnostics(
    *,
    risk_signal_input: str | Path,
    regime_distribution_output: str | Path,
    reason_code_summary_output: str | Path,
    top_risk_hours_output: str | Path,
    report_output: str | Path,
    json_output: str | Path,
    top_n: int = 20,
) -> RiskDiagnosticResult:
    signals = load_risk_signals(risk_signal_input)

    regime_distribution = build_regime_distribution(signals)
    reason_code_summary = build_reason_code_summary(signals)
    top_risk_hours = build_top_risk_hours(signals, top_n=top_n)

    result = diagnose_risk_signals(signals)

    regime_distribution_output = Path(regime_distribution_output)
    reason_code_summary_output = Path(reason_code_summary_output)
    top_risk_hours_output = Path(top_risk_hours_output)
    report_output = Path(report_output)
    json_output = Path(json_output)

    regime_distribution_output.parent.mkdir(parents=True, exist_ok=True)
    reason_code_summary_output.parent.mkdir(parents=True, exist_ok=True)
    top_risk_hours_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)

    regime_distribution.to_csv(regime_distribution_output, index=False)
    reason_code_summary.to_csv(reason_code_summary_output, index=False)
    top_risk_hours.to_csv(top_risk_hours_output, index=False)

    report_output.write_text(
        render_risk_diagnostic_report(
            result=result,
            risk_signal_input=risk_signal_input,
            regime_distribution_output=regime_distribution_output,
            reason_code_summary_output=reason_code_summary_output,
            top_risk_hours_output=top_risk_hours_output,
        ),
        encoding="utf-8",
    )

    json_output.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | risk diagnostics status={result.status} | report={report_output}")
    print(f"OK | regime distribution={regime_distribution_output}")
    print(f"OK | reason-code summary={reason_code_summary_output}")
    print(f"OK | top risk hours={top_risk_hours_output}")

    if result.status == "STOP — NEEDS VERIFICATION":
        raise SystemExit(1)

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Phase 4B risk diagnostics.")

    parser.add_argument("--risk-signal-input", required=True)
    parser.add_argument("--regime-distribution-output", required=True)
    parser.add_argument("--reason-code-summary-output", required=True)
    parser.add_argument("--top-risk-hours-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--top-n", type=int, default=20)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_risk_diagnostics(
        risk_signal_input=args.risk_signal_input,
        regime_distribution_output=args.regime_distribution_output,
        reason_code_summary_output=args.reason_code_summary_output,
        top_risk_hours_output=args.top_risk_hours_output,
        report_output=args.report_output,
        json_output=args.json_output,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
