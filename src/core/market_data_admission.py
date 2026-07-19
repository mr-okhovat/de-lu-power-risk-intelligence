from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


VERSION = "17A.1"


class AdmissionDecision(str, Enum):
    ACCEPT = "ACCEPT"
    ACCEPT_WITH_WARNINGS = "ACCEPT_WITH_WARNINGS"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    observed: Any = None
    threshold: Any = None


@dataclass(frozen=True)
class AdmissionResult:
    version: str
    dataset_id: str
    decision: str
    reliability_score: float
    score_breakdown: dict[str, Any]
    operational_use_allowed: bool
    research_use_allowed: bool
    row_count: int
    expected_rows: int | None
    coverage_ratio: float | None
    invalid_timestamp_rows: int
    duplicate_timestamp_rows: int
    maximum_gap_hours: float | None
    freshness_lag_hours: float | None
    findings: list[dict[str, Any]]


def read_yaml(path: str | Path) -> dict[str, Any]:
    policy_path = Path(path)

    if not policy_path.exists():
        raise FileNotFoundError(
            f"Missing admission policy: {policy_path}"
        )

    data = yaml.safe_load(
        policy_path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            f"Admission policy must be a YAML mapping: {policy_path}"
        )

    return data


def expected_hour_count(
    start_utc: str | pd.Timestamp,
    end_utc: str | pd.Timestamp,
) -> int:
    start = pd.Timestamp(start_utc)
    end = pd.Timestamp(end_utc)

    if start.tzinfo is None:
        start = start.tz_localize("UTC")

    if end.tzinfo is None:
        end = end.tz_localize("UTC")

    if end < start:
        raise ValueError(
            "Expected end must be on or after expected start."
        )

    return int(
        (end - start).total_seconds() // 3600
    ) + 1


def calculate_score_breakdown(
    findings: list[Finding],
    penalties: dict[str, float],
) -> dict[str, Any]:
    starting_score = 100.0
    penalty_entries: list[dict[str, Any]] = []

    for finding in findings:
        penalty = float(
            penalties.get(finding.severity, 0.0)
        )

        penalty_entries.append(
            {
                "finding_code": finding.code,
                "severity": finding.severity,
                "penalty": penalty,
            }
        )

    total_penalty = round(
        sum(
            entry["penalty"]
            for entry in penalty_entries
        ),
        2,
    )

    final_score = round(
        max(
            0.0,
            min(
                100.0,
                starting_score - total_penalty,
            ),
        ),
        2,
    )

    return {
        "starting_score": starting_score,
        "penalties": penalty_entries,
        "total_penalty": total_penalty,
        "final_score": final_score,
    }


def calculate_score(
    findings: list[Finding],
    penalties: dict[str, float],
) -> float:
    return float(
        calculate_score_breakdown(
            findings,
            penalties,
        )["final_score"]
    )

def determine_decision(
    findings: list[Finding],
    reliability_score: float,
    policy: dict[str, Any],
) -> AdmissionDecision:
    severities = {
        finding.severity
        for finding in findings
    }

    if "reject" in severities:
        return AdmissionDecision.REJECT

    if "quarantine" in severities:
        return AdmissionDecision.QUARANTINE

    thresholds = policy.get(
        "decision_thresholds",
        {},
    )

    accept_min_score = float(
        thresholds.get("accept_min_score", 90.0)
    )

    warning_min_score = float(
        thresholds.get("warning_min_score", 70.0)
    )

    if (
        not findings
        and reliability_score >= accept_min_score
    ):
        return AdmissionDecision.ACCEPT

    if reliability_score >= warning_min_score:
        return AdmissionDecision.ACCEPT_WITH_WARNINGS

    return AdmissionDecision.QUARANTINE


