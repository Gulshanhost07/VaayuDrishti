
import os

from fpdf import FPDF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "VaayuDrishti_Frontend_Spec.pdf")

BLUE = (13, 55, 110)
GREY = (90, 90, 90)


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
        self.cell(0, 6, clean("VaayuDrishti | Frontend Specification (Phase 2) | SIH26069"), 0, 1, "R")
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
        if self.get_y() > 262:
            self.add_page()
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*BLUE)
        self.set_x(self.l_margin)
        self.multi_cell(0, 7, clean(t))
        self.ln(1)

    def h3(self, t):
        if self.get_y() > 270:
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

    def mono(self, t, size=8.5):
        if self.get_y() > 279:
            self.add_page()
        self.set_font("Courier", "", size)
        self.set_text_color(20, 20, 20)
        for line in t.split("\n"):
            self.set_x(self.l_margin)
            self.multi_cell(0, 4.4, clean(line))
        self.ln(1.5)

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

    def sig(self, method, path, auth, codes="200"):
        if self.get_y() > 274:
            self.add_page()
        self.set_font("Courier", "B", 10)
        self.set_text_color(*BLUE)
        self.set_x(self.l_margin)
        self.multi_cell(0, 5.4, clean("%-6s %s" % (method, path)))
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        self.set_x(self.l_margin)
        self.multi_cell(0, 4.8, clean("auth: %s   success: %s" % (auth, codes)))
        self.ln(1)

    def _wrap_lines(self, text, width):
        out = []
        for para in str(text).split("\n"):
            words = para.split(" ")
            cur = ""
            for w in words:
                trial = w if not cur else cur + " " + w
                if self.get_string_width(trial) <= width - 1.5:
                    cur = trial
                else:
                    if cur:
                        out.append(cur)
                    cur = w
            out.append(cur)
        return out or [""]

    def table(self, headers, rows, widths, size=8.5):
        line_h = 4.6

        def header_row():
            self.set_font("Helvetica", "B", size)
            self.set_fill_color(235, 240, 246)
            self.set_text_color(*BLUE)
            for h, w in zip(headers, widths):
                self.cell(w, line_h + 1, clean(h), 1, 0, fill=True)
            self.ln(line_h + 1)

        def draw_row(cells):
            self.set_font("Courier", "", size - 0.7)
            wrapped = [self._wrap_lines(c, w) for c, w in zip(cells, widths)]
            max_h = max(len(ws) for ws in wrapped) * line_h
            x0, y0 = self.get_x(), self.get_y()
            self.set_text_color(170, 170, 170)
            self.set_draw_color(170, 170, 170)
            x = x0
            for w in widths:
                self.rect(x, y0, w, max_h)
                x += w
            self.set_text_color(20, 20, 20)
            x = x0
            for ws, w in zip(wrapped, widths):
                y = y0 + 0.4
                for ln in ws:
                    self.set_xy(x, y)
                    self.cell(w, line_h, clean(ln))
                    y += line_h
                x += w
            self.set_xy(x0, y0 + max_h)

        if self.get_y() > 264:
            self.add_page()
        header_row()
        for row in rows:
            if self.get_y() > 276:
                self.add_page()
                header_row()
            draw_row(row)
        self.ln(2)

    def json(self, t):
        self.mono(t, size=8)


pdf = Doc(format="A4", unit="mm")
pdf.set_margins(18, 16, 18)
pdf.set_auto_page_break(True, margin=16)
pdf.add_page()

pdf.ln(28)
pdf.set_font("Helvetica", "B", 28)
pdf.set_text_color(*BLUE)
pdf.multi_cell(0, 13, clean("VaayuDrishti"))
pdf.ln(2)
pdf.set_font("Helvetica", "", 16)
pdf.set_text_color(60, 60, 60)
pdf.multi_cell(0, 9, clean("National Weather Big Data Analytics Platform"))
pdf.ln(4)
pdf.set_font("Helvetica", "", 13)
pdf.multi_cell(0, 7, clean("Frontend Specification - Complete API Reference"))
pdf.ln(12)
pdf.set_draw_color(*BLUE)
pdf.set_line_width(1)
pdf.line(18, pdf.get_y(), 80, pdf.get_y())
pdf.set_line_width(0.2)
pdf.ln(9)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(30, 30, 30)
pdf.kv([
    ("Problem ID", "SIH26069 (26069)"),
    ("Organization", "Ministry of Earth Sciences (MoES) / IMD"),
    ("Purpose", "Everything a frontend team needs to build Phase 2"),
    ("Contents", "32 REST endpoints + WebSocket, request/response contracts,"),
    ("", "auth model, error codes, and per-page feature mapping"),
    ("Base URL", "http://localhost:8000  (API prefix: /api/v1)"),
    ("Interactive docs", "http://localhost:8000/docs  (Swagger UI)"),
    ("Machine contract", "http://localhost:8000/openapi.json"),
    ("Verified by", "backend/scripts/api_smoke.py - 49/49 checks passing"),
    ("Version", "1.0"),
    ("Date", "30 September 2026"),
], kw=45)

