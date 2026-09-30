
from __future__ import annotations

import json
import os
import sys

from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = os.environ.get("RAW_TOPIC", "weather.raw.posts")
CHECKPOINT = os.environ.get(
    "SPARK_CHECKPOINT", "/tmp/spark/checkpoints/stream_ingest"
)
TRIGGER_SECONDS = os.environ.get("TRIGGER_SECONDS", "10")
START_OFFSETS = os.environ.get("STARTING_OFFSETS", "earliest")
DEFAULT_PG_URL = "postgresql+psycopg2://vaayu:vaayu@postgres:5432/vaayu"

RAW_SCHEMA = StructType(
    [
        StructField("source", StringType()),
        StructField("external_id", StringType()),
        StructField("text", StringType()),
        StructField("source_url", StringType()),
        StructField("author", StringType()),
        StructField("observed_at", TimestampType()),
        StructField("hashtags", ArrayType(StringType())),
        StructField("lat", DoubleType()),
        StructField("lon", DoubleType()),
        StructField("city_hint", StringType()),
        StructField("state_hint", StringType()),
        StructField("media_urls", ArrayType(StringType())),
        StructField("lang", StringType()),
        StructField("raw", StringType()),
    ]
)


def pg_dsn() -> str:
    return os.environ.get("DATABASE_URL_SYNC", DEFAULT_PG_URL).replace("+psycopg2", "")


def write_batch(batch_df, batch_id: int, dsn: str) -> None:
    import psycopg2
    from psycopg2.extras import Json

    rows = [r.asDict(recursive=True) for r in batch_df.toLocalIterator()]
    if not rows:
        return
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC'")
            insert_sql = (
                "INSERT INTO reports (id, source, external_id, text, source_url, author, "
                "observed_at, hashtags, lat, lon, raw, verification_status, is_duplicate) "
                "VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "'pending', false) "
                "ON CONFLICT (source, external_id) DO NOTHING"
            )
            for r in rows:
                raw_val = r.get("raw")
                if isinstance(raw_val, str):
                    try:
                        raw = json.loads(raw_val) or {}
                    except ValueError:
                        raw = {"_unparsed": raw_val[:1000]}
                elif isinstance(raw_val, dict):
                    raw = raw_val
                else:
                    raw = {}
                if r.get("city_hint"):
                    raw["city_hint"] = r["city_hint"]
                if r.get("state_hint"):
                    raw["state_hint"] = r["state_hint"]
                cur.execute(
                    insert_sql,
                    (
                        r.get("source"),
                        r.get("external_id"),
                        r.get("text"),
                        r.get("source_url"),
                        r.get("author"),
                        r.get("observed_at"),
                        r.get("hashtags") or [],
                        r.get("lat"),
                        r.get("lon"),
                        Json(raw),
                    ),
                )
            cur.execute("SELECT count(*) FROM reports")
        conn.commit()
        print(f"[stream_ingest] batch={batch_id} rows={len(rows)}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    spark = (
        SparkSession.builder.appName("vaayudrishti-stream-ingest")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    dsn = pg_dsn()

    stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", START_OFFSETS)
        .option("failOnDataLoss", "false")
        .load()
        .selectExpr("CAST(value AS STRING) AS json")
        .select(F.from_json("json", RAW_SCHEMA).alias("d"))
        .select("d.*")
        .filter(F.col("source").isNotNull() & F.col("external_id").isNotNull())
        .filter(F.col("text").isNotNull())
    )

    query = (
        stream.writeStream.foreachBatch(lambda df, bid: write_batch(df, bid, dsn))
        .option("checkpointLocation", CHECKPOINT)
        .trigger(processingTime=f"{TRIGGER_SECONDS} seconds")
        .start()
    )
    query.awaitTermination()
    return 0


if __name__ == "__main__":
    sys.exit(main())
