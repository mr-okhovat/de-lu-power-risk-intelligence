# Databricks notebook source

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "power_risk_poc"

SILVER_TABLE = f"{CATALOG}.{SCHEMA}.silver_hourly_features"
QUALITY_TABLE = f"{CATALOG}.{SCHEMA}.silver_quality_check_results"
GOLD_TABLE = f"{CATALOG}.{SCHEMA}.gold_release_status"

silver_profile = (
    spark.table(SILVER_TABLE)
    .groupBy(
        "silver_validation_run_id",
        "source_file",
    )
    .agg(
        F.count("*").alias("row_count"),
        F.countDistinct("timestamp_utc").alias("distinct_timestamp_count"),
        F.min("timestamp_utc").alias("period_start_utc"),
        F.max("timestamp_utc").alias("period_end_utc"),
        F.first("market_label").alias("market_label"),
        F.first("smard_region").alias("smard_region"),
        F.first("feature_schema_version").alias("feature_schema_version"),
    )
)

quality_summary = (
    spark.table(QUALITY_TABLE)
    .groupBy("silver_validation_run_id")
    .agg(
        F.count("*").alias("check_count"),
        F.sum(
            F.when(F.col("check_status") == "FAIL", 1).otherwise(0)
        ).cast("int").alias("failed_check_count"),
        F.sum(
            F.when(
                (F.col("severity") == "CRITICAL")
                & (F.col("check_status") == "FAIL"),
                1,
            ).otherwise(0)
        ).cast("int").alias("critical_failed_check_count"),
        F.collect_list(
            F.when(
                F.col("check_status") == "FAIL",
                F.concat_ws(": ", F.col("check_name"), F.col("detail")),
            )
        ).alias("failed_check_details"),
        F.max("checked_at_utc").alias("quality_checked_at_utc"),
    )
    .withColumn(
        "failed_check_details",
        F.expr("filter(failed_check_details, x -> x is not null)")
    )
)

gold_df = (
    silver_profile
    .join(quality_summary, on="silver_validation_run_id", how="inner")
    .withColumn(
        "release_status",
        F.when(
            F.col("failed_check_count") == 0,
            F.lit("READY"),
        ).otherwise(F.lit("BLOCKED"))
    )
    .withColumn(
        "release_reason",
        F.when(
            F.col("failed_check_count") == 0,
            F.lit(
                "All release-gate checks passed. "
                "Dataset may feed downstream analytics."
            ),
        ).otherwise(
            F.concat_ws("; ", F.col("failed_check_details"))
        )
    )
    .withColumn(
        "release_policy_version",
        F.lit("analytical_dataset_release_gate_v1")
    )
    .withColumn(
        "released_at_utc",
        F.current_timestamp()
    )
    .select(
        "silver_validation_run_id",
        "source_file",
        "market_label",
        "smard_region",
        "feature_schema_version",
        "period_start_utc",
        "period_end_utc",
        "row_count",
        "distinct_timestamp_count",
        "check_count",
        "failed_check_count",
        "critical_failed_check_count",
        "quality_checked_at_utc",
        "release_status",
        "release_reason",
        "release_policy_version",
        "released_at_utc",
    )
)

(
    gold_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(GOLD_TABLE)
)

print(f"OK | Gold release table created: {GOLD_TABLE}")

display(
    spark.table(GOLD_TABLE)
    .orderBy(F.desc("released_at_utc"))
)

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "workspace"
SCHEMA = "power_risk_poc"

SILVER_TABLE = f"{CATALOG}.{SCHEMA}.silver_hourly_features"
QUALITY_TABLE = f"{CATALOG}.{SCHEMA}.silver_quality_check_results"
GOLD_TABLE = f"{CATALOG}.{SCHEMA}.gold_release_status"

silver_profile = (
    spark.table(SILVER_TABLE)
    .groupBy(
        "silver_validation_run_id",
        "source_file",
    )
    .agg(
        F.count("*").alias("row_count"),
        F.countDistinct("timestamp_utc").alias("distinct_timestamp_count"),
        F.min("timestamp_utc").alias("period_start_utc"),
        F.max("timestamp_utc").alias("period_end_utc"),
        F.first("market_label").alias("market_label"),
        F.first("smard_region").alias("smard_region"),
        F.first("feature_schema_version").alias("feature_schema_version"),
    )
)

quality_summary = (
    spark.table(QUALITY_TABLE)
    .groupBy("silver_validation_run_id")
    .agg(
        F.count("*").alias("check_count"),
        F.sum(
            F.when(F.col("check_status") == "FAIL", 1).otherwise(0)
        ).cast("int").alias("failed_check_count"),
        F.sum(
            F.when(
                (F.col("severity") == "CRITICAL")
                & (F.col("check_status") == "FAIL"),
                1,
            ).otherwise(0)
        ).cast("int").alias("critical_failed_check_count"),
        F.collect_list(
            F.when(
                F.col("check_status") == "FAIL",
                F.concat_ws(": ", F.col("check_name"), F.col("detail")),
            )
        ).alias("failed_check_details"),
        F.max("checked_at_utc").alias("quality_checked_at_utc"),
    )
    .withColumn(
        "failed_check_details",
        F.expr("filter(failed_check_details, x -> x is not null)")
    )
)

gold_df = (
    silver_profile
    .join(quality_summary, on="silver_validation_run_id", how="inner")
    .withColumn(
        "release_status",
        F.when(
            F.col("failed_check_count") == 0,
            F.lit("READY"),
        ).otherwise(F.lit("BLOCKED"))
    )
    .withColumn(
        "release_reason",
        F.when(
            F.col("failed_check_count") == 0,
            F.lit(
                "All release-gate checks passed. "
                "Dataset may feed downstream analytics."
            ),
        ).otherwise(
            F.concat_ws("; ", F.col("failed_check_details"))
        )
    )
    .withColumn(
        "release_policy_version",
        F.lit("analytical_dataset_release_gate_v1")
    )
    .withColumn(
        "released_at_utc",
        F.current_timestamp()
    )
    .select(
        "silver_validation_run_id",
        "source_file",
        "market_label",
        "smard_region",
        "feature_schema_version",
        "period_start_utc",
        "period_end_utc",
        "row_count",
        "distinct_timestamp_count",
        "check_count",
        "failed_check_count",
        "critical_failed_check_count",
        "quality_checked_at_utc",
        "release_status",
        "release_reason",
        "release_policy_version",
        "released_at_utc",
    )
)

(
    gold_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(GOLD_TABLE)
)

print(f"OK | Gold release table created: {GOLD_TABLE}")

display(
    spark.table(GOLD_TABLE)
    .orderBy(F.desc("released_at_utc"))
)
