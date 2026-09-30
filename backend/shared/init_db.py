
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from shared.db import build_engine
from shared.logging import q, setup_logging
from shared.models import Base, UserRole

log = setup_logging("init_db")

REFERENCE_DIR = Path(os.environ.get("REFERENCE_DIR", "/app/data/reference"))
if not REFERENCE_DIR.exists():
    REFERENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "reference"

DEFAULT_SOURCES = {
    "imd": 600,
    "open_meteo": 900,
    "reddit": 300,
    "rss": 900,
    "citizen_db": 30,
    "simulator": 10,
}

POSTGIS_STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "ALTER TABLE reports ADD COLUMN IF NOT EXISTS geom geography(Point, 4326)",
    """
    CREATE OR REPLACE FUNCTION reports_geom_update() RETURNS trigger AS $fn$
    BEGIN
      IF NEW.lat IS NOT NULL AND NEW.lon IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326)::geography;
      ELSE
        NEW.geom := NULL;
      END IF;
      RETURN NEW;
    END;
    $fn$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_reports_geom ON reports",
    """
    CREATE TRIGGER trg_reports_geom
      BEFORE INSERT OR UPDATE OF lat, lon ON reports
      FOR EACH ROW EXECUTE FUNCTION reports_geom_update()
    """,
    "CREATE INDEX IF NOT EXISTS ix_reports_geom ON reports USING GIST (geom)",
]


async def ensure_postgis(engine) -> bool:
    async with engine.begin() as conn:
        try:
            await conn.execute(text(POSTGIS_STATEMENTS[0]))
        except ProgrammingError:
            log.warning(q("postgis unavailable - spatial trigger/index skipped"))
            return False
        for stmt in POSTGIS_STATEMENTS[1:]:
            await conn.execute(text(stmt))
    log.info(q("postgis extension + geom trigger ready"))
    return True


async def seed_sources() -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from shared.db import SessionLocal
    from shared.models import SourceConfig

    async with SessionLocal() as session:
        for name, interval in DEFAULT_SOURCES.items():
            stmt = pg_insert(SourceConfig).values(
                name=name, enabled=True, interval_seconds=interval
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
            await session.execute(stmt)
        await session.commit()
    log.info(q("source_config seeded"))


async def seed_admin() -> None:
    from argon2 import PasswordHasher

    from shared.db import SessionLocal

    email = os.environ.get("ADMIN_EMAIL", "admin@vaayu.local")
    password = os.environ.get("ADMIN_PASSWORD", "vaayu@123")
    ph = PasswordHasher()
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                text("SELECT id FROM admin_users WHERE email = :e"), {"e": email}
            )
        ).first()
        if existing:
            log.info(q(f"admin user already present: {email}"))
            return
        await session.execute(
            text(
                "INSERT INTO admin_users (id, email, password_hash, full_name, role, is_active, created_at) "
                "VALUES (gen_random_uuid(), :e, :p, :n, :r, true, now())"
            ),
            {
                "e": email,
                "p": ph.hash(password),
                "n": "Platform Admin",
                "r": UserRole.admin.value,
            },
        )
        await session.commit()
    log.info(q(f"admin user created: {email}"))


async def main() -> int:
    engine = build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info(q("schema ensured (create_all)"))

    await ensure_postgis(engine)
    await seed_admin()
    await seed_sources()

    from shared.db import SessionLocal

    async with SessionLocal() as session:
        admins: int = (await session.execute(text("SELECT count(*) FROM admin_users"))).scalar_one()
        sources: int = (
            await session.execute(text("SELECT count(*) FROM source_config"))
        ).scalar_one()
        reports: int = (await session.execute(text("SELECT count(*) FROM reports"))).scalar_one()

    msg = f"DB ready: admins={admins} sources={sources} reports={reports}"
    log.info(q(msg))
    print(msg)
    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
