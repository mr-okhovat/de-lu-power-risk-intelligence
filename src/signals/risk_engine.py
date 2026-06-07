from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


RISK_SCHEMA_VERSION = "4A.1"


REQUIRED_FEATURE_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "total_load_mw",
    "residual_load_official_mw",
    "renewable_generation_mw",
    "renewable_share",
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
    "feature_schema_version",
]


RISK_OUTPUT_COLUMNS = [
    "timestamp_utc",
    "timestamp_local",
    "market_label",
    "smard_region",
    "risk_score",
    "regime_label",
    "reason_codes",
    "residual_load_percentile",
    "renewable_share_percentile",
    "abs_load_ramp_percentile",
    "abs_residual_load_ramp_percentile",
    "abs_renewable_generation_ramp_percentile",
    "risk_schema_version",
]


@dataclass(frozen=True)
class RiskQualityResult:
    status: str
    row_count: int
    required_columns_missing: list[str]
    missing_by_column: dict[str, int]
    regime_counts: dict[str, int]
    max_risk_score: float
    min_risk_score: float
    extreme_without_multiple_reasons: int
    notes: list[str]


def load_feature_frame(path: str | Path) -> pd.DataFrame:
    feature_path = Path(path)

    if not feature_path.exists():
        raise FileNotFoundError(f"Feature file not found: {feature_path}")

    df = pd.read_csv(feature_path)

    missing = [column for column in REQUIRED_FEATURE_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Feature file is missing required risk-engine columns: {missing}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["timestamp_local"] = pd.to_datetime(df["timestamp_local"], utc=True).dt.tz_convert(
        "Europe/Berlin"
    )

    return df.sort_values("timestamp_utc").reset_index(drop=True)


def past_percentile_rank(values: pd.Series, *, min_history: int = 24) -> pd.Series:
    ranks: list[float | None] = []

    for index, value in enumerate(values):
        if pd.isna(value) or index < min_history:
            ranks.append(np.nan)
            continue

        history = values.iloc[:index].dropna()

        if len(history) < min_history:
            ranks.append(np.nan)
            continue

        rank = float((history <= value).mean())
        ranks.append(rank)

    return pd.Series(ranks, index=values.index, dtype="float64")


def build_risk_features(features: pd.DataFrame, *, min_history: int = 24) -> pd.DataFrame:
    df = features.copy()

    df["abs_load_ramp_mw"] = df["load_ramp_mw"].abs()
    df["abs_residual_load_ramp_mw"] = df["residual_load_ramp_mw"].abs()
    df["abs_renewable_generation_ramp_mw"] = df["renewable_generation_ramp_mw"].abs()

    df["residual_load_percentile"] = past_percentile_rank(
        df["residual_load_official_mw"],
        min_history=min_history,
    )

    df["renewable_share_percentile"] = past_percentile_rank(
        df["renewable_share"],
        min_history=min_history,
    )

    df["abs_load_ramp_percentile"] = past_percentile_rank(
        df["abs_load_ramp_mw"],
        min_history=min_history,
    )

    df["abs_residual_load_ramp_percentile"] = past_percentile_rank(
        df["abs_residual_load_ramp_mw"],
        min_history=min_history,
    )

    df["abs_renewable_generation_ramp_percentile"] = past_percentile_rank(
        df["abs_renewable_generation_ramp_mw"],
        min_history=min_history,
    )

    return df


def score_row(row: pd.Series) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    residual_pct = row.get("residual_load_percentile")
    renewable_pct = row.get("renewable_share_percentile")
    load_ramp_pct = row.get("abs_load_ramp_percentile")
    residual_ramp_pct = row.get("abs_residual_load_ramp_percentile")
    renewable_ramp_pct = row.get("abs_renewable_generation_ramp_percentile")

    if pd.notna(residual_pct) and residual_pct >= 0.90:
        score += 30
        reasons.append("HIGH_RESIDUAL_LOAD")

    if pd.notna(renewable_pct) and renewable_pct <= 0.10:
        score += 25
        reasons.append("LOW_RENEWABLE_SHARE")

    if pd.notna(residual_ramp_pct) and residual_ramp_pct >= 0.90:
        score += 20
        reasons.append("HIGH_RESIDUAL_LOAD_RAMP")

    if pd.notna(load_ramp_pct) and load_ramp_pct >= 0.90:
        score += 15
        reasons.append("HIGH_LOAD_RAMP")

    if pd.notna(renewable_ramp_pct) and renewable_ramp_pct >= 0.90:
        score += 10
        reasons.append("HIGH_RENEWABLE_GENERATION_RAMP")

    score = min(score, 100)

    if not reasons:
        reasons.append("NO_RULE_TRIGGERED")

    return score, reasons


def regime_from_score(score: int) -> str:
    if score < 30:
        return "NORMAL"

    if score < 60:
        return "WATCH"

    if score < 85:
        return "STRESSED"

    return "EXTREME"


def build_risk_signals(features: pd.DataFrame, *, min_history: int = 24) -> pd.DataFrame:
    risk_features = build_risk_features(features, min_history=min_history)

    scores: list[int] = []
    reason_codes: list[str] = []

    for _, row in risk_features.iterrows():
        score, reasons = score_row(row)
        scores.append(score)
        reason_codes.append("|".join(reasons))

    risk_features["risk_score"] = scores
    risk_features["regime_label"] = [regime_from_score(score) for score in scores]
    risk_features["reason_codes"] = reason_codes
    risk_features["risk_schema_version"] = RISK_SCHEMA_VERSION

    return risk_features[RISK_OUTPUT_COLUMNS].copy()


def count_extreme_without_multiple_reasons(signals: pd.DataFrame) -> int:
    if signals.empty:
        return 0

    extreme = signals[signals["regime_label"] == "EXTREME"]

    if extreme.empty:
        return 0

    return int(
        extreme["reason_codes"]
        .apply(lambda value: len(str(value).split("|")) < 2)
        .sum()
    )


def validate_risk_signals(signals: pd.DataFrame) -> RiskQualityResult:
    required_columns_missing = [
        column for column in RISK_OUTPUT_COLUMNS if column not in signals.columns
    ]

    critical_columns = [
        "timestamp_utc",
        "market_label",
        "risk_score",
        "regime_label",
        "reason_codes",
    ]

    missing_by_column = {
        column: int(signals[column].isna().sum())
        for column in critical_columns
        if column in signals.columns
    }

    regime_counts = (
        signals["regime_label"].value_counts().sort_index().to_dict()
        if "regime_label" in signals.columns
        else {}
    )

    max_risk_score = float(signals["risk_score"].max()) if "risk_score" in signals.columns else float("nan")
    min_risk_score = float(signals["risk_score"].min()) if "risk_score" in signals.columns else float("nan")

    extreme_without_multiple_reasons = count_extreme_without_multiple_reasons(signals)

    notes: list[str] = []

    if required_columns_missing:
        notes.append(f"Missing risk signal columns: {required_columns_missing}")

    if sum(missing_by_column.values()) > 0:
        notes.append("Missing values found in critical risk signal columns.")

    if min_risk_score < 0 or max_risk_score > 100:
        notes.append("Risk score outside expected 0-100 range.")

    if extreme_without_multiple_reasons > 0:
        notes.append("EXTREME signals found with fewer than two reason codes.")

    if not notes:
        notes.append("Risk signal table passed Phase 4A checks.")

    blocking_issue = (
        bool(required_columns_missing)
        or sum(missing_by_column.values()) > 0
        or min_risk_score < 0
        or max_risk_score > 100
        or extreme_without_multiple_reasons > 0
    )

    status = "STOP — NEEDS VERIFICATION" if blocking_issue else "PASS"

    return RiskQualityResult(
        status=status,
        row_count=int(len(signals)),
        required_columns_missing=required_columns_missing,
        missing_by_column=missing_by_column,
        regime_counts={str(k): int(v) for k, v in regime_counts.items()},
        max_risk_score=max_risk_score,
        min_risk_score=min_risk_score,
        extreme_without_multiple_reasons=extreme_without_multiple_reasons,
        notes=notes,
    )


def render_risk_quality_report(
    result: RiskQualityResult,
    *,
    feature_input: str | Path,
    signal_output: str | Path,
    min_history: int,
) -> str:
    lines = [
        "# Risk Signal Quality Report — Phase 4A",
        "",
        f"- Feature input: `{feature_input}`",
        f"- Risk signal output: `{signal_output}`",
        f"- Status: `{result.status}`",
        f"- Row count: `{result.row_count}`",
        f"- Risk schema version: `{RISK_SCHEMA_VERSION}`",
        f"- Minimum history for percentile logic: `{min_history}`",
        f"- Minimum risk score: `{result.min_risk_score}`",
        f"- Maximum risk score: `{result.max_risk_score}`",
        f"- EXTREME rows with fewer than two reason codes: `{result.extreme_without_multiple_reasons}`",
        "",
        "## Regime Counts",
        "",
    ]

    for regime, count in result.regime_counts.items():
        lines.append(f"- `{regime}`: `{count}`")

    lines.extend(["", "## Required Columns Missing", ""])

    if result.required_columns_missing:
        for column in result.required_columns_missing:
            lines.append(f"- `{column}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Missing Values in Critical Columns", ""])

    for column, count in result.missing_by_column.items():
        lines.append(f"- `{column}`: `{count}`")

    lines.extend(["", "## Notes", ""])

    for note in result.notes:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Methodological Boundary",
            "",
            "This is a rule-based market stress signal layer, not a trading strategy.",
            "",
            "No price data, P&L, execution logic, or backtest is included in Phase 4A.",
            "",
            "Percentile ranks are calculated using past observations only. Early rows with insufficient history receive no percentile-triggered stress reasons.",
            "",
        ]
    )

    return "\n".join(lines)


