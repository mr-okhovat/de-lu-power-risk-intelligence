# Databricks notebook source

from datetime import datetime, timezone
from pyspark.sql import functions as F

spark.conf.set("spark.sql.session.timeZone", "UTC")

CATALOG = "workspace"
SCHEMA = "power_risk_poc"

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.bronze_hourly_features"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.silver_hourly_features"

SILVER_RUN_ID = datetime.now(timezone.utc).strftime("dbx_%Y%m%dT%H%M%SZ")

bronze_df = spark.table(BRONZE_TABLE)

def normalise_boolean(column_name: str):
    value = F.lower(F.trim(F.col(column_name).cast("string")))

    return (
        F.when(value.isin("true", "1", "yes", "y"), F.lit(True))
        .when(value.isin("false", "0", "no", "n"), F.lit(False))
        .otherwise(F.lit(None).cast("boolean"))
    )

silver_df = (
    bronze_df
    .select(
        # Canonical analytical time axis
        F.try_to_timestamp(F.col("timestamp_utc")).alias("timestamp_utc"),

        # Preserve original local representation and UTC offset exactly as supplied
        F.col("timestamp_local").cast("string").alias("timestamp_local"),

        F.col("market_label").cast("string").alias("market_label"),
        F.col("smard_region").cast("string").alias("smard_region"),

        F.col("total_load_mw").cast("double").alias("total_load_mw"),
        F.col("residual_load_official_mw").cast("double").alias("residual_load_official_mw"),
        F.col("wind_onshore_validated_mw").cast("double").alias("wind_onshore_validated_mw"),
        F.col("solar_validated_mw").cast("double").alias("solar_validated_mw"),
        F.col("wind_offshore_validated_mw").cast("double").alias("wind_offshore_validated_mw"),

        normalise_boolean("missing_any_flag").alias("missing_any_flag"),

        F.col("wind_total_mw").cast("double").alias("wind_total_mw"),
        F.col("renewable_generation_mw").cast("double").alias("renewable_generation_mw"),
        F.col("residual_load_calculated_mw").cast("double").alias("residual_load_calculated_mw"),
        F.col("residual_gap_mw").cast("double").alias("residual_gap_mw"),
        F.col("residual_gap_abs_mw").cast("double").alias("residual_gap_abs_mw"),

        F.col("renewable_share").cast("double").alias("renewable_share"),
        F.col("wind_share").cast("double").alias("wind_share"),
        F.col("solar_share").cast("double").alias("solar_share"),

        F.col("load_ramp_mw").cast("double").alias("load_ramp_mw"),
        F.col("residual_load_ramp_mw").cast("double").alias("residual_load_ramp_mw"),
        F.col("renewable_generation_ramp_mw").cast("double").alias("renewable_generation_ramp_mw"),

        F.to_date(F.col("local_date")).alias("local_date"),
        F.col("local_hour").cast("int").alias("local_hour"),
        F.col("local_weekday").cast("string").alias("local_weekday"),
        normalise_boolean("is_weekend").alias("is_weekend"),
        F.col("feature_schema_version").cast("string").alias("feature_schema_version"),

        # Lineage
        F.col("source_file").cast("string").alias("source_file"),
        F.col("ingested_at_utc").alias("bronze_ingested_at_utc"),
        F.col("run_id").cast("string").alias("bronze_ingestion_run_id"),

        # Silver audit metadata
        F.current_timestamp().alias("silver_validated_at_utc"),
        F.lit(SILVER_RUN_ID).alias("silver_validation_run_id"),
    )
)

(
    silver_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(SILVER_TABLE)
)

print(f"OK | Silver table created: {SILVER_TABLE}")
print(f"OK | Silver validation run ID: {SILVER_RUN_ID}")
print(f"OK | Rows written: {silver_df.count()}")

display(
    spark.table(SILVER_TABLE)
    .select(
        "timestamp_utc",
        "timestamp_local",
        "total_load_mw",
        "missing_any_flag",
        "local_date",
        "local_hour",
        "source_file",
        "silver_validation_run_id",
    )
    .orderBy("timestamp_utc")
    .limit(5)
)

# COMMAND ----------

from pathlib import Path
from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

CATALOG = "workspace"
SCHEMA = "power_risk_poc"

SILVER_TABLE = f"{CATALOG}.{SCHEMA}.silver_hourly_features"
QUALITY_TABLE = f"{CATALOG}.{SCHEMA}.silver_quality_check_results"

METADATA_PATH = (
    f"/Volumes/{CATALOG}/{SCHEMA}/landing/"
    "hourly_features_DE-LU_2024-06-01_to_2024-06-03.metadata.json"
)

EXPECTED_MARKET_LABEL = "DE-LU"
EXPECTED_SMARD_REGION = "DE"
RESIDUAL_GAP_TOLERANCE_MW = 1.0

