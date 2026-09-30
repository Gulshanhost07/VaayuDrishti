
import os
from fpdf import FPDF

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VaayuDrishti_Full_Workflow.pdf")

BLUE = (13, 55, 110)
GREY = (90, 90, 90)
LIGHT = (235, 240, 246)


def clean(t):
    rep = {
        "\u2192": "->", "\u2190": "<-", "\u2022": "-", "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2026": "...",
        "\u00a0": " ", "\u2713": "[x]", "\u25b6": ">", "\u25bc": "v", "\u25b2": "^",
        "\u00d7": "x", "\u2265": ">=", "\u2264": "<=",
    }
    for k, v in rep.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "replace").decode("latin-1")


class Doc(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, clean("VaayuDrishti | National Weather Big Data Analytics Platform | SIH26069"), 0, 1, "R")
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, 14, self.w - self.r_margin, 14)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 8, clean("Page %d" % self.page_no()), 0, 0, "C")

    def h1(self, t, new=True):
        if new:
            self.add_page()
        self.set_font("Helvetica", "B", 17)
        self.set_text_color(*BLUE)
        self.set_x(self.l_margin)
        self.multi_cell(0, 9, clean(t))
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        y = self.get_y() + 1
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_line_width(0.2)
        self.ln(5)

    def h2(self, t):
        self.ln(2)
        if self.get_y() > 265:
            self.add_page()
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*BLUE)
        self.set_x(self.l_margin)
        self.multi_cell(0, 7, clean(t))
        self.ln(1)

    def h3(self, t):
        if self.get_y() > 272:
            self.add_page()
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 30, 30)
        self.set_x(self.l_margin)
        self.multi_cell(0, 6, clean(t))
        self.ln(0.5)

    def p(self, t, size=10):
        if self.get_y() > 275:
            self.add_page()
        self.set_font("Helvetica", "", size)
        self.set_text_color(20, 20, 20)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5.2, clean(t))
        self.ln(1.5)

    def b(self, t, size=10):
        if self.get_y() > 278:
            self.add_page()
        self.set_font("Helvetica", "", size)
        self.set_text_color(20, 20, 20)
        x = self.l_margin
        self.set_x(x)
        self.cell(5, 5.2, "-")
        self.set_x(x + 5)
        self.multi_cell(0, 5.2, clean(t))
        self.ln(0.6)

    def num(self, n, t):
        if self.get_y() > 278:
            self.add_page()
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*BLUE)
        self.set_x(self.l_margin)
        self.cell(8, 5.2, clean(str(n)) + ".")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 5.2, clean(t))
        self.ln(0.6)

    def mono(self, t, size=8.5):
        if self.get_y() > 279:
            self.add_page()
        self.set_font("Courier", "", size)
        self.set_text_color(20, 20, 20)
        for line in t.split("\n"):
            self.set_x(self.l_margin)
            self.multi_cell(0, 4.4, clean(line))
        self.ln(1.5)

    def tree(self, t):
        if self.get_y() > 240:
            self.add_page()
        self.set_font("Courier", "", 7.6)
        self.set_text_color(30, 30, 30)
        self.set_fill_color(248, 249, 251)
        lines = t.split("\n")
        for line in lines:
            if self.get_y() > 282:
                self.add_page()
                self.set_font("Courier", "", 7.6)
            self.cell(0, 4.0, clean(line), 0, 1, fill=False)
        self.ln(2)

    def kv(self, pairs, kw=42):
        for k, v in pairs:
            if self.get_y() > 276:
                self.add_page()
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*BLUE)
            self.set_x(self.l_margin)
            self.cell(kw, 5.4, clean(k))
            self.set_font("Helvetica", "", 10)
            self.set_text_color(20, 20, 20)
            self.multi_cell(0, 5.4, clean(v))
            self.set_x(self.l_margin)
            self.ln(0.5)
        self.ln(1)


pdf = Doc(format="A4", unit="mm")
pdf.set_margins(18, 16, 18)
pdf.set_auto_page_break(True, margin=16)
pdf.add_page()