pdf.h1("1. Base URL, Conventions & Error Handling")
pdf.h2("1.1 Base URL and envelope conventions")
pdf.kv([
    ("REST base", "http://localhost:8000/api/v1"),
    ("Health base", "GET /health and GET /api/v1/health (identical)"),
    ("WebSocket", "ws://localhost:8000/api/v1/live/stream"),
    ("Content type", "application/json; charset=utf-8 (except media + CSV export)"),
    ("Timestamps", "ISO-8601 with offset, e.g. 2026-09-30T08:30:00+00:00 (UTC)"),
    ("Coordinates", "WGS84 decimal degrees: lat -90..90, lon -180..180"),
    ("Pagination", "Every list returns {items:[...], meta:{page,page_size,total,pages}}"),
    ("Unknown params", "Silently ignored (they do NOT cause 422)"),
    ("CORS", "Enabled, default allow_origins='*' (configure via CORS_ORIGINS)"),
])
pdf.h2("1.2 Error envelope (FastAPI default)")
pdf.p("All errors return the standard FastAPI shape. Plan the frontend error "
      "interceptor around it:")
pdf.json(
    '{"detail": "invalid credentials"}            # 401 / 403 / 404 / 409 / 429\n'
    '{"detail": [{"loc": ["query", "bucket"],\n'
    '             "msg": "Input should be ...",\n'
    '             "type": "literal_error"}]}      # 422 validation errors'
)
pdf.h2("1.3 Status-code cheat sheet")
pdf.table(
    ["Code", "When"],
    [
        ["200", "Success (GET/PATCH/POST where documented)"],
        ["201", "Citizen report created (returns tracking token)"],
        ["401", "Missing/invalid/expired JWT, or bad login credentials"],
        ["403", "Authenticated but role too low (e.g. reviewer PATCHes sources)"],
        ["404", "Unknown report id, tracking token, media key, or source name"],
        ["413", "Citizen upload image larger than 10 MB"],
        ["422", "Validation error (bad enum, out-of-range, short text, bad bbox)"],
        ["429", "Login rate limit (15/5min/IP) or citizen limit (10/hour/IP)"],
    ],
    [18, 154],
)

pdf.h1("2. Authentication & Session Management")
pdf.h2("2.1 Login flow")
pdf.sig("POST", "/api/v1/auth/login", "public", "200 | 401 | 422 | 429")
pdf.mono(
    'REQUEST\n'
    '{"email": "admin@vaayu.local", "password": "vaayu@123"}\n'
    '\n'
    'RESPONSE 200\n'
    '{"access_token": "eyJhbGciOi...",\n'
    ' "refresh_token": "eyJhbGciOi...",\n'
    ' "token_type": "bearer", "role": "admin"}'
)
pdf.b("Store access_token (30 min TTL) in memory; refresh_token (7 day TTL) in an "
      "httpOnly-ish storage of your choice.")
pdf.b("Send Authorization: Bearer <access_token> on every authenticated request.")
pdf.b("Login rate limit: 15 attempts / 300 s per IP -> 429 {\"detail\":\"too many login attempts, retry later\"}.")
pdf.h2("2.2 Refresh flow")
pdf.sig("POST", "/api/v1/auth/refresh", "public", "200 | 401 | 422")
pdf.mono('{"refresh_token": "eyJhbGciOi..."}  ->  TokenOut (new access + refresh pair)')
pdf.p("On 401 from refresh: drop tokens and redirect to /admin/login. Refresh "
      "tokens are single-use in spirit - always persist the new pair from the "
      "response.")
pdf.h2("2.3 Current user")
pdf.sig("GET", "/api/v1/auth/me", "bearer", "200 | 401")
pdf.mono('{"id": "6f1c...-uuid", "email": "admin@vaayu.local",\n "full_name": "Admin", "role": "admin"}')
pdf.h2("2.4 Roles")
pdf.table(
    ["Role", "Can do"],
    [
        ["admin", "Everything: verification, bulk actions, source enable/interval"],
        ["reviewer", "Queue, verify/reject/dispute, bulk, pipeline, audit, export"],
        ["viewer", "Read-only admin GETs (same reads as reviewer)"],
    ],
    [26, 146],
)
pdf.p("Login response carries the role; gate frontend routes on it. The seeded "
      "demo admin is admin@vaayu.local / vaayu@123.")

