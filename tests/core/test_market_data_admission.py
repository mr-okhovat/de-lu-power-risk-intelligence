import pandas as pd

from src.core.market_data_admission import (
    AdmissionDecision,
    evaluate_dataframe,
    read_yaml,
)


POLICY_PATH = (
    "src/config/admission_policies/"
    "hourly_market_dataset.yaml"
)


def test_accepts_complete_hourly_dataset() -> None:
    policy = read_yaml(POLICY_PATH)

    frame = pd.DataFrame(
        {
            "timestamp_utc": pd.date_range(
                "2024-01-01 00:00",
                periods=24,
                freq="h",
                tz="UTC",
            )
        }
    )

    result = evaluate_dataframe(
        frame,
        dataset_id="healthy_dataset",
        policy=policy,
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-01 23:00",
        as_of_utc="2024-01-02 00:00",
    )

    assert result.decision == AdmissionDecision.ACCEPT.value
    assert result.reliability_score == 100.0
    assert result.operational_use_allowed is True
    assert result.research_use_allowed is True
    assert result.findings == []

def test_quarantines_low_quality_dataset() -> None:
    policy = read_yaml(POLICY_PATH)

    frame = pd.DataFrame(
        {
            "timestamp_utc": [
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 01:00:00+00:00",
                "2024-01-01 01:00:00+00:00",
                "2024-01-01 10:00:00+00:00",
            ]
        }
    )

    result = evaluate_dataframe(
        frame,
        dataset_id="low_quality_dataset",
        policy=policy,
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-01 23:00",
        as_of_utc="2024-01-05 00:00",
    )

    finding_codes = {
        finding["code"]
        for finding in result.findings
    }

    assert result.decision == AdmissionDecision.QUARANTINE.value
    assert result.operational_use_allowed is False
    assert result.research_use_allowed is True
    assert result.reliability_score == 0.0
    assert "DUPLICATE_TIMESTAMPS" in finding_codes
    assert "COVERAGE_BELOW_MINIMUM" in finding_codes
    assert "MAXIMUM_GAP_EXCEEDED" in finding_codes
    assert "FRESHNESS_LAG_EXCEEDED" in finding_codes


def test_rejects_failed_contract_and_empty_dataset() -> None:
    policy = read_yaml(POLICY_PATH)

    frame = pd.DataFrame()

    result = evaluate_dataframe(
        frame,
        dataset_id="rejected_dataset",
        policy=policy,
        contract_status="FAIL",
        provenance_complete=False,
    )

    finding_codes = {
        finding["code"]
        for finding in result.findings
    }

    assert result.decision == AdmissionDecision.REJECT.value
    assert result.operational_use_allowed is False
    assert result.research_use_allowed is False
    assert result.reliability_score == 0.0
    assert "CONTRACT_NOT_PASSED" in finding_codes
    assert "EMPTY_DATASET" in finding_codes
    assert "PROVENANCE_INCOMPLETE" in finding_codes
    assert "TIMESTAMP_COLUMN_MISSING" in finding_codes


def test_accepts_dataset_with_warnings() -> None:
    policy = read_yaml(POLICY_PATH)

    timestamps = pd.date_range(
        "2024-01-01 00:00",
        periods=240,
        freq="h",
        tz="UTC",
    ).delete([50, 150])

    frame = pd.DataFrame(
        {"timestamp_utc": timestamps}
    )

    result = evaluate_dataframe(
        frame,
        dataset_id="warning_dataset",
        policy=policy,
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-10 23:00",
        as_of_utc="2024-01-11 00:00",
    )

    finding_codes = {
        finding["code"]
        for finding in result.findings
    }

    assert result.decision == (
        AdmissionDecision.ACCEPT_WITH_WARNINGS.value
    )
    assert result.operational_use_allowed is True
    assert result.research_use_allowed is True
    assert result.reliability_score == 95.0
    assert result.coverage_ratio == 0.991667
    assert "COVERAGE_WARNING" in finding_codes


def test_quarantines_partially_invalid_timestamps() -> None:
    policy = read_yaml(POLICY_PATH)

    frame = pd.DataFrame(
        {
            "timestamp_utc": [
                "2024-01-01 00:00:00+00:00",
                "invalid-timestamp",
                "2024-01-01 02:00:00+00:00",
            ]
        }
    )

    result = evaluate_dataframe(
        frame,
        dataset_id="invalid_timestamp_dataset",
        policy=policy,
    )

    finding_codes = {
        finding["code"]
        for finding in result.findings
    }

    assert result.decision == AdmissionDecision.QUARANTINE.value
    assert result.invalid_timestamp_rows == 1
    assert result.operational_use_allowed is False
    assert result.research_use_allowed is True
    assert "INVALID_TIMESTAMPS" in finding_codes


def test_rejects_dataset_when_all_timestamps_are_invalid() -> None:
    policy = read_yaml(POLICY_PATH)

    frame = pd.DataFrame(
        {
            "timestamp_utc": [
                "invalid-a",
                "invalid-b",
            ]
        }
    )

    result = evaluate_dataframe(
        frame,
        dataset_id="all_invalid_timestamps",
        policy=policy,
    )

    finding_codes = {
        finding["code"]
        for finding in result.findings
    }

    assert result.decision == AdmissionDecision.REJECT.value
    assert result.invalid_timestamp_rows == 2
    assert result.operational_use_allowed is False
    assert result.research_use_allowed is False
    assert "INVALID_TIMESTAMPS" in finding_codes


def test_score_breakdown_explains_each_penalty() -> None:
    from src.core.market_data_admission import (
        Finding,
        calculate_score_breakdown,
    )

    findings = [
        Finding(
            code="COVERAGE_WARNING",
            severity="warning",
            message="Coverage is below the preferred threshold.",
        ),
        Finding(
            code="DUPLICATE_TIMESTAMPS",
            severity="quarantine",
            message="Duplicate timestamps exceed tolerance.",
        ),
    ]

    breakdown = calculate_score_breakdown(
        findings,
        {
            "warning": 5,
            "quarantine": 25,
            "reject": 100,
        },
    )

    assert breakdown == {
        "starting_score": 100.0,
        "penalties": [
            {
                "finding_code": "COVERAGE_WARNING",
                "severity": "warning",
                "penalty": 5.0,
            },
            {
                "finding_code": "DUPLICATE_TIMESTAMPS",
                "severity": "quarantine",
                "penalty": 25.0,
            },
        ],
        "total_penalty": 30.0,
        "final_score": 70.0,
    }


def test_admission_result_contains_score_breakdown() -> None:
    policy = read_yaml(POLICY_PATH)

    timestamps = pd.date_range(
        "2024-01-01 00:00",
        periods=240,
        freq="h",
        tz="UTC",
    ).delete([50, 150])

    result = evaluate_dataframe(
        pd.DataFrame(
            {"timestamp_utc": timestamps}
        ),
        dataset_id="score_breakdown_dataset",
        policy=policy,
        expected_start_utc="2024-01-01 00:00",
        expected_end_utc="2024-01-10 23:00",
        as_of_utc="2024-01-11 00:00",
    )

    assert result.reliability_score == 95.0
    assert result.score_breakdown["starting_score"] == 100.0
    assert result.score_breakdown["total_penalty"] == 5.0
    assert result.score_breakdown["final_score"] == 95.0
    assert result.score_breakdown["penalties"] == [
        {
            "finding_code": "COVERAGE_WARNING",
            "severity": "warning",
            "penalty": 5.0,
        }
    ]