pdf.ln(30)
pdf.set_font("Helvetica", "B", 30)
pdf.set_text_color(*BLUE)
pdf.multi_cell(0, 14, clean("VaayuDrishti"))
pdf.ln(2)
pdf.set_font("Helvetica", "", 17)
pdf.set_text_color(60, 60, 60)
pdf.multi_cell(0, 9, clean("National Weather Big Data Analytics Platform"))
pdf.ln(6)
pdf.set_font("Helvetica", "", 13)
pdf.multi_cell(0, 7, clean("Full Workflow & Repository Structure Document"))
pdf.ln(14)
pdf.set_draw_color(*BLUE)
pdf.set_line_width(1)
pdf.line(18, pdf.get_y(), 80, pdf.get_y())
pdf.set_line_width(0.2)
pdf.ln(10)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(30, 30, 30)
pdf.kv([
    ("Problem ID", "SIH26069 (26069)"),
    ("Organization", "Ministry of Earth Sciences (MoES)"),
    ("Department", "India Meteorological Department (IMD)"),
    ("Category", "Software"),
    ("Theme", "Disaster Management"),
    ("Scope of this doc", "Backend build (Phase 1) + Frontend specification (Phase 2)"),
    ("Version", "1.0"),
    ("Date", "30 September 2026"),
], kw=45)

pdf.h1("1. Problem Statement & Compliance Map")
pdf.p("Design and develop a scalable National Weather Big Data Analytics Platform capable of "
      "collecting and processing real-time weather-related information for India from multiple "
      "internet-based sources including social media platforms, public datasets, websites, APIs, "
      "and citizen reports. The platform automatically collects weather-related posts tagged with "
      "#IMD and other relevant weather hashtags along with metadata (date & time, city, state, GPS "
      "location, photos, videos, event category) and stores them in a centralized database. Big "
      "data technologies and open-source tools support large-scale real-time ingestion, processing, "
      "storage and visualization. ML/AI techniques identify fake or misleading reports, verify "
      "untrusted sources, remove duplicates and automatically categorize weather events. A "
      "web-based dashboard and Admin Panel provide date-wise, event-wise and location-wise "
      "filtering, verification status tracking, real-time visualization and analytics.")

pdf.h2("Requirement traceability")
pdf.kv([
    ("Multiple sources", "6 adapters: social (Reddit/public JSON), IMD API, Open-Meteo API, RSS/news websites, public datasets, citizen POST /reports + high-volume simulator"),
    ("#IMD + weather hashtags", "Hashtag vocabulary (English + Hindi) matched in enrich stage; hashtags[] column + trending-hashtag analytics"),
    ("Metadata: date/time", "observed_at, ingested_at (timezone-aware IST)"),
    ("Metadata: city/state", "Offline Indian gazetteer + district GeoJSON point-in-polygon geocoding"),
    ("Metadata: GPS", "lat/lon + PostGIS geography(Point) column, bbox filter support"),
    ("Metadata: photos/videos", "Object storage (MinIO), media[] references, size/type validation"),
    ("Metadata: event category", "7 PS categories: rainfall, thunderstorms, flooding, heatwaves, fog, dust storms, strong winds (+ other)"),
    ("Centralized database", "PostgreSQL 17 + PostGIS as canonical store; OpenSearch replica for search/analytics"),
    ("Big data / real-time", "Redpanda (Kafka API) streaming backbone, 3-stage consumer pipeline, Spark structured streaming + batch rollups, MinIO, Redis"),
    ("ML: fake/misleading", "Credibility model (gradient boosting over engineered features incl. weather-plausibility cross-check vs IMD/Open-Meteo observations)"),
    ("ML: verify untrusted", "Source-reputation registry + human verification workflow (JWT admin panel APIs) with audit trail"),
    ("ML: remove duplicates", "MinHash LSH + multilingual sentence embeddings -> duplicate_of links"),
    ("ML: auto-categorize", "Zero-shot baseline -> fine-tuned DistilBERT 7-class classifier with confidence"),
    ("Date/Event/Location filters", "GET /api/v1/reports with combined filter parameters (built now, consumed by UI later)"),
    ("Verification tracking", "verification_status enum + admin verify/reject/bulk endpoints + audit_log"),
    ("Real-time visualization", "WebSocket live feed (Redis pub/sub) + /api/v1/geo/reports.geojson + analytics endpoints"),
    ("Dashboard + Admin panel", "Phase 2 frontend (specified in Section 7), API contract frozen in Phase 1"),
])

pdf.h1("2. System Architecture")
pdf.p("Docker Compose based, fully open-source, runnable on a single developer machine and "
      "horizontally scalable by increasing service replicas. Services:")