pdf.h1("3. Data Models")
pdf.h2("3.1 Report (list item) - response of /reports, /admin/reports, search")
pdf.table(
    ["Field", "Type", "Notes"],
    [
        ["id", "uuid", "use in /reports/{id} detail links"],
        ["source", "string", "mastodon|reddit|rss|imd|open_meteo|simulator|citizen|load-*"],
        ["source_url", "string?", "original post URL"],
        ["author", "string?", "handle/display name"],
        ["text", "string", "post text (may contain #hashtags)"],
        ["lang", "string?", "e.g. en, hi"],
        ["hashtags", "[string]?", "lower-cased tags without #"],
        ["lat / lon", "float?", "WGS84; null when ungeocoded"],
        ["city / district / state", "string?", "gazetteer geocode"],
        ["event_category", "string?", "one of the 8 categories (below)"],
        ["severity", "string?", "extreme|severe|moderate|mild|unknown"],
        ["confidence", "float?", "classifier confidence 0..1"],
        ["credibility_score", "float?", "ML credibility 0..1"],
        ["verification_status", "string", "pending|verified|rejected|disputed"],
        ["verification_note", "string?", "reviewer note"],
        ["is_duplicate", "bool", "true = near-duplicate of duplicate_of"],
        ["duplicate_of", "uuid?", "canonical report id"],
        ["media", "[MediaRef]?", "see 3.3; [] or null when none"],
        ["observed_at", "datetime", "when the event happened"],
        ["ingested_at", "datetime", "when we stored it"],
        ["plausibility", "object?", "weather cross-check evidence"],
    ],
    [44, 24, 104],
)
pdf.h2("3.2 Report detail extras - GET /reports/{id}")
pdf.kv([
    ("credibility_features", "object: per-feature contributions of the credibility ML model"),
    ("raw", "object: original payload (adapter metadata, geo hints, etc.)"),
])
pdf.h2("3.3 MediaRef")
pdf.json(
    '{"bucket": "vaayu-media", "key": "simulator/ab12....jpg",\n'
    ' "content_type": "image/jpeg", "sha256": "...", "size": 48211,\n'
    ' "source_url": "https://..."}'
)
pdf.p("Render media through GET /api/v1/reports/{id}/media/{key} (same-origin "
      "relative URL, browser gets bytes with Cache-Control: max-age=86400). "
      "Never construct MinIO URLs directly.")
pdf.h2("3.4 Fixed vocabularies")
pdf.kv([
    ("event_category", "rainfall, thunderstorm, flooding, heatwave, fog, dust_storm, strong_winds, other"),
    ("severity", "extreme, severe, moderate, mild, unknown"),
    ("verification_status", "pending, verified, rejected, disputed"),
    ("media types", "image/jpeg, image/png, image/webp, image/gif (max 10 MB)"),
])
pdf.h2("3.5 Envelope models")
pdf.kv([
    ("PageMeta", "{page, page_size, total, pages}"),
    ("ReportPage", "{items: [Report], meta: PageMeta}"),
    ("TokenOut", "{access_token, refresh_token, token_type, role}"),
    ("CitizenSubmitOut", "{id, token, tracking_path, status}"),
    ("TrackOut", "{id, verification_status, verification_note, observed_at, city, state, event_category}"),
])

pdf.h1("4. Endpoint Reference")
pdf.p("All endpoints below were exercised live by backend/scripts/api_smoke.py "
      "(49/49 checks). Parameter tables list name, type, default and "
      "constraints; anything not listed is ignored.")

pdf.h2("4.1 System")
pdf.sig("GET", "/health  and  /api/v1/health", "public", "200")
pdf.kv([
    ("deep", "bool, default false. true -> per-component checks"),
], kw=14)
pdf.json(
    '{"status": "ok|degraded", "service": "api", "env": "dev",\n'
    ' "components": {"postgres": {"ok": true, "ms": 2.1},\n'
    '                "redis": {...}, "opensearch": {"status": "green"},\n'
    '                "kafka": {...}, "minio": {...}}}'
)
pdf.p("Use ?deep=true for the admin 'System Status' widget (adds ~1 s: Kafka "
      "probe runs in a worker thread).")

