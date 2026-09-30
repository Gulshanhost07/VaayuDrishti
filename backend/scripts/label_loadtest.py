
from __future__ import annotations

import asyncio

from sqlalchemy import func, select, update

from shared import search
from shared.db import SessionLocal
from shared.models import Report


async def main() -> int:
    async with SessionLocal() as session:
        res = await session.execute(
            update(Report)
            .where(Report.external_id.like("load-%"), Report.source != "loadtest")
            .values(source="loadtest")
        )
        await session.commit()
        changed = int(getattr(res, "rowcount", 0) or 0)
        print(f"relabelled {changed} rows to source='loadtest'")

        rows = list(
            (
                await session.execute(
                    select(Report).where(Report.external_id.like("load-%"))
                )
            ).scalars()
        )

        stats = (
            await session.execute(
                select(Report.source, func.count())
                .group_by(Report.source)
                .order_by(func.count().desc())
            )
        ).all()
        for src, n in stats:
            print(f"  {src}: {n}")

        if rows:

            def _reindex() -> None:
                search.ensure_index()
                for r in rows:
                    search.index_report(search.to_doc(r))

            await asyncio.to_thread(_reindex)
            print(f"reindexed {len(rows)} docs in OpenSearch")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