pdf.kv([
    ("postgres:17+PostGIS", "Central database: reports, users, audit, rollups, reference observations"),
    ("redpanda", "Kafka-compatible streaming broker (topics, 4 partitions each)"),
    ("opensearch:2", "Full-text search + aggregation engine (report index)"),
    ("minio", "S3-compatible object storage for photos/videos"),
    ("redis:7", "Cache, rate limiting, pub/sub fan-out for the live WebSocket feed"),
    ("api", "FastAPI + uvicorn: REST API, JWT auth, WebSocket (port 8000)"),
    ("ingestor", "APScheduler running all source adapters -> raw.posts"),
    ("worker-enrich", "Geocoding, hashtag/lang parse, media download -> enriched.posts"),
    ("worker-dedup", "MinHash + embedding near-duplicate detection -> deduped.posts"),
    ("worker-ml", "Event classification + credibility scoring -> classified.posts, sink -> DB/index"),
    ("spark-master/worker", "Structured streaming + hourly/daily rollup jobs"),
    ("seed", "One-shot: migrations, admin user, reference geo data"),
])
pdf.h2("End-to-end data flow")
pdf.mono(
    "  [IMD API] [Open-Meteo] [Reddit] [RSS/News] [Citizen POST] [Simulator]\n"
    "        \\         |          |         |            |            /\n"
    "         +--------+----------+---------+------------+-----------+\n"
    "                              |\n"
    "                     (1) adapters normalize -> RawPost JSON\n"
    "                              |\n"
    "                 [Kafka topic: weather.raw.posts]\n"
    "                              |\n"
    "              +---------------+----------------+\n"
    "              | (2) worker-enrich               |\n"
    "              |  hashtag parse, langdetect,      |\n"
    "              |  geocode -> city/state/district, |\n"
    "              |  media -> MinIO                  |\n"
    "              +---------------+----------------+\n"
    "                              |\n"
    "                 [Kafka topic: weather.enriched.posts]\n"
    "                              |\n"
    "              +---------------+----------------+\n"
    "              | (3) worker-dedup                 |\n"
    "              |  (source,external_id), MinHash,  |\n"
    "              |  embeddings -> duplicate_of      |\n"
    "              +---------------+----------------+\n"
    "                              |\n"
    "                 [Kafka topic: weather.deduped.posts]\n"
    "                              |\n"
    "              +---------------+----------------+\n"
    "              | (4) worker-ml                    |\n"
    "              |  7-class categorizer,            |\n"
    "              |  credibility + plausibility      |\n"
    "              +---------------+----------------+\n"
    "                              |\n"
    "                 [Kafka topic: weather.classified.posts]\n"
    "                              |\n"
    "              +---------------+----------------+\n"
    "              | (5) sink: idempotent upsert      |\n"
    "              +----+-----------+-----------+-----+\n"
    "                   |           |           |\n"
    "             PostgreSQL     OpenSearch    Redis (live channel)\n"
    "                   ^\n"
    "                   |  rollups (hourly/daily)\n"
    "             [Spark jobs]\n"
    "                   |\n"
    "             [FastAPI: REST + WebSocket]  ---> future dashboard & admin panel")