pdf.h2("4.2 Reports - list")
pdf.sig("GET", "/api/v1/reports", "public", "200 | 422")
pdf.table(
    ["Param", "Type", "Default", "Constraints"],
    [
        ["page", "int", "1", ">= 1"],
        ["page_size", "int", "25", "1..100"],
        ["sort", "enum", "observed_at", "observed_at|ingested_at|credibility_score"],
        ["order", "enum", "desc", "asc|desc"],
        ["date_from", "str", "-", "ISO date/datetime (observed_at >= )"],
        ["date_to", "str", "-", "ISO date/datetime (observed_at <= )"],
        ["state", "str", "-", "exact match, e.g. Maharashtra"],
        ["city", "str", "-", "exact match"],
        ["category", "enum", "-", "one of the 8 categories"],
        ["source", "str", "-", "exact match, e.g. mastodon"],
        ["verification_status", "enum", "-", "pending|verified|rejected|disputed"],
        ["lang", "str", "-", "e.g. en, hi"],
        ["include_duplicates", "bool", "false", "true also returns is_duplicate rows"],
        ["min_credibility", "float", "-", "0..1"],
    ],
    [40, 18, 32, 78],
)
pdf.p("Invalid sort/order value -> 422. All filters combine (AND). Duplicate "
      "rows are hidden by default - the public dashboard should keep that.")
pdf.h2("4.3 Reports - full-text search")
pdf.sig("GET", "/api/v1/reports/search", "public", "200 | 422")
pdf.table(
    ["Param", "Type", "Default", "Notes"],
    [
        ["q", "str", "REQUIRED", "1..200 chars; OpenSearch multi_match + fuzziness"],
        ["page / page_size", "int", "1 / 25", "same as list"],
        ["date_from/date_to", "str", "-", "same as list"],
        ["state / category / source", "str", "-", "same as list"],
        ["include_duplicates", "bool", "false", "same as list"],
    ],
    [46, 18, 30, 74],
)
pdf.p("Response is ReportPage. Empty q -> 422. OpenSearch down -> automatic "
      "Postgres ILIKE fallback (slower, same shape).")
pdf.h2("4.4 Reports - detail, media, tracking")
pdf.sig("GET", "/api/v1/reports/{id}", "public", "200 | 404 | 422")
pdf.p("422 when id is not a valid uuid. Returns ReportDetailOut (section 3.2).")
pdf.sig("GET", "/api/v1/reports/{id}/media/{key}", "public", "200 | 404")
pdf.p("key is the full MediaRef.key path (may contain '/'). Returns raw bytes "
      "with the stored content-type and Cache-Control: public, max-age=86400. "
      "404 when the report, media entry, or stored object is missing.")
pdf.sig("GET", "/api/v1/reports/track/{token}", "public", "200 | 404")
pdf.json(
    '{"id": "uuid", "verification_status": "pending",\n'
    ' "verification_note": null, "observed_at": "...",\n'
    ' "city": "Kolkata", "state": "West Bengal",\n'
    ' "event_category": "flooding"}'
)

pdf.h2("4.5 GeoJSON map layer")
pdf.sig("GET", "/api/v1/geo/reports.geojson", "public", "200 | 422")
pdf.table(
    ["Param", "Type", "Default", "Notes"],
    [
        ["bbox", "str", "-", "minlon,minlat,maxlon,maxlat; malformed -> 422"],
        ["lat / lon", "float", "-", "center of radius search (both required)"],
        ["radius_km", "float", "-", ">0, <=2000; used only with lat+lon"],
        ["limit", "int", "2000", "1..20000"],
        ["date_from/date_to", "str", "-", "report filters (see 4.2)"],
        ["state/city/category/source", "str", "-", "report filters"],
        ["verification_status", "str", "-", "report filter"],
        ["include_duplicates", "bool", "false", "report filter"],
    ],
    [52, 16, 24, 76],
)
pdf.json(
    '{"type": "FeatureCollection",\n'
    ' "features": [{"type": "Feature",\n'
    '   "geometry": {"type": "Point", "coordinates": [77.2, 28.6]},\n'
    '   "properties": {"id", "source", "city", "state", "event_category",\n'
    '     "severity", "confidence", "credibility_score",\n'
    '     "verification_status", "is_duplicate", "lang", "media_count",\n'
    '     "observed_at", "text"}}],\n'
    ' "meta": {"count": 512, "limit": 2000, "truncated": false}}'
)
pdf.p("No coords -> feature skipped. Points always present in properties for "
      "marker styling; fit the map view to bbox for viewport-driven queries.")