def build_risk_signal_table(
    *,
    feature_input: str | Path,
    signal_output: str | Path,
    report_output: str | Path,
    metadata_output: str | Path | None = None,
    min_history: int = 24,
) -> pd.DataFrame:
    features = load_feature_frame(feature_input)
    signals = build_risk_signals(features, min_history=min_history)

    quality_result = validate_risk_signals(signals)

    signal_output = Path(signal_output)
    report_output = Path(report_output)

    signal_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)

    signals.to_csv(signal_output, index=False)

    report_output.write_text(
        render_risk_quality_report(
            quality_result,
            feature_input=feature_input,
            signal_output=signal_output,
            min_history=min_history,
        ),
        encoding="utf-8",
    )

    if metadata_output is None:
        metadata_output = signal_output.with_suffix(".metadata.json")

    metadata_output = Path(metadata_output)

    metadata_payload = {
        "stage": "risk_signals",
        "risk_schema_version": RISK_SCHEMA_VERSION,
        "feature_input": str(Path(feature_input).as_posix()),
        "signal_output": str(signal_output.as_posix()),
        "quality_report": str(report_output.as_posix()),
        "min_history": min_history,
        "quality_result": asdict(quality_result),
        "rules": [
            "HIGH_RESIDUAL_LOAD if residual_load_percentile >= 0.90, +30",
            "LOW_RENEWABLE_SHARE if renewable_share_percentile <= 0.10, +25",
            "HIGH_RESIDUAL_LOAD_RAMP if abs_residual_load_ramp_percentile >= 0.90, +20",
            "HIGH_LOAD_RAMP if abs_load_ramp_percentile >= 0.90, +15",
            "HIGH_RENEWABLE_GENERATION_RAMP if abs_renewable_generation_ramp_percentile >= 0.90, +10",
        ],
        "notes": [
            "No price data is included in Phase 4A.",
            "No backtest is included in Phase 4A.",
            "No P&L claim is made in Phase 4A.",
        ],
    }

    metadata_output.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print(f"OK | risk signal rows={len(signals)} | output={signal_output}")
    print(f"OK | risk quality status={quality_result.status} | report={report_output}")

    if quality_result.status == "STOP — NEEDS VERIFICATION":
        raise SystemExit(1)

    return signals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Phase 4A rule-based risk signals.")

    parser.add_argument("--feature-input", required=True)
    parser.add_argument("--signal-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--metadata-output", default=None)
    parser.add_argument("--min-history", type=int, default=24)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    build_risk_signal_table(
        feature_input=args.feature_input,
        signal_output=args.signal_output,
        report_output=args.report_output,
        metadata_output=args.metadata_output,
        min_history=args.min_history,
    )


if __name__ == "__main__":
    main()
