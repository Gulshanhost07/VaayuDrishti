
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.config import settings
from shared.logging import q, setup_logging

log = setup_logging("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(q(f"api starting env={settings.app_env}"))
    try:
        from shared.search import ensure_index

        ensure_index()
    except Exception as exc:
        log.warning(q(f"opensearch not ready at boot: {exc}"))
    yield
    log.info(q("api stopped"))


def create_app() -> FastAPI:
    app = FastAPI(
        title="VaayuDrishti API",
        description="National Weather Big Data Analytics Platform (SIH26069) - backend API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "api", "env": settings.app_env}

    app.add_api_route(
        "/healthz",
        health,
        methods=["GET"],
        include_in_schema=False,
    )

    try:
        from api.routers import (
            admin,
            analytics,
            auth,
            citizen,
            geo,
            live,
            reports,
            system,
        )

        app.include_router(system.router, prefix="/api/v1", tags=["system"])
        app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
        app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
        app.include_router(geo.router, prefix="/api/v1", tags=["geo"])
        app.include_router(citizen.router, prefix="/api/v1", tags=["citizen"])
        app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
        app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
        app.include_router(live.router, prefix="/api/v1", tags=["live"])
        log.info(q("api routers attached"))
    except ImportError as exc:
        log.warning(q(f"api routers not available: {exc}"))

    here = Path(__file__).resolve()
    for candidate in (here.parents[1] / "frontend", here.parents[2] / "frontend"):
        if candidate.is_dir():
            app.mount("/", StaticFiles(directory=candidate, html=True), name="frontend")
            log.info(q(f"frontend mounted from {candidate}"))
            break

    return app


app = create_app()
