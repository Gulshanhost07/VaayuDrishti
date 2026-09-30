
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from pyspark.sql import SparkSession, functions as F

DEFAULT_URL = "postgresql+psycopg2://vaayu:vaayu@postgres:5432/vaayu"


def pg_url() -> str:
    return os.environ.get("DATABASE_URL_SYNC", DEFAULT_URL).replace("+psycopg2", "")


def jdbc_parts(url: str) -> tuple[str, str, str, str, str, str]:
    parsed = urlparse(url)
    user = parsed.username or "vaayu"
    password = parsed.password or "vaayu"
    host = parsed.hostname or "postgres"
    port = parsed.port or 5432
    database = (parsed.path or "/vaayu").lstrip("/")
    jdbc = f"jdbc:postgresql://{host}:{port}/{database}"
    return jdbc, user, password, host, str(port), database


def upsert(cur, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = (
        "bucket_start",
        "state",
        "event_category",
        "source",
        "report_count",
        "verified_count",
        "duplicate_count",
        "avg_credibility",
    )
    conflict = "(bucket_start, state, event_category, source)"
    updates = (
        "report_count = EXCLUDED.report_count, "
        "verified_count = EXCLUDED.verified_count, "
        "duplicate_count = EXCLUDED.duplicate_count, "
        "avg_credibility = EXCLUDED.avg_credibility, "
        "computed_at = now()"
    )
    sql = (
        f"INSERT INTO {table} ({', '.join(cols)}, computed_at) "
        f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now()) "
        f"ON CONFLICT {conflict} DO UPDATE SET {updates}"
    )
    for r in rows:
        cur.execute(
            sql,
            (
                r["bucket_start"],
                r["state"],
                r["event_category"],
                r["source"],
                int(r["report_count"]),
                int(r["verified_count"]),
                int(r["duplicate_count"]),
                float(r["avg_credibility"]) if r["avg_credibility"] is not None else None,
            ),
        )
    return len(rows)


def aggregate(df, trunc: str):
    return (
        df.withColumn("bucket_start", F.date_trunc(trunc, F.col("observed_at")))
        .groupBy(
            "bucket_start",
            F.coalesce("state", F.lit("Unknown")).alias("state"),
            F.coalesce("event_category", F.lit("other")).alias("event_category"),
            "source",
        )
        .agg(
            F.count(F.lit(1)).alias("report_count"),
            F.sum(F.when(F.col("verification_status") == "verified", 1).otherwise(0)).alias(
                "verified_count"
            ),
            F.sum(F.when(F.col("is_duplicate"), 1).otherwise(0)).alias("duplicate_count"),
            F.avg("credibility_score").alias("avg_credibility"),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="VaayuDrishti Spark rollups")
    parser.add_argument("--window-hours", type=int, default=48)
    parser.add_argument("--mode", choices=["hourly", "daily", "all"], default="all")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("vaayudrishti-rollups")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    url = pg_url()
    jdbc_url, user, password, *_ = jdbc_parts(url)
    cutoff = (datetime.now(UTC) - timedelta(hours=args.window_hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    dbtable = (
        "(SELECT state, event_category, source, verification_status, is_duplicate, "
        f"credibility_score, observed_at FROM reports WHERE observed_at >= '{cutoff}') AS reports_win"
    )

    reports = (
        spark.read.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", dbtable)
        .option("user", user)
        .option("password", password)
        .option("fetchsize", "5000")
        .load()
    )

    import psycopg2

    conn = psycopg2.connect(url)
    conn.autocommit = False
    written = {"hourly": 0, "daily": 0}
    try:
        with conn.cursor() as cur:
            if args.mode in ("hourly", "all"):
                rows = [r.asDict() for r in aggregate(reports, "hour").collect()]
                written["hourly"] = upsert(cur, "rollup_hourly", rows)
            if args.mode in ("daily", "all"):
                rows = [r.asDict() for r in aggregate(reports, "day").collect()]
                written["daily"] = upsert(cur, "rollup_daily", rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(
        f"[rollups] window={args.window_hours}h mode={args.mode} "
        f"hourly_rows={written['hourly']} daily_rows={written['daily']}"
    )
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
