"""
SCRAPER adapter — PokerAtlas (pokeratlas.com)

METHOD: scrape. PokerAtlas has the strongest North American daily-tournament
coverage but offers no public API, RSS, or calendar feed, so this adapter
parses HTML as a fallback.

TOS WARNING (review before enabling): PokerAtlas's Terms of Use restrict
automated collection of their content. Do NOT enable this adapter until you
have read their current terms (pokeratlas.com/terms) and are comfortable, or
have asked them for permission. The tos_warning field below makes the
pipeline print this reminder on every run while the adapter is enabled.

Robots.txt is checked automatically by PoliteFetcher; disallowed pages are
skipped even if you list them here.

WHAT YOU FILL IN:
  * ROOM_URLS — the tournament-schedule page for each poker room you want
  * the CSS selectors marked TODO — inspect one page in your browser
    (right-click -> Inspect) and adjust; the structure below matches the
    typical "one row per tournament" schedule table.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from . import Adapter
from ..fetch import PoliteFetcher
from ..schema import Tournament, normalize_game, parse_money

# TODO(owner): one entry per poker room schedule page:
# (url, venue_name, city, state)
ROOM_URLS: list[tuple[str, str, str, str]] = [
    # ("https://www.pokeratlas.com/poker-room/jack-cleveland-casino/tournaments",
    #  "JACK Cleveland Casino", "Cleveland", "OH"),
]

# TODO(owner): adjust these after inspecting a real schedule page.
SELECTORS = {
    "row": "table.tournaments tbody tr",   # one tournament per row
    "name": "td.name a",
    "date": "td.date",                     # e.g. "Jul 10"
    "time": "td.time",                     # e.g. "6:15 PM"
    "buyin": "td.buy-in",
    "guarantee": "td.guarantee",
    "game": "td.game",
    "link": "td.name a",                   # href -> detail page
}


class PokerAtlasScraperAdapter(Adapter):
    id = "pokeratlas"
    name = "PokerAtlas (scraper)"
    method = "scrape"
    tos_warning = ("PokerAtlas terms may restrict automated collection — "
                   "review pokeratlas.com/terms before running in production.")

    def fetch(self, fetcher: PoliteFetcher) -> list[Tournament]:
        results: list[Tournament] = []
        for url, venue, city, state in ROOM_URLS:
            try:
                html = fetcher.get(url)
                if html:
                    results.extend(self._parse_room(html, url, venue, city, state))
            except Exception as exc:
                print(f"  [{self.id}] error on {url}: {exc}")
        if not ROOM_URLS:
            print(f"  [{self.id}] no room URLs configured yet (see ROOM_URLS)")
        return results

    def _parse_room(self, html: str, page_url: str,
                    venue: str, city: str, state: str) -> list[Tournament]:
        from datetime import datetime

        soup = BeautifulSoup(html, "html.parser")
        tournaments = []
        for row in soup.select(SELECTORS["row"]):
            name_el = row.select_one(SELECTORS["name"])
            date_el = row.select_one(SELECTORS["date"])
            if not name_el or not date_el:
                continue

            date_iso = self._parse_date(date_el.get_text(strip=True))
            if not date_iso:
                continue

            link_el = row.select_one(SELECTORS["link"])
            href = link_el.get("href", "") if link_el else ""
            if href.startswith("/"):
                href = "https://www.pokeratlas.com" + href

            tournaments.append(Tournament(
                name=name_el.get_text(strip=True),
                venue=venue,
                city=city,
                state=state,
                date=date_iso,
                start_time=self._parse_time(self._text(row, "time")),
                buyin=parse_money(self._text(row, "buyin")),
                guarantee=parse_money(self._text(row, "guarantee")),
                game=normalize_game(self._text(row, "game") or name_el.get_text()),
                url=href or page_url,
                source=self.id,
            ))
        return tournaments

    # -- small helpers -------------------------------------------------------

    @staticmethod
    def _text(row, key):
        el = row.select_one(SELECTORS[key])
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _parse_date(text: str):
        """'Jul 10' -> '2026-07-10' (assumes upcoming; rolls to next year if
        the date already passed)."""
        from datetime import date, datetime
        for fmt in ("%b %d", "%B %d", "%m/%d", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text.strip(), fmt)
                year = dt.year if dt.year > 1900 else date.today().year
                candidate = dt.replace(year=year).date()
                if candidate < date.today() and dt.year <= 1900:
                    candidate = candidate.replace(year=year + 1)
                return candidate.isoformat()
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_time(text):
        from datetime import datetime
        if not text:
            return None
        for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
            try:
                return datetime.strptime(text.strip().upper(), fmt).strftime("%H:%M")
            except ValueError:
                continue
        return None
