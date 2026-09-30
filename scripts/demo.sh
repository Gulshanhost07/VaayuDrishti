#!/usr/bin/env bash
set -euo pipefail

step() { printf '\n\033[36m== %s ==\033[0m\n' "$1"; }

step "0. Start the full stack (~60s first time)"
cp -n .env.example .env || true
docker compose --profile full up -d --build
echo "Waiting for API health..."
until curl -sf http://localhost:8000/health >/dev/null; do sleep 2; done

step "1. Big-data stack on screen"
docker compose ps --format 'table {{.Service}}\t{{.Status}}'
echo "Spark UI: http://localhost:8080 | Kafka: localhost:19092 | OpenSearch: :9200 | MinIO: :9001"

step "2. Live ingestion (adapters -> weather.raw.posts)"
docker compose logs -f --tail=15 ingestor & LOGS=$!
sleep 8; kill $LOGS 2>/dev/null || true

step "3. Blast 10k posts through the 4-stage pipeline"
docker compose exec api python -m scripts.load_test --count 10000 --rate 1000

step "4. Admin login (JWT)"
TOKEN=$(curl -sf -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@vaayu.local","password":"vaayu@123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "JWT acquired (${#TOKEN} chars)"

step "5. Pipeline throughput + consumer lag"
curl -s "http://localhost:8000/api/v1/admin/pipeline" -H "Authorization: Bearer $TOKEN" | python -m json.tool

step "6. REST API analytics"
curl -s "http://localhost:8000/api/v1/analytics/summary" -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s "http://localhost:8000/api/v1/analytics/by-state?limit=5" -H "Authorization: Bearer $TOKEN" | python -m json.tool

step "7. Full-text search + GeoJSON map data"
curl -s "http://localhost:8000/api/v1/reports/search?q=floods&size=2" -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s "http://localhost:8000/api/v1/geo/reports.geojson?limit=3" | python -m json.tool

step "8. Spark hourly rollups"
docker compose --profile full run --rm spark-jobs

step "9. Postgres row count + OpenSearch index"
docker compose exec postgres psql -U vaayu -d vaayu -c 'SELECT event_category, count(*) FROM reports GROUP BY 1 ORDER BY 2 DESC LIMIT 8;'
curl -s "http://localhost:9200/_cat/indices?v" || true

step "10. Citizen submission round-trip (public endpoint, no auth)"
curl -s -X POST http://localhost:8000/api/v1/citizen/reports \
  -H 'Content-Type: application/json' \
  -d '{"text":"Very heavy rain with waterlogging on MG Road","city":"Bengaluru","state":"Karnataka","lat":12.97,"lon":77.59,"event_category":"rainfall"}' \
  | python -m json.tool

step "11. Admin verification queue (audited)"
curl -s "http://localhost:8000/api/v1/admin/reports?verification_status=pending&page_size=3" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

step "12. WebSocket live feed"
echo "Connect ws://localhost:8000/api/v1/live/stream in a client to watch posts arrive in real time."

step "Demo complete. Useful follow-ups:"
echo "  make logs           # tail everything"
echo "  make spark-stream   # Spark structured-streaming ingest fast path"
echo "  make down           # stop (volumes kept)"
echo "  http://localhost:8000/docs   # OpenAPI"
