-- Snowflake analytical dataset release gate
-- Public-data reference implementation for DE-LU hourly feature data.

USE WAREHOUSE POWER_RISK_POC_WH;
USE DATABASE POWER_RISK_POC;
USE SCHEMA CONTROL;

CREATE TABLE IF NOT EXISTS RELEASE_CHECK_RESULTS (
    release_run_id VARCHAR,
    source_file VARCHAR,
    check_name VARCHAR,
    check_category VARCHAR,
    severity VARCHAR,
    check_status VARCHAR,
    observed_value VARCHAR,
    expected_value VARCHAR,
    detail VARCHAR,
    checked_at_utc TIMESTAMP_TZ
);

-- Canonical typed analytical layer.
CREATE OR REPLACE TABLE POWER_RISK_POC.CONTROL.HOURLY_FEATURES_TYPED AS
SELECT
    TRY_TO_TIMESTAMP_TZ(timestamp_utc) AS timestamp_utc,
    timestamp_local AS timestamp_local_raw,
    TRY_TO_TIMESTAMP_TZ(timestamp_local) AS timestamp_local_tz,

    market_label,
    smard_region,

    TRY_TO_DOUBLE(total_load_mw) AS total_load_mw,
    TRY_TO_DOUBLE(residual_load_official_mw) AS residual_load_official_mw,
    TRY_TO_DOUBLE(wind_onshore_validated_mw) AS wind_onshore_validated_mw,
    TRY_TO_DOUBLE(solar_validated_mw) AS solar_validated_mw,
    TRY_TO_DOUBLE(wind_offshore_validated_mw) AS wind_offshore_validated_mw,

    TRY_TO_BOOLEAN(missing_any_flag) AS missing_any_flag,

    TRY_TO_DOUBLE(wind_total_mw) AS wind_total_mw,
    TRY_TO_DOUBLE(renewable_generation_mw) AS renewable_generation_mw,
    TRY_TO_DOUBLE(residual_load_calculated_mw) AS residual_load_calculated_mw,
    TRY_TO_DOUBLE(residual_gap_mw) AS residual_gap_mw,
    TRY_TO_DOUBLE(residual_gap_abs_mw) AS residual_gap_abs_mw,

    TRY_TO_DOUBLE(renewable_share) AS renewable_share,
    TRY_TO_DOUBLE(wind_share) AS wind_share,
    TRY_TO_DOUBLE(solar_share) AS solar_share,

    TRY_TO_DOUBLE(load_ramp_mw) AS load_ramp_mw,
    TRY_TO_DOUBLE(residual_load_ramp_mw) AS residual_load_ramp_mw,
    TRY_TO_DOUBLE(renewable_generation_ramp_mw) AS renewable_generation_ramp_mw,

    TRY_TO_DATE(local_date) AS local_date,
    TRY_TO_NUMBER(local_hour) AS local_hour,
    local_weekday,
    TRY_TO_BOOLEAN(is_weekend) AS is_weekend,
    feature_schema_version,

    'hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv' AS source_file,
    CURRENT_TIMESTAMP() AS typed_at_utc

FROM POWER_RISK_POC.RAW.HOURLY_FEATURES_LANDING;

-- Each execution receives an auditable release-run identifier.
SET RELEASE_RUN_ID = (SELECT UUID_STRING());

-- Computes release metrics from the typed analytical dataset.
CREATE OR REPLACE VIEW POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS AS
WITH ordered AS (
    SELECT
        *,
        LAG(timestamp_utc) OVER (
            ORDER BY timestamp_utc
        ) AS previous_timestamp_utc,
        ROW_NUMBER() OVER (
            ORDER BY timestamp_utc
        ) AS row_number_by_time
    FROM POWER_RISK_POC.CONTROL.HOURLY_FEATURES_TYPED
)
SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT timestamp_utc) AS distinct_timestamp_count,

    COUNT_IF(timestamp_utc IS NULL) AS invalid_timestamp_count,

    COUNT_IF(
        previous_timestamp_utc IS NOT NULL
        AND DATEDIFF(
            'hour',
            previous_timestamp_utc,
            timestamp_utc
        ) <> 1
    ) AS hourly_continuity_break_count,

    COUNT_IF(
        total_load_mw IS NULL
        OR residual_load_official_mw IS NULL
        OR wind_onshore_validated_mw IS NULL
        OR solar_validated_mw IS NULL
        OR wind_offshore_validated_mw IS NULL
        OR wind_total_mw IS NULL
        OR renewable_generation_mw IS NULL
        OR residual_load_calculated_mw IS NULL
        OR residual_gap_mw IS NULL
        OR residual_gap_abs_mw IS NULL
        OR renewable_share IS NULL
        OR wind_share IS NULL
        OR solar_share IS NULL
    ) AS core_null_row_count,

    COUNT_IF(
        missing_any_flag IS NULL
        OR missing_any_flag = TRUE
    ) AS missing_flag_issue_count,

    COUNT_IF(
        row_number_by_time > 1
        AND (
            load_ramp_mw IS NULL
            OR residual_load_ramp_mw IS NULL
            OR renewable_generation_ramp_mw IS NULL
        )
    ) AS ramp_missing_after_first_row_count,

    MAX(ABS(residual_gap_abs_mw)) AS residual_gap_max_abs_mw,

    COUNT_IF(
        renewable_share IS NULL
        OR wind_share IS NULL
        OR solar_share IS NULL
        OR renewable_share < 0 OR renewable_share > 1
        OR wind_share < 0 OR wind_share > 1
        OR solar_share < 0 OR solar_share > 1
    ) AS share_range_violation_row_count,

    COUNT(DISTINCT market_label) AS market_label_count,
    MIN(market_label) AS market_label_value,

    COUNT(DISTINCT smard_region) AS smard_region_count,
    MIN(smard_region) AS smard_region_value,

    COUNT(DISTINCT feature_schema_version) AS schema_version_count,
    MIN(feature_schema_version) AS schema_version_value,

    MAX(source_file) AS source_file