pdf.h1("3. Step-by-Step Workflow")
pdf.h2("3.1 Ingestion (M1)")
pdf.num(1, "Scheduler (APScheduler) invokes each adapter on its own interval (IMD 10 min, Open-Meteo 15 min, Reddit 5 min, RSS 15 min, simulator continuous).")
pdf.num(2, "Adapter fetches source (httpx async), normalizes to RawPost schema: source, external_id, url, author, text, hashtags, lang, observed_at, lat/lon (if any), media urls, raw payload.")
pdf.num(3, "Producer publishes to weather.raw.posts (acks=all, idempotent). Adapter writes counters/errors to ingest_runs for the admin health endpoint.")
pdf.num(4, "Citizen reports: POST /api/v1/citizen/reports validated (rate limit, size, spam guard) -> stored pending -> injected into the same topic so every record follows one pipeline.")
pdf.h2("3.2 Processing pipeline (M2)")
pdf.num(5, "ENRICH: extract/normalize hashtags (#IMD, #MumbaiRains, Hindi variants); langdetect language; geocode text/GPS via offline gazetteer + district GeoJSON point-in-polygon -> city, state, district, geometry; download media to MinIO (type/size limits, SHA-256 key); emit enriched.posts.")
pdf.num(6, "DEDUP: exact match on (source, external_id); MinHash LSH over normalized text shingles; embedding cosine > 0.92 confirms near-duplicate -> set duplicate_of, skip sink for duplicates (counted for admin).")
pdf.num(7, "CLASSIFY: DistilBERT 7-class model returns event_category + confidence (zero-shot fallback when model artifact absent). Credibility model computes 0-1 score with feature contributions stored as JSONB.")
pdf.num(8, "PLAUSIBILITY: report location+time is checked against cached reference observations (IMD/Open-Meteo) - e.g. claimed '120mm rain' vs observed 0mm lowers credibility; disagreement raises a disputed flag.")
pdf.num(9, "SINK: idempotent upsert into reports (ON CONFLICT), index document into OpenSearch, publish to Redis channel weather:live for the WebSocket; all steps observable via pipeline metrics endpoint.")
pdf.h2("3.3 Storage & analytics (M5)")
pdf.num(10, "PostgreSQL holds the source of truth with GIST/btree/gin indexes; OpenSearch answers full-text + facet queries; MinIO holds media binaries referenced by reports.media[].")
pdf.num(11, "Spark jobs aggregate hourly/daily rollups (counts by category/state/source, avg credibility) into rollup_hourly / rollup_daily so analytics endpoints stay fast at scale.")
pdf.num(12, "Verification: admin reviewer inspects report + plausibility evidence via admin APIs, sets verification_status (verified/rejected/disputed) + note; audit_log records who/when/old/new.")