CORE_VALUE_COLUMNS = [
    "total_load_mw",
    "residual_load_official_mw",
    "wind_onshore_validated_mw",
    "solar_validated_mw",
    "wind_offshore_validated_mw",
    "wind_total_mw",
    "renewable_generation_mw",
    "residual_load_calculated_mw",
    "residual_gap_mw",
    "residual_gap_abs_mw",
    "renewable_share",
    "wind_share",
    "solar_share",
]

RAMP_COLUMNS = [
    "load_ramp_mw",
    "residual_load_ramp_mw",
    "renewable_generation_ramp_mw",
]

SHARE_COLUMNS = [
    "renewable_share",
    "wind_share",
    "solar_share",
]

silver_df = spark.table(SILVER_TABLE)

silver_run_id = (
    silver_df
    .select("silver_validation_run_id")
    .limit(1)
    .collect()[0][0]
)

profile = (
    silver_df
    .agg(
        F.count("*").alias("row_count"),
        F.countDistinct("timestamp_utc").alias("distinct_timestamp_count"),
        F.sum(
            F.when(F.col("timestamp_utc").isNull(), 1).otherwise(0)
        ).alias("invalid_timestamp_count"),
        F.min("timestamp_utc").alias("min_timestamp_utc"),
        F.max("timestamp_utc").alias("max_timestamp_utc"),
    )
    .collect()[0]
)

row_count = int(profile["row_count"])
distinct_timestamp_count = int(profile["distinct_timestamp_count"])
invalid_timestamp_count = int(profile["invalid_timestamp_count"] or 0)
duplicate_timestamp_count = row_count - distinct_timestamp_count

if profile["min_timestamp_utc"] and profile["max_timestamp_utc"]:
    expected_hour_count = int(
        (profile["max_timestamp_utc"] - profile["min_timestamp_utc"])
        .total_seconds() / 3600
    ) + 1
else:
    expected_hour_count = 0

valid_time_df = (
    silver_df
    .filter(F.col("timestamp_utc").isNotNull())
    .select("timestamp_utc")
)

time_window = Window.orderBy("timestamp_utc")

hourly_continuity_breaks = (
    valid_time_df
    .withColumn("previous_timestamp_utc", F.lag("timestamp_utc").over(time_window))
    .filter(
        F.col("previous_timestamp_utc").isNotNull()
        & (
            F.unix_timestamp("timestamp_utc")
            - F.unix_timestamp("previous_timestamp_utc")
            != 3600
        )
    )
    .count()
)

missing_exprs = [
    F.sum(F.when(F.col(column).isNull(), 1).otherwise(0)).alias(column)
    for column in CORE_VALUE_COLUMNS
]

core_missing = silver_df.agg(*missing_exprs).collect()[0].asDict()
core_missing = {
    column: int(value or 0)
    for column, value in core_missing.items()
}

flag_true_or_missing_count = (
    silver_df
    .filter(
        F.col("missing_any_flag").isNull()
        | (F.col("missing_any_flag") == F.lit(True))
    )
    .count()
)

ramp_window = Window.orderBy("timestamp_utc")

ramp_ranked_df = (
    silver_df
    .withColumn("row_number_by_time", F.row_number().over(ramp_window))
)

ramp_missing = {}
for column in RAMP_COLUMNS:
    ramp_missing[column] = (
        ramp_ranked_df
        .filter(
            (F.col("row_number_by_time") > 1)
            & F.col(column).isNull()
        )
        .count()
    )

residual_gap_max = (
    silver_df
    .agg(F.max(F.abs(F.col("residual_gap_abs_mw"))).alias("max_gap"))
    .collect()[0]["max_gap"]
)

residual_gap_max = (
    float(residual_gap_max)
    if residual_gap_max is not None
    else None
)

residual_gap_pass = (
    residual_gap_max is not None
    and residual_gap_max <= RESIDUAL_GAP_TOLERANCE_MW
)

share_violations = {}
for column in SHARE_COLUMNS:
    share_violations[column] = (
        silver_df
        .filter(
            F.col(column).isNull()
            | (F.col(column) < 0.0)
            | (F.col(column) > 1.0)
        )
        .count()
    )

market_values = sorted(
    row["market_label"]
    for row in (
        silver_df
        .select("market_label")
        .distinct()
        .collect()
    )
    if row["market_label"] is not None
)

region_values = sorted(
    row["smard_region"]
    for row in (
        silver_df
        .select("smard_region")
        .distinct()
        .collect()
    )
    if row["smard_region"] is not None
)

schema_versions = sorted(
    row["feature_schema_version"]
    for row in (
        silver_df
        .select("feature_schema_version")
        .distinct()
        .collect()
    )
    if row["feature_schema_version"] is not None
)

metadata_payload = (
    spark.read
    .option("multiline", "true")
    .json(METADATA_PATH)
    .collect()[0]
    .asDict(recursive=True)
)

