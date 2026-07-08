"""
TEMPLATE — dedicated adapter for one specific local venue.

Use this when a room the recipient cares about isn't covered by the
aggregators. Copy the pattern from pokeratlas_scraper.py (if the room's site
needs HTML scraping) or thepokerlist_feed.py (if it publishes a calendar
feed — many casino event pages have an "add to calendar" .ics link, which is
the easiest and most stable thing to consume).

METHOD: fill in "feed" or "scrape" once you've looked at the room's site.
TOS: check the room's site terms; a single polite daily request to a public
schedule page is normally fine, but note anything concerning in tos_warning.

To enable: uncomment the import + registration lines in adapters/__init__.py.
"""

from __future__ import annotations

from . import Adapter
from ..fetch import PoliteFetcher
from ..schema import Tournament


class MyLocalRoomAdapter(Adapter):
    id = "my-local-room"
    name = "My Local Room (TODO)"
    method = "scrape"  # or "feed"
    tos_warning = ""

    VENUE = "TODO Room Name"
    CITY = "TODO City"
    STATE = "OH"
    SCHEDULE_URL = "https://example.com/poker/tournaments"  # TODO

    def fetch(self, fetcher: PoliteFetcher) -> list[Tournament]:
        html = fetcher.get(self.SCHEDULE_URL)
        if not html:
            return []
        # TODO: parse `html` and return Tournament objects — see the
        # PokerAtlas adapter for a worked example with BeautifulSoup.
        return []