pdf.h1("4. Repository Folder Structure")
pdf.p("Monorepo layout. Phase 1 builds backend/; frontend/ is specified here and built in Phase 2.")
pdf.tree(
"""VaayuDrishti/
|-- docker-compose.yml            # all services, profiles: core/full/tools
|-- .env.example                  # API keys (IMD), secrets, toggles
|-- Makefile                      # make up | down | migrate | seed | test | lint
|-- README.md                     # quickstart + demo script
|-- docs/
|   |-- VaayuDrishti_Full_Workflow.pdf   # this document
|   |-- architecture.md
|   |-- api.md                   # endpoint contract for frontend team
|   `-- generate_pdf.py
|-- scripts/
|   |-- load_test.py             # 10k-post simulator blast + latency report
|   `-- demo.sh                  # 10-minute judge demo walkthrough
|-- data/
|   `-- reference/
|       |-- districts.geojson    # India districts (point-in-polygon)
|       |-- cities.csv           # offline gazetteer: city/state/district/lat/lon
|       |-- hashtags.txt         # weather hashtag vocabulary (en + hi)
|       `-- credibility_lexicon.txt
|-- backend/
|   |-- pyproject.toml           # deps + ruff/mypy/pytest config
|   |-- Dockerfile                # shared image for api/ingestor/workers
|   |-- alembic.ini
|   |-- migrations/
|   |   |-- env.py
|   |   `-- versions/            # 0001_initial, ...
|   |-- shared/
|   |   |-- config.py            # pydantic-settings (env-driven)
|   |   |-- db.py                # async engine/session, tx helpers
|   |   |-- models.py            # SQLAlchemy ORM (reports, ingest_runs, ...)
|   |   |-- schemas.py           # Pydantic RawPost/EnrichedPost/... contracts
|   |   |-- topics.py            # Kafka topic names + partitions
|   |   |-- kafka.py             # producer/consumer factory (aiokafka)
|   |   |-- redis_client.py      # cache + pub/sub helper
|   |   |-- objectstore.py       # MinIO client wrapper
|   |   `-- search.py            # OpenSearch index helper
|   |-- api/
|   |   |-- main.py              # app factory, CORS, routers, health
|   |   |-- deps.py              # DI: sessions, auth, pagination
|   |   |-- security.py          # JWT create/verify, password hashing, roles
|   |   |-- ws.py                # /api/v1/live/stream WebSocket endpoint
|   |   `-- routers/
|   |       |-- reports.py       # list/detail/filters/media
|   |       |-- analytics.py     # summary/timeseries/by-state/by-category/by-source/hashtags
|   |       |-- geo.py           # reports.geojson, states summary
|   |       |-- citizen.py       # POST reports, status tracking
|   |       |-- auth.py          # login, refresh, me
|   |       `-- admin.py         # verification, pipeline, ingest-runs, sources, audit, export
|   |-- ingest/
|   |   |-- base.py              # Adapter ABC + stats + error policy
|   |   |-- scheduler.py         # APScheduler entrypoint
|   |   `-- adapters/
|   |       |-- imd.py           # api.imd.gov.in + mausam fallback (key in .env)
|   |       |-- open_meteo.py    # keyless obs/forecast (also feeds plausibility)
|   |       |-- reddit.py        # public JSON endpoints, weather subreddits
|   |       |-- rss.py           # IMD bulletins + news RSS keyword filter
|   |       |-- citizen_db.py    # drains pending citizen reports -> topic
|   |       `-- simulator.py     # synthetic #IMD social stream (hi+en, true/false/dup)
|   |-- pipeline/
|   |   |-- run_stage.py         # generic consumer loop (offsets, DLQ, metrics)
|   |   |-- enrich.py            # stage 2
|   |   |-- dedup.py             # stage 3
|   |   |-- classify.py          # stage 4 (category + credibility + plausibility)
|   |   `-- sink.py              # stage 5 (PG upsert, OS index, Redis live)
|   |-- ml/
|   |   |-- geocode/             # gazetteer loader + point-in-polygon
|   |   |-- classify/            # model wrapper, label map, zero-shot fallback
|   |   |-- credibility/         # feature extraction + GBM model + plausibility
|   |   |-- dedup/               # minhash + embedding wrapper
|   |   |-- embeddings.py        # sentence-transformers loader (multilingual)
|   |   `-- train/
|   |       |-- make_synthetic_labels.py
|   |       |-- train_classifier.py
|   |       |-- train_credibility.py
|   |       `-- evaluate.py      # precision/recall/F1 report
|   |-- spark/
|   |   |-- Dockerfile
|   |   `-- jobs/
|   |       |-- stream_ingest.py # structured streaming (raw -> PG batches)
|   |       `-- rollups.py       # hourly/daily aggregation
|   `-- tests/
|       |-- conftest.py          # testcontainers-style fixtures
|       |-- test_schemas.py
|       |-- test_geocode.py
|       |-- test_dedup.py
|       |-- test_classifier.py
|       |-- test_api_reports.py
|       `-- test_pipeline_e2e.py
`-- frontend/                    # PHASE 2 (specified in Section 7, not built now)
    |-- package.json             # Vite, React 18, TypeScript, Tailwind
    |-- vite.config.ts
    |-- tailwind.config.js
    `-- src/
        |-- main.tsx
        |-- App.tsx              # router: public vs /admin guards
        |-- api/client.ts        # fetch wrapper + typed endpoints
        |-- stores/filters.ts    # global filter state (date/event/location/status)
        |-- stores/auth.ts
        |-- pages/
        |   |-- DashboardMap.tsx     # live map + KPI + charts
        |   |-- ReportsList.tsx      # table with all filters + pagination
        |   |-- ReportDetail.tsx     # shareable report page + media gallery
        |   |-- CitizenSubmit.tsx    # public report form + GPS + upload
        |   |-- TrackReport.tsx      # status by tracking token
        |   `-- admin/
        |       |-- Login.tsx
        |       |-- VerificationQueue.tsx
        |       |-- PipelineHealth.tsx
        |       |-- IngestRuns.tsx
        |       |-- Sources.tsx
        |       `-- AuditLog.tsx
        |-- components/
        |   |-- map/IndiaMap.tsx     # MapLibre GL, clusters, layer toggles
        |   |-- map/TimeSlider.tsx
        |   |-- filters/FilterBar.tsx
        |   |-- charts/{TimeSeries,StateRank,SourceDonut,TrendHashtags}.tsx
        |   |-- kpi/KpiCards.tsx
        |   |-- report/ReportCard.tsx, MediaGallery.tsx, CredibilityBadge.tsx
        |   └-- layout/{Header,Sidebar,ThemeToggle}.tsx
        `-- i18n/                  # en + hi dictionaries""")

