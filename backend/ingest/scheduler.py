
from __future__ import annotations

import asyncio
import signal
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from ingest.adapters import ADAPTERS
from shared.config import settings
from shared.db import SessionLocal
from shared.kafka import Producer, ensure_topics
from shared.logging import q, setup_logging
from shared.models import SourceConfig

log = setup_logging("ingest.scheduler")


async def load_source_configs() -> dict[str, SourceConfig]:
    async with SessionLocal() as session:
        rows = (await session.execute(select(SourceConfig))).scalars().all()
    return {r.name: r for r in rows}


async def main() -> int:
    if not settings.ingest_enabled:
        log.warning(q("INGEST_ENABLED=false - scheduler idle"))
        await asyncio.Event().wait()
        return 0

    await ensure_topics()
    producer = Producer()
    await producer.start()

    configs = await load_source_configs()
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    started = 0

    for name, cls in ADAPTERS.items():
        cfg = configs.get(name)
        if cfg is not None and not cfg.enabled:
            log.info(q(f"adapter '{name}' disabled by source_config - skipping"))
            continue
        if name == "simulator" and not settings.simulator_enabled:
            log.info(q("adapter 'simulator' disabled by SIMULATOR_ENABLED - skipping"))
            continue
        if name == "imd" and not settings.imd_api_key:
            log.warning(q("adapter 'imd' scheduled but IMD_API_KEY is empty (will idle)"))
        interval = cfg.interval_seconds if cfg else cls.default_interval
        adapter = cls(producer)
        scheduler.add_job(
            adapter.run,
            "interval",
            seconds=max(10, interval),
            id=name,
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(ZoneInfo("Asia/Kolkata")),
        )
        started += 1
        log.info(q(f"adapter '{name}' scheduled every {interval}s"))

    if started == 0:
        log.error(q("no adapters enabled - exiting"))
        return 1

    scheduler.start()
    log.info(q(f"scheduler started with {started} adapters"))

    stop = asyncio.Event()

    def _stop(*_args: object) -> None:
        log.info(q("shutdown signal received"))
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, _stop)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, lambda *_: _stop())

    await stop.wait()
    scheduler.shutdown(wait=False)
    await producer.stop()
    log.info(q("scheduler stopped"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