pdf.h2("4.6 Analytics - KPI summary")
pdf.sig("GET", "/api/v1/analytics/summary", "public", "200")
pdf.p("No parameters. Non-duplicate reports only (all time):")
pdf.json(
    '{"total_reports": 11336, "verified": 812, "pending": 10480,\n'
    ' "disputed": 12, "rejected": 32, "verified_pct": 7.2,\n'
    ' "avg_credibility": 0.531, "reports_last_24h": 3904,\n'
    ' "reports_last_hour": 168, "states_covered": 31,\n'
    ' "categories": {"rainfall": 4021, "flooding": 2110, ...},\n'
    ' "sources_enabled": 6, "computed_at": "2026-09-30T..."}'
)
pdf.h2("4.7 Analytics - time series (charts)")
pdf.sig("GET", "/api/v1/analytics/timeseries", "public", "200 | 422")
pdf.table(
    ["Param", "Type", "Default", "Notes"],
    [
        ["bucket", "enum", "hour", "hour|day|week (invalid -> 422)"],
        ["group_by", "enum", "category", "category|state|source|city|lang"],
        ["date_from/date_to", "str", "-", "report filters"],
        ["state / category", "str", "-", "report filters"],
    ],
    [40, 18, 30, 84],
)
pdf.json(
    '{"bucket": "hour", "group_by": "category",\n'
    ' "points": [{"bucket": "2026-09-30T00:00:00+00:00",\n'
    '             "key": "rainfall", "count": 148}, ...]}'
)
pdf.p("Default window: last 7 days when no date filter is given. Each point "
      "row is a (time, series-key) pair - pivot by key in the chart layer.")
pdf.h2("4.8 Analytics - breakdowns")
pdf.sig("GET", "/api/v1/analytics/by-state", "public", "200")
pdf.kv([
    ("params", "date_from, date_to, limit (1..50, default 36)"),
    ("response", '{"states": [{"state": "Maharashtra", "count": 1841, "verified": 92, "avg_credibility": 0.54, "last_seen": "..."}]}'),
], kw=22)
pdf.sig("GET", "/api/v1/analytics/by-category", "public", "200")
pdf.kv([
    ("params", "date_from, date_to"),
    ("response", '{"categories": [{"category": "rainfall", "count": 4021, "avg_credibility": 0.55, "last_24h": 812, "prev_24h": 790, "trend": 22}]}'),
    ("trend", "trend = last_24h - prev_24h (delta for up/down arrows)"),
], kw=22)
pdf.sig("GET", "/api/v1/analytics/by-source", "public", "200")
pdf.kv([
    ("params", "date_from, date_to"),
    ("response", '{"sources": [{"source": "mastodon", "count": 5012, "share_pct": 44.2, "avg_credibility": 0.51}]}'),
], kw=22)
pdf.h2("4.9 Analytics - hashtags & filter options")
pdf.sig("GET", "/api/v1/analytics/hashtags", "public", "200")
pdf.kv([
    ("params", "days (1..90, default 7), limit (1..100, default 20)"),
    ("response", '{"days": 7, "hashtags": [{"tag": "mumbai rains", "count": 143}]}'),
], kw=22)
pdf.sig("GET", "/api/v1/analytics/filters", "public", "200")
pdf.kv([
    ("params", "none"),
    ("response", '{"states": [...], "cities": [...], "sources": [...], "langs": [...], "categories": [8 values], "verification_statuses": [4 values]}'),
    ("use", "populates the global FilterBar dropdowns on first load (cache it)"),
], kw=22)

pdf.h2("4.10 Citizen submission")
pdf.sig("POST", "/api/v1/citizen/reports", "public", "201 | 422 | 413 | 429")
pdf.p("Two request styles:")
pdf.mono(
    "JSON (no file):\n"
    '{"text": "Street flooding under the flyover...",  # 10..4000 chars REQUIRED\n'
    ' "city": "Kolkata", "state": "West Bengal",       # optional, <=120 chars\n'
    ' "lat": 22.57, "lon": 88.36,                       # optional GPS\n'
    ' "event_category": "flooding"}                    # optional, 8-value enum\n'
    "\n"
    "MULTIPART (with photo): same fields + file=\n"
    "  (image/jpeg|png|webp|gif, <= 10 MB)"
)
pdf.json(
    '201 RESPONSE\n'
    '{"id": "uuid",\n'
    ' "token": "G6AN29x29lOM...",     # show this to the citizen\n'
    ' "tracking_path": "/track/G6AN...",\n'
    ' "status": "pending"}'
)
pdf.b("Business rules: text trimmed to >= 10 chars; max 4 URLs; no <script>. "
      "Violations -> 422 with string detail.")
pdf.b("Rate limit: 10 submissions / hour / IP -> 429.")
pdf.b("After submit, poll GET /reports/track/{token} (section 4.4) for status.")

