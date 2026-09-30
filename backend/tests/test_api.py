
from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_root_health() -> None:
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] in {"ok", "degraded"}


def test_healthz_alias() -> None:
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200


def test_openapi_contract() -> None:
    spec = app.openapi()
    paths = spec["paths"]
    for required in (
        "/api/v1/reports",
        "/api/v1/reports/{report_id}",
        "/api/v1/analytics/summary",
        "/api/v1/analytics/timeseries",
        "/api/v1/analytics/by-state",
        "/api/v1/analytics/by-category",
        "/api/v1/geo/reports.geojson",
        "/api/v1/citizen/reports",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/me",
        "/api/v1/admin/reports",
        "/api/v1/admin/pipeline",
        "/api/v1/health",
    ):
        assert required in paths, f"missing {required}"
    assert len(paths) >= 27


def test_unauthenticated_admin_rejected() -> None:
    with TestClient(app) as client:
        for path in (
            "/api/v1/admin/reports",
            "/api/v1/admin/pipeline",
            "/api/v1/auth/me",
        ):
            r = client.get(path)
            assert r.status_code == 401, f"{path} -> {r.status_code}"
            assert r.headers.get("www-authenticate") == "Bearer"


def test_bad_token_rejected() -> None:
    with TestClient(app) as client:
        r = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"}
        )
        assert r.status_code == 401


def test_login_validation_before_redis() -> None:
    with TestClient(app) as client:
        r = client.post("/api/v1/auth/login", json={})
        assert r.status_code == 422


def test_unknown_route_404() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/nope").status_code == 404
