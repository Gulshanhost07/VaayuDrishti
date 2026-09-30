# VaayuDrishti - National Weather Big Data Analytics Platform

**SIH26069 | Ministry of Earth Sciences | India Meteorological Department**

Scalable, real-time collection + processing + ML verification of weather reports
for India from social media, APIs, RSS, public datasets and citizen submissions.

## Stack

| Layer | Tech |
|---|---|
| Streaming | Redpanda (Kafka API), 4-stage pipeline + DLQ |
| Database | PostgreSQL 17 + PostGIS (centralized store) |
| Search/analytics | OpenSearch (FTS + aggregations) |
| Objects | MinIO (photos/videos) |
| Cache/live | Redis (dedup LSH, rate limits, pub/sub WebSocket feed) |
| Batch | Apache Spark: rollups job + structured-streaming ingest fast path |
| API | FastAPI + JWT/argon2 auth + WebSocket live feed |
| ML | Rule+lexicon multilingual categorizer, explainable credibility scorer, MinHash LSH dedup, plausibility cross-check vs reference observations, offline gazetteer geocoder (all CPU-only, works offline) |

## Quickstart

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

Default admin: `admin@vaayu.local` / `vaayu@123` (change in `.env`).

### Useful commands

```bash
make help
make up-full
make logs
make psql
make test
make lint
make typecheck
make loadtest
make spark-rollups
make spark-up
make demo
make pdf
```

## Data flow

```
sources (IMD/Open-Meteo/RSS/Reddit/Mastodon/citizen/simulator)
  -> weather.raw.posts          (Spark fast path can also write here -> PG)
  -> enrich   (gazetteer geocode, lang, hashtags, media)
  -> weather.enriched.posts
  -> dedup    (content hash + 64-sig MinHash/16-band LSH, Redis)
  -> weather.deduped.posts
  -> classify (event category + severity + credibility)
  -> weather.classified.posts
  -> sink     (Postgres + OpenSearch + Redis live feed) -> dashboard
```

Every stage validates against the previous stage's Pydantic contract; failures go to
`weather.dlq`. Duplicates are stored and flagged (`is_duplicate`) - excluded from
default analytics, available with `include_duplicates=true`.

## API surface (v1, all under `/api/v1`)

| Area | Endpoints |
|---|---|
| Public reports | `GET /reports`, `/reports/search`, `/reports/{id}`, `/reports/track/{token}`, `/reports/{id}/media/{key}` |
| Analytics | `GET /analytics/summary`, `/timeseries`, `/by-state`, `/by-category`, `/by-source`, `/hashtags`, `/filters` |
| Geo | `GET /geo/reports.geojson` (bbox/radius) |
| Citizen | `POST /citizen/reports` (JSON or multipart, rate-limited, returns tracking token) |
| Auth | `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` (roles: viewer < reviewer < admin) |
| Admin | `GET /admin/reports`, `PATCH /admin/reports/{id}/verification`, `POST /admin/reports/bulk-verification`, `GET /admin/pipeline` (counters + consumer lag), `GET /admin/ingest-runs`, `GET/PATCH /admin/sources`, `GET /admin/audit`, `GET /admin/export?format=csv\|json` |
| Live | `WS /live/stream` (Redis pub/sub, heartbeat) |
| System | `GET /health` (deep checks), `GET /healthz` |

## Repo layout

See Section 4 of the PDF for the annotated tree. Short form:

- `backend/` - API, ingestion adapters, pipeline workers, ML, tests, load test
- `spark/jobs/` - Spark rollups + structured-streaming ingest (Dockerfile included)
- `data/reference/` - offline gazetteer (268 cities), aliases (Devanagari + English), hashtag vocabulary, credibility lexicon
- `docs/` - design PDF + generator
- `scripts/demo.sh` - the 10-minute walkthrough used with judges
- `frontend/` - Phase 2 (spec in the PDF, not built yet)

## Verification status workflow

`pending -> verified | rejected | disputed` - set via admin APIs
(`/api/v1/admin/reports/{id}/verification`), every change audited in `audit_logs`.

## Testing

```bash
make test
make lint && make typecheck
```

Tests need no external services (no DB/Redis/Kafka), so they run anywhere in ~100s.
