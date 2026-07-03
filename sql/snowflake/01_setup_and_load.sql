-- Snowflake public-data reference setup and raw landing
-- Prerequisite:
-- Upload hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv
-- to POWER_RISK_POC.RAW.STG_HOURLY_FEATURES through Snowsight.

USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS POWER_RISK_POC_WH
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'Compute for DE-LU public-data release-gate POC';

CREATE DATABASE IF NOT EXISTS POWER_RISK_POC
  COMMENT = 'Public-data reference implementation for DE-LU analytical release control';

CREATE SCHEMA IF NOT EXISTS POWER_RISK_POC.RAW
  COMMENT = 'Source-faithful public-data landing tables';

CREATE SCHEMA IF NOT EXISTS POWER_RISK_POC.CONTROL
  COMMENT = 'Quality-check and release-control evidence';

CREATE SCHEMA IF NOT EXISTS POWER_RISK_POC.MART
  COMMENT = 'Consumer-facing release-status objects';

USE WAREHOUSE POWER_RISK_POC_WH;
USE DATABASE POWER_RISK_POC;
USE SCHEMA RAW;

CREATE FILE FORMAT IF NOT EXISTS RAW.FF_HOURLY_FEATURES_CSV
  TYPE = CSV
  FIELD_DELIMITER = ','
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  EMPTY_FIELD_AS_NULL = TRUE
  NULL_IF = ('')
  COMMENT = 'CSV format for public DE-LU hourly feature reference data';

CREATE STAGE IF NOT EXISTS RAW.STG_HOURLY_FEATURES
  FILE_FORMAT = RAW.FF_HOURLY_FEATURES_CSV
  COMMENT = 'Internal stage for public DE-LU feature-dataset reference files';

CREATE TABLE IF NOT EXISTS RAW.HOURLY_FEATURES_LANDING (
  timestamp_utc VARCHAR,
  timestamp_local VARCHAR,
  market_label VARCHAR,
  smard_region VARCHAR,
  total_load_mw VARCHAR,
  residual_load_official_mw VARCHAR,
  wind_onshore_validated_mw VARCHAR,
  solar_validated_mw VARCHAR,
  wind_offshore_validated_mw VARCHAR,
  missing_any_flag VARCHAR,
  wind_total_mw VARCHAR,
  renewable_generation_mw VARCHAR,
  residual_load_calculated_mw VARCHAR,
  residual_gap_mw VARCHAR,
  residual_gap_abs_mw VARCHAR,
  renewable_share VARCHAR,
  wind_share VARCHAR,
  solar_share VARCHAR,
  load_ramp_mw VARCHAR,
  residual_load_ramp_mw VARCHAR,
  renewable_generation_ramp_mw VARCHAR,
  local_date VARCHAR,
  local_hour VARCHAR,
  local_weekday VARCHAR,
  is_weekend VARCHAR,
  feature_schema_version VARCHAR
)
COMMENT = 'Source-faithful public DE-LU hourly feature landing table';

-- Confirm that the CSV has been uploaded through Snowsight.
LIST @POWER_RISK_POC.RAW.STG_HOURLY_FEATURES;

COPY INTO POWER_RISK_POC.RAW.HOURLY_FEATURES_LANDING
FROM @POWER_RISK_POC.RAW.STG_HOURLY_FEATURES
FILES = ('hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv')
ON_ERROR = 'ABORT_STATEMENT';

SELECT
    COUNT(*) AS row_count,
    COUNT(DISTINCT timestamp_utc) AS distinct_timestamp_count,
    MIN(timestamp_utc) AS min_timestamp_utc_raw,
    MAX(timestamp_utc) AS max_timestamp_utc_raw,
    COUNT(DISTINCT market_label) AS market_label_count,
    COUNT(DISTINCT smard_region) AS smard_region_count
FROM POWER_RISK_POC.RAW.HOURLY_FEATURES_LANDING;