metadata_feature_output = Path(
    metadata_payload.get("feature_output", "")
).name

metadata_quality_result = metadata_payload.get("quality_result", {})

metadata_row_count = metadata_quality_result.get("row_count")
metadata_quality_status = metadata_quality_result.get("status")
metadata_schema_version = metadata_payload.get("feature_schema_version")

metadata_checks = {
    "metadata_feature_output_matches": (
        metadata_feature_output
        == "hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv"
    ),
    "metadata_row_count_matches": metadata_row_count == row_count,
    "metadata_quality_status_pass": metadata_quality_status == "PASS",
    "metadata_schema_version_matches": (
        len(schema_versions) == 1
        and metadata_schema_version == schema_versions[0]
    ),
}

checks = []

def add_check(
    check_name: str,
    category: str,
    observed_value: str,
    expected_value: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(
        (
            silver_run_id,
            check_name,
            category,
            "CRITICAL",
            "PASS" if passed else "FAIL",
            observed_value,
            expected_value,
            detail,
        )
    )

add_check(
    "dataset_not_empty",
    "completeness",
    str(row_count),
    "> 0",
    row_count > 0,
    "Feature dataset must contain at least one row.",
)

add_check(
    "timestamp_parse_validity",
    "timestamp",
    str(invalid_timestamp_count),
    "0 invalid timestamps",
    invalid_timestamp_count == 0,
    "timestamp_utc must parse successfully for every row.",
)

add_check(
    "timestamp_uniqueness",
    "timestamp",
    str(duplicate_timestamp_count),
    "0 duplicate timestamps",
    duplicate_timestamp_count == 0,
    "timestamp_utc is the expected hourly primary key.",
)

add_check(
    "hourly_continuity",
    "timestamp",
    str(hourly_continuity_breaks),
    "0 continuity breaks",
    hourly_continuity_breaks == 0,
    f"Expected hour count from timestamp span: {expected_hour_count}.",
)

for column, count in core_missing.items():
    add_check(
        f"core_nulls::{column}",
        "completeness",
        str(count),
        "0 null values",
        count == 0,
        "Core analytical values must be complete.",
    )

add_check(
    "missing_any_flag",
    "source_quality",
    str(flag_true_or_missing_count),
    "0 true or missing flags",
    flag_true_or_missing_count == 0,
    "No row may carry a source-level missing-data flag.",
)

for column, count in ramp_missing.items():
    add_check(
        f"ramp_nulls_after_first_row::{column}",
        "feature_quality",
        str(count),
        "0 null values after first observation",
        count == 0,
        "The first ramp value may be null by definition; later values may not.",
    )

add_check(
    "residual_gap_tolerance",
    "reconciliation",
    str(residual_gap_max),
    f"<= {RESIDUAL_GAP_TOLERANCE_MW} MW",
    residual_gap_pass,
    "Calculated residual load must reconcile with the official residual load.",
)

for column, count in share_violations.items():
    add_check(
        f"share_range::{column}",
        "plausibility",
        str(count),
        "0 values outside [0, 1]",
        count == 0,
        "Share fields must remain within the inclusive [0, 1] range.",
    )

add_check(
    "market_label_consistency",
    "identity",
    str(market_values),
    str([EXPECTED_MARKET_LABEL]),
    market_values == [EXPECTED_MARKET_LABEL],
    "The dataset must contain exactly one expected market label.",
)

add_check(
    "smard_region_consistency",
    "identity",
    str(region_values),
    str([EXPECTED_SMARD_REGION]),
    region_values == [EXPECTED_SMARD_REGION],
    "The dataset must contain exactly one expected SMARD region.",
)

for check_name, passed in metadata_checks.items():
    add_check(
        check_name,
        "metadata",
        str(passed),
        "True",
        passed,
        "Feature metadata must align with the released analytical dataset.",
    )

quality_schema = T.StructType(
    [
        T.StructField("silver_validation_run_id", T.StringType(), False),
        T.StructField("check_name", T.StringType(), False),
        T.StructField("check_category", T.StringType(), False),
        T.StructField("severity", T.StringType(), False),
        T.StructField("check_status", T.StringType(), False),
        T.StructField("observed_value", T.StringType(), True),
        T.StructField("expected_value", T.StringType(), True),
        T.StructField("detail", T.StringType(), True),
    ]
)

quality_df = (
    spark.createDataFrame(checks, schema=quality_schema)
    .withColumn("checked_at_utc", F.current_timestamp())
)

(
    quality_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(QUALITY_TABLE)
)

print(f"OK | Quality-check table created: {QUALITY_TABLE}")
print(f"OK | Checks recorded: {quality_df.count()}")

display(
    spark.table(QUALITY_TABLE)
    .orderBy("check_category", "check_name")
)