def evaluate_dataframe(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    policy: dict[str, Any],
    contract_status: str = "PASS",
    provenance_complete: bool = True,
    expected_start_utc: str | None = None,
    expected_end_utc: str | None = None,
    as_of_utc: str | pd.Timestamp | None = None,
) -> AdmissionResult:
    timestamp_column = str(
        policy.get(
            "timestamp_column",
            "timestamp_utc",
        )
    )

    findings: list[Finding] = []

    if contract_status != "PASS":
        findings.append(
            Finding(
                code="CONTRACT_NOT_PASSED",
                severity="reject",
                message="Dataset contract status is not PASS.",
                observed=contract_status,
                threshold="PASS",
            )
        )

    if frame.empty:
        findings.append(
            Finding(
                code="EMPTY_DATASET",
                severity="reject",
                message="Dataset contains no rows.",
                observed=0,
                threshold="> 0",
            )
        )

    if not provenance_complete:
        findings.append(
            Finding(
                code="PROVENANCE_INCOMPLETE",
                severity="quarantine",
                message="Required provenance metadata is incomplete.",
            )
        )

    if timestamp_column not in frame.columns:
        findings.append(
            Finding(
                code="TIMESTAMP_COLUMN_MISSING",
                severity="reject",
                message=f"Missing timestamp column: {timestamp_column}",
            )
        )

        parsed_timestamps = pd.Series(
            pd.NaT,
            index=frame.index,
            dtype="datetime64[ns, UTC]",
        )

    else:
        parsed_timestamps = pd.to_datetime(
            frame[timestamp_column],
            format="mixed",
            utc=True,
            errors="coerce",
        )

    invalid_timestamp_rows = int(
        parsed_timestamps.isna().sum()
    )

    if invalid_timestamp_rows:
        invalid_severity = (
            "reject"
            if invalid_timestamp_rows == len(frame)
            else "quarantine"
        )

        findings.append(
            Finding(
                code="INVALID_TIMESTAMPS",
                severity=invalid_severity,
                message="One or more timestamps could not be parsed.",
                observed=invalid_timestamp_rows,
                threshold=0,
            )
        )

    valid_timestamps = (
        parsed_timestamps
        .dropna()
        .sort_values()
    )

    duplicate_timestamp_rows = int(
        valid_timestamps
        .duplicated(keep=False)
        .sum()
    )

    duplicate_limit = int(
        policy
        .get("duplicate_timestamp_rows", {})
        .get("quarantine_above", 0)
    )

    if duplicate_timestamp_rows > duplicate_limit:
        findings.append(
            Finding(
                code="DUPLICATE_TIMESTAMPS",
                severity="quarantine",
                message="Duplicate timestamps exceed policy tolerance.",
                observed=duplicate_timestamp_rows,
                threshold=duplicate_limit,
            )
        )

    expected_rows: int | None = None
    coverage_ratio: float | None = None

    if (
        expected_start_utc is not None
        and expected_end_utc is not None
    ):
        expected_start = pd.Timestamp(
            expected_start_utc
        )

        expected_end = pd.Timestamp(
            expected_end_utc
        )

        if expected_start.tzinfo is None:
            expected_start = expected_start.tz_localize(
                "UTC"
            )

        if expected_end.tzinfo is None:
            expected_end = expected_end.tz_localize(
                "UTC"
            )

        expected_rows = expected_hour_count(
            expected_start,
            expected_end,
        )

        in_window = valid_timestamps[
            (valid_timestamps >= expected_start)
            & (valid_timestamps <= expected_end)
        ]

        observed_unique_rows = int(
            in_window.nunique()
        )

        coverage_ratio = round(
            observed_unique_rows / expected_rows,
            6,
        )

        coverage_policy = policy.get(
            "coverage_ratio",
            {},
        )

        quarantine_below = float(
            coverage_policy.get(
                "quarantine_below",
                0.98,
            )
        )

        warn_below = float(
            coverage_policy.get(
                "warn_below",
                0.995,
            )
        )

        if coverage_ratio < quarantine_below:
            findings.append(
                Finding(
                    code="COVERAGE_BELOW_MINIMUM",
                    severity="quarantine",
                    message=(
                        "Temporal coverage is below "
                        "the operational threshold."
                    ),
                    observed=coverage_ratio,
                    threshold=quarantine_below,
                )
            )

        elif coverage_ratio < warn_below:
            findings.append(
                Finding(
                    code="COVERAGE_WARNING",
                    severity="warning",
                    message=(
                        "Temporal coverage is below "
                        "the preferred threshold."
                    ),
                    observed=coverage_ratio,
                    threshold=warn_below,
                )
            )

    maximum_gap_hours: float | None = None

    unique_valid_timestamps = (
        valid_timestamps
        .drop_duplicates()
        .sort_values()
    )

    if len(unique_valid_timestamps) >= 2:
        gaps = (
            unique_valid_timestamps
            .diff()
            .dropna()
            .dt.total_seconds()
            .div(3600)
        )

        maximum_gap_hours = round(
            float(gaps.max()),
            6,
        )

        gap_policy = policy.get(
            "maximum_gap_hours",
            {},
        )

        quarantine_above = float(
            gap_policy.get(
                "quarantine_above",
                6.0,
            )
        )

        warn_above = float(
            gap_policy.get(
                "warn_above",
                2.0,
            )
        )

        if maximum_gap_hours > quarantine_above:
            findings.append(
                Finding(
                    code="MAXIMUM_GAP_EXCEEDED",
                    severity="quarantine",
                    message=(
                        "Maximum timestamp gap exceeds "
                        "the operational threshold."
                    ),
                    observed=maximum_gap_hours,
                    threshold=quarantine_above,
                )
            )

        elif maximum_gap_hours > warn_above:
            findings.append(
                Finding(
                    code="MAXIMUM_GAP_WARNING",
                    severity="warning",
                    message=(
                        "Maximum timestamp gap exceeds "
                        "the preferred threshold."
                    ),
                    observed=maximum_gap_hours,
                    threshold=warn_above,
                )
            )

    freshness_lag_hours: float | None = None

    if (
        as_of_utc is not None
        and not unique_valid_timestamps.empty
    ):
        as_of = pd.Timestamp(as_of_utc)

        if as_of.tzinfo is None:
            as_of = as_of.tz_localize("UTC")

        freshness_lag_hours = round(
            float(
                (
                    as_of
                    - unique_valid_timestamps.max()
                ).total_seconds()
                / 3600
            ),
            6,
        )

        freshness_policy = policy.get(
            "freshness_lag_hours",
            {},
        )

        freshness_quarantine_above = float(
            freshness_policy.get(
                "quarantine_above",
                72.0,
            )
        )

        freshness_warn_above = float(
            freshness_policy.get(
                "warn_above",
                24.0,
            )
        )

        if freshness_lag_hours > freshness_quarantine_above:
            findings.append(
                Finding(
                    code="FRESHNESS_LAG_EXCEEDED",
                    severity="quarantine",
                    message=(
                        "Dataset freshness lag exceeds "
                        "the operational threshold."
                    ),
                    observed=freshness_lag_hours,
                    threshold=freshness_quarantine_above,
                )
            )

        elif freshness_lag_hours > freshness_warn_above:
            findings.append(
                Finding(
                    code="FRESHNESS_LAG_WARNING",
                    severity="warning",
                    message=(
                        "Dataset freshness lag exceeds "
                        "the preferred threshold."
                    ),
                    observed=freshness_lag_hours,
                    threshold=freshness_warn_above,
                )
            )

    penalties = {
        str(key): float(value)
        for key, value in policy.get(
            "score_penalties",
            {},
        ).items()
    }

    score_breakdown = calculate_score_breakdown(
        findings,
        penalties,
    )

    reliability_score = float(
        score_breakdown["final_score"]
    )

    decision = determine_decision(
        findings,
        reliability_score,
        policy,
    )

    operational_use_allowed = decision in {
        AdmissionDecision.ACCEPT,
        AdmissionDecision.ACCEPT_WITH_WARNINGS,
    }

    research_use_allowed = decision != AdmissionDecision.REJECT

    return AdmissionResult(
        version=VERSION,
        dataset_id=dataset_id,
        decision=decision.value,
        reliability_score=reliability_score,
        score_breakdown=score_breakdown,
        operational_use_allowed=operational_use_allowed,
        research_use_allowed=research_use_allowed,
        row_count=int(len(frame)),
        expected_rows=expected_rows,
        coverage_ratio=coverage_ratio,
        invalid_timestamp_rows=invalid_timestamp_rows,
        duplicate_timestamp_rows=duplicate_timestamp_rows,
        maximum_gap_hours=maximum_gap_hours,
        freshness_lag_hours=freshness_lag_hours,
        findings=[
            asdict(finding)
            for finding in findings
        ],
    )