pdf.h1("5. Backend Specification (Phase 1 - Build Now)")
pdf.h2("5.1 Technology stack")
pdf.kv([
    ("Language", "Python 3.11 (containers); typing + pydantic v2"),
    ("API", "FastAPI + uvicorn, async SQLAlchemy 2, Alembic migrations"),
    ("Streaming", "Redpanda 24.x (Kafka API), aiokafka consumers/producers"),
    ("Database", "PostgreSQL 17 + PostGIS 3.4"),
    ("Search", "OpenSearch 2.x"),
    ("Objects", "MinIO (S3 API)"),
    ("Cache/bus", "Redis 7"),
    ("Batch", "Apache Spark 3.5 (pyspark)"),
    ("ML", "scikit-learn, datasketch (MinHash), sentence-transformers (multilingual MiniLM), transformers (DistilBERT / bart-large-mnli zero-shot)"),
    ("Quality", "ruff, mypy, pytest (+ httpx TestClient, testcontainers)"),
])
pdf.h2("5.2 Data model (PostgreSQL)")
pdf.h3("reports")
pdf.mono(
    "id uuid PK | source text | external_id text | source_url text\n"
    "author text | text text | lang text | hashtags text[]\n"
    "media jsonb            # [{bucket,key,content_type,sha256}]\n"
    "lat double precision | lon double precision | geom geography(Point,4326)\n"
    "city text | district text | state text\n"
    "event_category enum    # rainfall|thunderstorm|flooding|heatwave|fog|\n"
    "                       # dust_storm|strong_winds|other\n"
    "severity text | confidence numeric | observed_at timestamptz\n"
    "ingested_at timestamptz | credibility_score numeric\n"
    "credibility_features jsonb | plausibility jsonb\n"
    "verification_status enum  # pending|verified|rejected|disputed\n"
    "verified_by uuid | verified_at timestamptz | verification_note text\n"
    "duplicate_of uuid FK | is_duplicate bool | raw jsonb\n"
    "UNIQUE(source, external_id)  |  GIST(geom), btree(event_category,\n"
    "observed_at), gin(text gin_trgm)")
pdf.h3("Other tables")
pdf.kv([
    ("ingest_runs", "id, source, started_at, finished_at, fetched, published, errors, last_error, status"),
    ("admin_users", "id, email, password_hash, full_name, role(admin|reviewer|viewer), is_active, created_at"),
    ("audit_log", "id, user_id, action, entity, entity_id, before jsonb, after jsonb, created_at"),
    ("rollup_hourly", "bucket_start, state, event_category, source, report_count, avg_credibility, verified_count"),
    ("rollup_daily", "same grain at day level"),
    ("reference_observations", "provider, station, lat, lon, observed_at, temp_c, precip_mm, wind_kph, payload jsonb"),
    ("citizen_tokens", "report_id, token, created_at (for public status tracking)"),
])
pdf.h2("5.3 Kafka topics")
pdf.kv([
    ("weather.raw.posts", "adapter output (4 partitions)"),
    ("weather.enriched.posts", "after geocode/media/lang"),
    ("weather.deduped.posts", "after duplicate marking"),
    ("weather.classified.posts", "after category + credibility"),
    ("weather.verified.posts", "successfully persisted records (audit/other consumers)"),
    ("weather.dlq", "poison messages with error metadata"),
])
pdf.h2("5.4 Source adapters")
pdf.kv([
    ("imd", "api.imd.gov.in city forecast/nowcast/warnings (free key via env IMD_API_KEY); graceful fallback when key absent"),
    ("open_meteo", "keyless hourly current weather for gazetteer cities; also populates reference_observations for plausibility"),
    ("reddit", "public JSON endpoints of weather/India subreddits, keyword+hashtag filter, polite UA, rate limit aware"),
    ("rss", "IMD bulletins + Indian news RSS (rainfall/flood/cyclone keywords) -> post normalization"),
    ("citizen_db", "drains citizen_reports flagged pending -> pipeline (keeps API write path decoupled)"),
    ("simulator", "generates realistic #IMD social posts: Indian cities, en/hi text, 7 categories, includes injected duplicates and fake claims for ML demo; rate configurable"),
])
pdf.h2("5.5 ML components")
pdf.kv([
    ("Event classifier", "7 PS categories; train: synthetic + rule-labeled corpus -> DistilBERT; inference fallback: bart-large-mnli zero-shot; output label + confidence"),
    ("Credibility scorer", "GBM/logistic over ~25 features: source trust tier, author age/followers (when available), sensationalism lexicon, exclamation/caps ratio, GPS-vs-text city mismatch, weather-plausibility delta, duplicate burst velocity, media presence, hashtag stuffing; output 0-1 + per-feature contributions (JSONB)"),
    ("Plausibility engine", "nearest reference observation (IMD/Open-Meteo) vs claimed phenomenon within +/- 3h and +/- 50km -> support ratio"),
    ("Dedup", "minhash LSH (64 perms, 5-shingle) + multilingual embeddings cosine >= 0.92; exact (source, external_id) guard first"),
    ("Geocoder", "offline gazetteer (~cities.csv) + district GeoJSON point-in-polygon; text city extraction with state hints; no external API dependency"),
    ("Artifacts", "backend/ml/artifacts/ (joblib/onnx) versioned + fallback chain: trained -> zero-shot -> keyword rules"),
])
pdf.h2("5.6 REST + WebSocket API contract")
pdf.mono(
    "GET    /health                          liveness/readiness\n"
    "GET    /api/v1/reports                  filters: date_from,date_to,\n"
    "                                        event[], state,district,city,\n"
    "                                        verification_status, source,\n"
    "                                        q, bbox, min_credibility,\n"
    "                                        page,page_size,sort\n"
    "GET    /api/v1/reports/{id}             full detail + credibility features\n"
    "GET    /api/v1/reports/{id}/media/{key} signed-ish media streaming\n"
    "POST   /api/v1/reports                  citizen submit (multipart, rate-limit)\n"
    "GET    /api/v1/reports/track/{token}    public verification status\n"
    "GET    /api/v1/analytics/summary        KPIs (totals, verified %, live rate)\n"
    "GET    /api/v1/analytics/timeseries     bucket=hour|day, group_by category/state\n"
    "GET    /api/v1/analytics/by-state       counts + avg credibility per state\n"
    "GET    /api/v1/analytics/by-category    counts + trend delta\n"
    "GET    /api/v1/analytics/by-source      platform distribution\n"
    "GET    /api/v1/analytics/hashtags       trending hashtags\n"
    "GET    /api/v1/geo/reports.geojson      map layer (bbox + filters)\n"
    "WS     /api/v1/live/stream              new report events (redis pub/sub)\n"
    "--- auth: POST /api/v1/auth/login -> JWT(access,refresh); Bearer required ---\n"
    "GET    /api/v1/auth/me\n"
    "PATCH  /api/v1/admin/reports/{id}/verification   verify|reject|dispute+note\n"
    "POST   /api/v1/admin/reports/bulk-verification   bulk actions\n"
    "GET    /api/v1/admin/pipeline           kafka lag, rates, stage health\n"
    "GET    /api/v1/admin/ingest-runs        adapter health table\n"
    "PATCH  /api/v1/admin/sources/{name}     enable/disable adapter\n"
    "GET    /api/v1/admin/audit              audit trail\n"
    "GET    /api/v1/admin/export?format=csv  filtered dataset export")
