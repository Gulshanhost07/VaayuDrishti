
from __future__ import annotations

import contextlib
from typing import Any

from opensearchpy import OpenSearch, RequestsHttpConnection

from shared.config import settings
from shared.logging import q, setup_logging

log = setup_logging("search")

INDEX = "reports_v1"

MAPPING = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "source": {"type": "keyword"},
            "author": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "standard"},
            "lang": {"type": "keyword"},
            "hashtags": {"type": "keyword"},
            "city": {"type": "keyword"},
            "district": {"type": "keyword"},
            "state": {"type": "keyword"},
            "event_category": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "verification_status": {"type": "keyword"},
            "is_duplicate": {"type": "boolean"},
            "credibility_score": {"type": "float"},
            "lat": {"type": "float"},
            "lon": {"type": "float"},
            "location": {"type": "geo_point"},
            "observed_at": {"type": "date"},
            "ingested_at": {"type": "date"},
            "media_count": {"type": "integer"},
        }
    },
}


def client() -> OpenSearch:
    host = settings.opensearch_url.replace("http://", "").replace("https://", "")
    hostname, _, port = host.partition(":")
    return OpenSearch(
        hosts=[{"host": hostname or "localhost", "port": int(port or 9200)}],
        http_auth=None,
        use_ssl=settings.opensearch_url.startswith("https"),
        verify_certs=False,
        connection_class=RequestsHttpConnection,
        timeout=10,
    )


def ensure_index() -> None:
    c = client()
    if not c.indices.exists(index=INDEX):
        c.indices.create(index=INDEX, body=MAPPING)
        log.info(q(f"created index {INDEX}"))


def index_report(doc: dict[str, Any]) -> None:
    c = client()
    c.index(index=INDEX, id=doc["id"], body=doc, refresh=False)


def delete_report(report_id: str) -> None:
    c = client()
    with contextlib.suppress(Exception):
        c.delete(index=INDEX, id=report_id, refresh=False)


def to_doc(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "source": row.source,
        "author": row.author,
        "text": row.text,
        "lang": row.lang,
        "hashtags": row.hashtags or [],
        "city": row.city,
        "district": row.district,
        "state": row.state,
        "event_category": row.event_category,
        "severity": row.severity,
        "verification_status": row.verification_status,
        "is_duplicate": bool(row.is_duplicate),
        "credibility_score": float(row.credibility_score or 0),
        "lat": row.lat,
        "lon": row.lon,
        "location": {"lat": row.lat, "lon": row.lon}
        if row.lat is not None and row.lon is not None
        else None,
        "observed_at": row.observed_at.isoformat() if row.observed_at else None,
        "ingested_at": row.ingested_at.isoformat() if row.ingested_at else None,
        "media_count": len(row.media or []),
    }