pdf.h2("4.11 Admin - verification queue")
pdf.sig("GET", "/api/v1/admin/reports", "bearer (reviewer+)", "200 | 401 | 403")
pdf.table(
    ["Param", "Type", "Default", "Notes"],
    [
        ["page / page_size", "int", "1 / 25", "page_size max 200 (vs 100 public)"],
        ["verification_status", "enum", "pending", "queue defaults to pending"],
        ["include_duplicates", "bool", "true", "queue shows duplicates too"],
        ["date_from/date_to/state/category/source", "str", "-", "same filters as 4.2"],
        ["min_credibility", "float", "-", "same as 4.2"],
    ],
    [58, 16, 28, 66],
)
pdf.p("Returns ReportPage (same items schema as the public list).")
pdf.h2("4.12 Admin - set verification")
pdf.sig("PATCH", "/api/v1/admin/reports/{id}/verification", "bearer (reviewer+)", "200 | 401 | 404 | 422")
pdf.mono('{"status": "verified",            # verified|rejected|disputed|pending\n "note": "confirmed by IMD bulletin"}   # optional, <=1000 chars')
pdf.p("Returns the updated Report. Side effects: audit_log entry + OpenSearch "
      "reindex. 404 for unknown id.")
pdf.h2("4.13 Admin - bulk verification")
pdf.sig("POST", "/api/v1/admin/reports/bulk-verification", "bearer (reviewer+)", "200 | 401 | 422")
pdf.mono('{"ids": ["uuid1", "uuid2", ...],   # 1..200 uuids\n "status": "verified", "note": "..."}')
pdf.json(
    '{"updated": 2, "missing": ["00000000-..."], "status": "verified"}'
)
pdf.p("Unknown ids are reported in missing[] - the call still returns 200. "
      "ids: [] -> 422.")
pdf.h2("4.14 Admin - pipeline health")
pdf.sig("GET", "/api/v1/admin/pipeline", "bearer (reviewer+)", "200 | 401")
pdf.json(
    '{"counters": {"sink_saved": 11336, "sink_duplicate": 1204, ...},\n'
    ' "kafka": {"available": true,\n'
    '           "lag": {"pipeline-enrich": 0, "pipeline-dedup": 0,\n'
    '                   "pipeline-classify": 0, "pipeline-sink": 0},\n'
    '           "sum": 0},\n'
    ' "stages": ["enrich", "dedup", "classify", "sink"],\n'
    ' "recent_runs": [{"source": "simulator", "status": "ok",\n'
    '    "fetched": 42, "published": 42, "errors": 0,\n'
    '    "started_at": "...", "finished_at": "..."}],\n'
    ' "computed_at": "..."}'
)
pdf.p("Poll every 10 s while the admin dashboard is open; kafka.available "
      "false means the broker probe timed out (render degraded state).")
pdf.h2("4.15 Admin - ingest runs, sources, audit, export")
pdf.sig("GET", "/api/v1/admin/ingest-runs", "bearer (reviewer+)", "200 | 401")
pdf.kv([
    ("params", "source (str, optional), limit (1..500, default 50)"),
    ("response", '{"runs": [{"id", "source", "status", "started_at", "finished_at", "fetched", "published", "duplicates", "errors", "last_error"}]}'),
], kw=22)
pdf.sig("GET", "/api/v1/admin/sources", "bearer (reviewer+)", "200 | 401")
pdf.kv([
    ("response", '{"sources": [{"name": "imd", "enabled": true, "interval_seconds": 600, "updated_at": "..."}]}'),
    ("note", "array is under the 'sources' key (not a bare list)"),
], kw=22)
pdf.sig("PATCH", "/api/v1/admin/sources/{name}", "bearer (admin only)", "200 | 401 | 403 | 404 | 422")
pdf.mono('{"enabled": false}                 # and/or:\n{"interval_seconds": 600}        # 5..86400')
pdf.kv([
    ("response", '{"name": "imd", "enabled": false, "interval_seconds": 600}'),
    ("notes", "unknown name -> 404; reviewer role -> 403; audit-logged"),
], kw=22)
pdf.sig("GET", "/api/v1/admin/audit", "bearer (reviewer+)", "200 | 401")
pdf.kv([
    ("params", "limit (1..1000, default 100), action (str filter, e.g. verification:verified)"),
    ("response", '{"entries": [{"id", "user_id", "action", "entity", "entity_id", "before", "after", "created_at"}]}'),
], kw=22)
pdf.sig("GET", "/api/v1/admin/export", "bearer (reviewer+)", "200 | 401 | 422")
pdf.table(
    ["Param", "Type", "Default", "Notes"],
    [
        ["format", "enum", "csv", "csv|json (invalid -> 422)"],
        ["date_from/date_to/state/category/source", "str", "-", "report filters"],
        ["verification_status", "str", "-", "report filter"],
        ["include_duplicates", "bool", "false", "report filter"],
        ["limit", "int", "10000", "1..50000"],
    ],
    [58, 16, 28, 66],
)
pdf.p("csv -> text/csv stream with Content-Disposition attachment "
      "vaayu_export_YYYYmmdd_HHMMSS.csv (columns: id, source, external_id, "
      "observed_at, ingested_at, state, city, district, lat, lon, "
      "event_category, severity, confidence, credibility_score, "
      "verification_status, is_duplicate, lang, author, source_url, text). "
      "json -> {items:[...], count:N}.")

