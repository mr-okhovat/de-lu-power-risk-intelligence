-- Phase 3B SQL schema contract
-- Table: power_market_features
-- Purpose: SQL/Power BI-ready feature table for DE-LU public-data analytics.
-- This schema is a contract, not a database migration yet.

CREATE TABLE IF NOT EXISTS power_market_features (
    timestamp_utc TIMESTAMP PRIMARY KEY,
    timestamp_local TIMESTAMP,
    market_label TEXT NOT NULL,
    smard_region TEXT NOT NULL,
    total_load_mw DOUBLE PRECISION,
    residual_load_official_mw DOUBLE PRECISION,
    wind_onshore_validated_mw DOUBLE PRECISION,
    wind_offshore_validated_mw DOUBLE PRECISION,
    solar_validated_mw DOUBLE PRECISION,
    wind_total_mw DOUBLE PRECISION,
    renewable_generation_mw DOUBLE PRECISION,
    renewable_share DOUBLE PRECISION,
    wind_share DOUBLE PRECISION,
    solar_share DOUBLE PRECISION,
    load_ramp_mw DOUBLE PRECISION,
    residual_load_ramp_mw DOUBLE PRECISION,
    renewable_generation_ramp_mw DOUBLE PRECISION,
    local_date DATE,
    local_hour INTEGER,
    local_weekday TEXT,
    is_weekend BOOLEAN,
    feature_schema_version TEXT,
    dashboard_schema_version TEXT
);

CREATE INDEX IF NOT EXISTS idx_power_market_features_market_time
ON power_market_features (market_label, timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_power_market_features_local_date
ON power_market_features (local_date);
