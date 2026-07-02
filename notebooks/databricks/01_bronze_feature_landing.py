# Databricks notebook source

from datetime import datetime, timezone
from pyspark.sql import functions as F

spark.conf.set("spark.sql.session.timeZone", "UTC")

CATALOG = "workspace"
SCHEMA = "power_risk_poc"
VOLUME = "landing"

SOURCE_FILE = "hourly_features_DE-LU_2024-06-01_to_2024-06-03.csv"

SOURCE_PATH = (
    f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/{SOURCE_FILE}"
)

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.bronze_hourly_features"

RUN_ID = datetime.now(timezone.utc).strftime("dbx_%Y%m%dT%H%M%SZ")

# Bronze principle:
# preserve the source representation; do not infer or transform business fields here.
raw_bronze_df = (
    spark.read
    .option("header", True)
    .option("inferSchema", False)
    .csv(SOURCE_PATH)
)

bronze_df = (
    raw_bronze_df
    .withColumn("source_file", F.lit(SOURCE_FILE))
    .withColumn("ingested_at_utc", F.current_timestamp())
    .withColumn("run_id", F.lit(RUN_ID))
)

(
    bronze_df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(BRONZE_TABLE)
)

print(f"OK | Source-faithful Bronze table created: {BRONZE_TABLE}")
print(f"OK | Run ID: {RUN_ID}")
print(f"OK | Rows written: {bronze_df.count()}")

display(
    spark.table(BRONZE_TABLE)
    .select(
        "timestamp_utc",
        "timestamp_local",
        "market_label",
        "total_load_mw",
        "source_file",
        "ingested_at_utc",
        "run_id",
    )
    .orderBy("timestamp_utc")
    .limit(5)
)