pdf.h1("5. WebSocket Live Feed")
pdf.sig("WS", "/api/v1/live/stream", "public (no auth)", "101")
pdf.p("Server pushes Redis pub/sub messages verbatim. Three message types:")
pdf.h3("5.1 hello (first frame after connect)")
pdf.json('{"type": "hello", "channel": "weather:live", "ts": "2026-09-30T..."}')
pdf.h3("5.2 heartbeat (every 20 s)")
pdf.json('{"type": "heartbeat", "ts": "2026-09-30T..."}')
pdf.p("Use it as a watchdog: if no frame arrives for > 60 s, reconnect.")
pdf.h3("5.3 report (new non-duplicate report persisted by the sink)")
pdf.json(
    '{"id": "uuid", "source": "mastodon", "city": "Pune",\n'
    ' "state": "Maharashtra", "event_category": "rainfall",\n'
    ' "severity": "moderate", "confidence": 0.87,\n'
    ' "credibility_score": 0.62,\n'
    ' "text": "Heavy rain in Pune since morning #IMD",   # <=280 chars\n'
    ' "lat": 18.52, "lon": 73.86,\n'
    ' "observed_at": "2026-09-30T08:31:00+00:00"}'
)
pdf.b("Note: report frames have no 'type' field - discriminate on presence of "
      "the 'id' field (or: type absent + id present => report).")
pdf.b("Client -> server frames are ignored (send pings/text freely).")
pdf.b("Duplicates are NOT published; rate is typically 1-3 msg/s (simulator on).")
pdf.b("Reconnect strategy: exponential backoff (1s, 2s, 4s ... cap 30s); on "
      "reconnect re-fetch geo/summary REST data, then apply deltas from WS.")
pdf.b("Same origin works: ws://localhost:8000/api/v1/live/stream (no auth "
      "header needed; cookies not used).")

pdf.h1("6. Frontend Feature Specification (Phase 2)")
pdf.h2("6.1 Recommended stack")
pdf.kv([
    ("Framework", "Vite + React 18 + TypeScript"),
    ("Styling", "Tailwind CSS, dark/light theme toggle"),
    ("Map", "MapLibre GL (India boundaries, clusters, heatmap, time slider)"),
    ("Charts", "ECharts (timeseries, bars, donut, hashtag cloud)"),
    ("Data", "TanStack Query for REST + native WebSocket for live feed"),
    ("State", "Zustand global filter store shared by map/charts/table"),
    ("Routing", "React Router; /admin/* guarded by JWT role"),
    ("i18n", "English + Hindi dictionaries"),
], kw=30)
pdf.h2("6.2 Public pages and their endpoints")
pdf.table(
    ["Page", "Endpoints consumed"],
    [
        ["DashboardMap",
         "geo/reports.geojson (viewport bbox), analytics/summary (KPI),\n"
         "analytics/timeseries (chart), analytics/filters (FilterBar),\n"
         "WS live/stream (new markers)"],
        ["ReportsList",
         "reports (filters+pagination+sort), analytics/filters,\n"
         "optional reports/search for the search box"],
        ["ReportDetail",
         "reports/{id} (detail), reports/{id}/media/{key} (gallery),\n"
         "geo/reports.geojson with small bbox for 'nearby'"],
        ["CitizenSubmit",
         "POST citizen/reports (JSON or multipart); show token +\n"
         "tracking link on success"],
        ["TrackReport",
         "reports/track/{token}; poll every 30 s while open"],
        ["Analytics page",
         "analytics/by-state, by-category, by-source, hashtags"],
    ],
    [34, 138],
)
pdf.p("Shared FilterBar state: date range, category[], state->city cascade, "
      "verification_status[], source[], min_credibility. Every widget reads "
      "the same store and appends its query params; /analytics/filters "
      "populates the dropdowns once per session.")