FROM ordered;

-- Persists the twelve critical check outcomes for this release run.
INSERT INTO POWER_RISK_POC.CONTROL.RELEASE_CHECK_RESULTS (
    release_run_id,
    source_file,
    check_name,
    check_category,
    severity,
    check_status,
    observed_value,
    expected_value,
    detail,
    checked_at_utc
)

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'dataset_not_empty',
    'completeness',
    'CRITICAL',
    IFF(row_count > 0, 'PASS', 'FAIL'),
    TO_VARCHAR(row_count),
    '> 0',
    'Feature dataset must contain at least one row.',
    CURRENT_TIMESTAMP()
FROM POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS

UNION ALL

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'timestamp_parse_validity',
    'timestamp',
    'CRITICAL',
    IFF(invalid_timestamp_count = 0, 'PASS', 'FAIL'),
    TO_VARCHAR(invalid_timestamp_count),
    '0 invalid timestamps',
    'Every timestamp_utc value must parse successfully.',
    CURRENT_TIMESTAMP()
FROM POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS

UNION ALL

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'timestamp_uniqueness',
    'timestamp',
    'CRITICAL',
    IFF(row_count = distinct_timestamp_count, 'PASS', 'FAIL'),
    'rows=' || TO_VARCHAR(row_count)
        || ', distinct=' || TO_VARCHAR(distinct_timestamp_count),
    'rows = distinct timestamps',
    'timestamp_utc is the hourly primary key.',
    CURRENT_TIMESTAMP()
FROM POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS

UNION ALL

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'hourly_continuity',
    'timestamp',
    'CRITICAL',
    IFF(hourly_continuity_break_count = 0, 'PASS', 'FAIL'),
    TO_VARCHAR(hourly_continuity_break_count),
    '0 continuity breaks',
    'The canonical UTC time axis must be hourly continuous.',
    CURRENT_TIMESTAMP()
FROM POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS

UNION ALL

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'core_analytical_completeness',
    'completeness',
    'CRITICAL',
    IFF(core_null_row_count = 0, 'PASS', 'FAIL'),
    TO_VARCHAR(core_null_row_count),
    '0 rows with core analytical nulls',
    'Core load, renewable, residual and share fields must be complete.',
    CURRENT_TIMESTAMP()
FROM POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS

UNION ALL

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'missing_any_flag',
    'source_quality',
    'CRITICAL',
    IFF(missing_flag_issue_count = 0, 'PASS', 'FAIL'),
    TO_VARCHAR(missing_flag_issue_count),
    '0 true or missing flags',
    'No source-level missing-data flag may remain in a released dataset.',
    CURRENT_TIMESTAMP()
FROM POWER_RISK_POC.CONTROL.V_RELEASE_GATE_METRICS

UNION ALL

SELECT
    TO_VARCHAR($RELEASE_RUN_ID),
    source_file,
    'ramp_completeness_after_first_row',
    'feature_quality',
    'CRITICAL',
    IFF(ramp_missing_after_first_row_count = 0, 'PASS', 'FAIL'),
    TO_VARCHAR(ramp_missing_after_first_row_count),
    '0 missing ramp values after first row',
    'The first ramp may be null by definition;

-- Consumer-facing READY / BLOCKED decision.
CREATE OR REPLACE VIEW POWER_RISK_POC.MART.V_RELEASE_STATUS AS
WITH release_summary AS (
    SELECT
        release_run_id,
        MAX(source_file) AS source_file,
        COUNT(*) AS check_count,
        COALESCE(
            COUNT_IF(check_status = 'FAIL'),
            0
        ) AS failed_check_count,
        COALESCE(
            COUNT_IF(
                severity = 'CRITICAL'
                AND check_status = 'FAIL'
            ),
            0
        ) AS critical_failed_check_count,
        MAX(checked_at_utc) AS quality_checked_at_utc
    FROM POWER_RISK_POC.CONTROL.RELEASE_CHECK_RESULTS
    GROUP BY release_run_id
)

SELECT
    release_run_id,
    source_file,
    check_count,
    failed_check_count,
    critical_failed_check_count,
    quality_checked_at_utc,

    IFF(
        critical_failed_check_count = 0,
        'READY',
        'BLOCKED'
    ) AS release_status,

    IFF(
        critical_failed_check_count = 0,
        'All critical release checks passed. Dataset may feed downstream analytics.',
        'One or more critical checks failed. Consult CONTROL.RELEASE_CHECK_RESULTS for check-level evidence.'
    ) AS release_reason,

    'snowflake_release_gate_v1' AS release_policy_version

FROM release_summary;

-- Final release decision for the current run.
SELECT
    release_run_id,
    source_file,
    check_count,
    failed_check_count,
    critical_failed_check_count,
    release_status,
    release_reason,
    quality_checked_at_utc
FROM POWER_RISK_POC.MART.V_RELEASE_STATUS
WHERE release_run_id = $RELEASE_RUN_ID;