pdf.h2("5.7 Security & non-functional")
pdf.b("JWT access (30 min) + refresh (7 d); roles admin > reviewer > viewer enforced by dependency.")
pdf.b("Argon2/bcrypt password hashing; citizen endpoints rate-limited per IP (Redis token bucket).")
pdf.b("Idempotent consumers, DLQ for poison messages, graceful shutdown (SIGTERM drains).")
pdf.b("httpx timeouts + retries with backoff; every adapter isolated so one failing source never blocks others.")
pdf.b("Structured JSON logs + /api/v1/admin/pipeline exposes consumer lag and throughput for the demo.")
pdf.b("Media hard limits (10 MB/image, 50 MB/video, mime allowlist), EXIF GPS optionally harvested.")

pdf.h1("6. Build Milestones (backend)")
pdf.h2("M0 - Scaffold & infrastructure")
pdf.b("docker-compose.yml with all services + profiles; Dockerfile; Makefile; .env.example")
pdf.b("shared/: config, db, models, schemas, kafka/redis/minio/opensearch helpers")
pdf.b("Alembic initial migration; seed job (admin user + reference geo data); /health green")
pdf.h2("M1 - Ingestion")
pdf.b("Adapter base + scheduler + ingest_runs accounting")
pdf.b("IMD, Open-Meteo, Reddit, RSS, citizen, simulator adapters publishing to weather.raw.posts")
pdf.h2("M2 - Pipeline")
pdf.b("enrich (geocode/lang/media/hashtags) -> dedup (minhash+embeddings) -> classify (category+credibility) -> sink (PG+OS+Redis)")
pdf.b("Idempotency, DLQ, per-stage counters; end-to-end record visible with city/state/category/dup flag")
pdf.h2("M3 - API")
pdf.b("Reports list/detail with all filters; analytics endpoints; geo.json; media streaming")
pdf.b("Citizen submit + tracking; JWT auth; admin verification + pipeline + ingest + audit + export; WebSocket live feed")
pdf.h2("M4 - ML")
pdf.b("Synthetic label generation, classifier training/eval report, credibility model training")
pdf.b("Plausibility engine wired to reference_observations; artifacts + fallback chain")
pdf.h2("M5 - Spark, hardening & demo")
pdf.b("Spark hourly/daily rollups into rollup_* tables; analytics endpoints read rollups")
pdf.b("Load test (10k posts), latency report, pytest suite green, ruff+mypy clean")
pdf.b("README + scripts/demo.sh: 10-minute judge walkthrough")

