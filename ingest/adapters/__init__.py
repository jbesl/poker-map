"""
Adapter interface + registry.

An adapter = one data source. Each adapter:
  * declares an `id`, a human `name`, and whether it uses a FEED or SCRAPE
  * implements fetch(fetcher) -> list[Tournament]
  * is registered in ENABLED_ADAPTERS below

To add a source: copy an existing adapter file, conform to the interface,
and add one line to ENABLED_ADAPTERS. To disable a source: comment out its
line. Nothing else in the project changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schema import Tournament
from ..fetch import PoliteFetcher


class Adapter(ABC):
    id: str = ""            # short slug, e.g. "pokeratlas"
    name: str = ""          # human name for logs/README
    method: str = ""        # "feed" or "scrape"
    tos_warning: str = ""   # non-empty => pipeline prints a review warning

    @abstractmethod
    def fetch(self, fetcher: PoliteFetcher) -> list[Tournament]:
        """Return upcoming tournaments. Must never raise — catch errors and
        return [] so one broken source can't take down the daily run."""


def get_enabled_adapters() -> list[Adapter]:
    # Imported here (not at module top) so a syntax error in one adapter
    # file gives a clear message instead of breaking all imports.
    from .thepokerlist_feed import ThePokerListFeedAdapter
    from .pokeratlas_scraper import PokerAtlasScraperAdapter
    # from .my_local_room import MyLocalRoomAdapter   # dedicated single-venue adapter

    return [
        ThePokerListFeedAdapter(),
        PokerAtlasScraperAdapter(),
        # MyLocalRoomAdapter(),
    ]