pdf.h2("6.3 Admin pages and their endpoints")
pdf.table(
    ["Page", "Endpoints consumed", "Poll"],
    [
        ["Login", "auth/login, auth/refresh, auth/me", "-"],
        ["VerificationQueue",
         "admin/reports, PATCH admin/reports/{id}/verification,\n"
         "POST bulk-verification (multi-select rows)", "-"],
        ["PipelineHealth", "admin/pipeline (lag + counters + runs)", "10 s"],
        ["IngestRuns", "admin/ingest-runs", "30 s"],
        ["Sources", "admin/sources GET + PATCH {name}", "60 s"],
        ["AuditLog", "admin/audit (action filter)", "60 s"],
        ["Export", "admin/export?format=csv (download)", "-"],
        ["System", "health?deep=true", "30 s"],
    ],
    [34, 120, 18],
)
pdf.b("Optimistic UI: apply verify/reject locally, roll back on 4xx; show the "
      "audit id in the toast for traceability.")
pdf.b("403 -> banner 'reviewer role required'; 401 -> silent refresh, else "
      "redirect to login; 429 -> countdown timer from Retry-After absent, "
      "use fixed 60 s for login, 1 h for citizen submit.")
pdf.h2("6.4 Real-time behaviour")
pdf.b("One shared WebSocket connection at app root; fan out to map + ticker "
      "+ KPI increments via a tiny event bus.")
pdf.b("On report frame: insert marker, bump summary counters locally, append "
      "to ticker (cap 50 rows).")
pdf.b("Charts refresh on a 60 s interval instead of on every WS message.")
pdf.h2("6.5 UX / i18n / accessibility")
pdf.b("Language toggle EN/HI on all static copy; report text stays as-is "
      "(lang field available for badges).")
pdf.b("Color-code severity: extreme=red, severe=orange, moderate=yellow, "
      "mild=blue, unknown=grey; always pair color with an icon/label.")
pdf.b("Empty states ('no reports match filters'), skeletons for tables, "
      "error toasts with the API 'detail' string.")
pdf.b("CredibilityBadge: score >= 0.7 green, 0.4-0.7 amber, < 0.4 red; "
      "tooltip shows plausibility object when present.")
pdf.b("Deep-linkable URLs: keep filter state in the query string "
      "(/[reports?state=Maharashtra&category=flooding]).")

pdf.h1("7. Tooling & Verification")
pdf.kv([
    ("openapi.json", "docs/openapi.json - exported from the live API (32 REST ops, 16 schemas)"),
    ("Swagger UI", "http://localhost:8000/docs - try-it-out for every endpoint"),
    ("ReDoc", "http://localhost:8000/redoc"),
    ("Smoke script", "cd backend && python -m scripts.api_smoke - 49/49 checks"),
    ("Live WS test", "connect to ws://localhost:8000/api/v1/live/stream and watch frames"),
    ("Tests", "cd backend && pytest (59 tests) | ruff check . | mypy ."),
    ("Stack up", "docker compose up -d (add --profile full for Spark)"),
], kw=38)
pdf.h2("7.1 Endpoint inventory (all 32)")
pdf.mono(
    "PUBLIC (no auth)\n"
    " GET    /health                     GET    /api/v1/health\n"
    " GET    /api/v1/reports             GET    /api/v1/reports/search\n"
    " GET    /api/v1/reports/{id}        GET    /api/v1/reports/{id}/media/{key}\n"
    " GET    /api/v1/reports/track/{token}\n"
    " GET    /api/v1/geo/reports.geojson\n"
    " GET    /api/v1/analytics/summary   GET    /api/v1/analytics/timeseries\n"
    " GET    /api/v1/analytics/by-state  GET    /api/v1/analytics/by-category\n"
    " GET    /api/v1/analytics/by-source GET    /api/v1/analytics/hashtags\n"
    " GET    /api/v1/analytics/filters\n"
    " POST   /api/v1/citizen/reports\n"
    " POST   /api/v1/auth/login          POST   /api/v1/auth/refresh\n"
    " WS     /api/v1/live/stream\n"
    "\n"
    "BEARER (Authorization: Bearer ...)\n"
    " GET    /api/v1/auth/me\n"
    " GET    /api/v1/admin/reports       PATCH  /api/v1/admin/reports/{id}/verification\n"
    " POST   /api/v1/admin/reports/bulk-verification\n"
    " GET    /api/v1/admin/pipeline      GET    /api/v1/admin/ingest-runs\n"
    " GET    /api/v1/admin/sources       PATCH  /api/v1/admin/sources/{name}  (admin)\n"
    " GET    /api/v1/admin/audit         GET    /api/v1/admin/export"
)

pdf.output(OUT)
print("WROTE", OUT)