pdf.h1("7. Frontend Specification (Phase 2 - Not Built Now)")
pdf.p("The backend exposes the complete contract above; the frontend is a pure consumer and can be "
      "built independently afterwards.")
pdf.h2("7.1 Stack")
pdf.kv([
    ("Framework", "Vite + React 18 + TypeScript"),
    ("Styling", "Tailwind CSS, dark/light theme"),
    ("Map", "MapLibre GL (India boundaries, clusters, hexbin heatmap, time slider)"),
    ("Charts", "ECharts (time series, state rank, source donut, hashtags)"),
    ("Data", "TanStack Query (REST) + native WebSocket for live feed"),
    ("State", "Zustand global filter store shared by map/charts/table"),
    ("Routing", "React Router; public routes vs /admin guarded by JWT role"),
    ("i18n", "English + Hindi dictionaries"),
])
pdf.h2("7.2 Public dashboard pages")
pdf.b("DashboardMap: live India map (clustered markers colored by category), KPI cards, stacked time-series, state ranking, source donut, trending hashtags, verified-alerts ticker; layer toggles (category/status/source); time-slider replay of last 24h/7d.")
pdf.b("FilterBar (global): date range presets, event multi-select, state->district->city cascade, verification status, source; drives every widget.")
pdf.b("ReportsList: paginated table with all filters, sort, credibility score column, quick-verify badges.")
pdf.b("ReportDetail: shareable URL, full metadata, media gallery, credibility breakdown, verification timeline, nearby reports.")
pdf.b("CitizenSubmit: text + category + city/GPS 'use my location' + photo/video upload + CAPTCHA; success returns tracking token.")
pdf.b("TrackReport: verification status by token.")
pdf.h2("7.3 Admin panel pages (JWT)")
pdf.b("Login; VerificationQueue: pending reports side-by-side with plausibility evidence, one-click Verify/Reject/Flag, bulk actions, reviewer notes.")
pdf.b("PipelineHealth: Kafka lag per topic, ingestion rate/min, adapter last-success (WebSocket-refreshed).")
pdf.b("IngestRuns, Sources (enable/disable), AuditLog, CSV/JSON export of filtered datasets.")
pdf.h2("7.4 Real-time & UX")
pdf.b("WebSocket feeds new reports to map + charts without refresh; optimistic UI for admin actions.")
pdf.b("Responsive desktop-first, skeletons/empty states/error toasts, accessible color-coded severity.")

pdf.h1("8. Demo & Verification Script (judge walkthrough)")
pdf.num(1, "docker compose up -d --profile full -> make migrate seed -> health endpoints green.")
pdf.num(2, "Show live Kafka topic counters rising (simulator + Open-Meteo + Reddit adapters).")
pdf.num(3, "Blast: python scripts/load_test.py --count 10000 -> show pipeline throughput + end-to-end latency report.")
pdf.num(4, "Query one record through its lifecycle: raw -> enriched (city/state/GPS) -> dedup (duplicate flagged) -> classified (category+credibility) -> sink.")
pdf.num(5, "Fake-detection: show a fabricated '120mm rain' report vs reference observation -> low plausibility -> disputed suggestion; vs a corroborated report -> high score.")
pdf.num(6, "Admin APIs via /docs: verify/reject a report, audit log entry appears.")
pdf.num(7, "Analytics: date/event/location filters combined; timeseries + state ranking; Spark rollup speeds the query.")
pdf.num(8, "WebSocket: new event appears in live feed instantly; GeoJSON layer ready for the map.")
pdf.num(9, "pytest / ruff / mypy run green (quality gate).")
pdf.p("Success criteria: all PS requirements traceable (Section 1), pipeline observable end-to-end, "
      "ML components demonstrable with metrics, API contract frozen for the frontend team.")

pdf.output(OUT)
print("WROTE", OUT)
