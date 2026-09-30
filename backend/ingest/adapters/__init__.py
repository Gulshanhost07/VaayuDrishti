
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ingest.base import Adapter

from ingest.adapters.citizen_db import CitizenDbAdapter
from ingest.adapters.imd import IMDAdapter
from ingest.adapters.mastodon import MastodonAdapter
from ingest.adapters.open_meteo import OpenMeteoAdapter
from ingest.adapters.reddit import RedditAdapter
from ingest.adapters.rss import RSSAdapter
from ingest.adapters.simulator import SimulatorAdapter

ADAPTERS: dict[str, type[Adapter]] = {
    IMDAdapter.name: IMDAdapter,
    OpenMeteoAdapter.name: OpenMeteoAdapter,
    MastodonAdapter.name: MastodonAdapter,
    RSSAdapter.name: RSSAdapter,
    RedditAdapter.name: RedditAdapter,
    SimulatorAdapter.name: SimulatorAdapter,
    CitizenDbAdapter.name: CitizenDbAdapter,
}
