"""
FEED adapter — The Poker List (thepokerlist.com)

METHOD: feed. The Poker List aggregates public casino/tour schedules and
exposes structured event data (iCal-style calendar exports on event pages,
and listing pages that are close to structured data). Feeds are preferred:
they're stable across redesigns and clearly intended for consumption.

TOS: Review thepokerlist.com/terms before enabling in production. Public
calendar feeds are generally intended for reuse, but confirm.

WHAT YOU FILL IN: FEED_URLS below — one calendar/feed URL per region or tour
you care about. The iCal parsing here is deliberately dependency-free and
handles the fields we need (SUMMARY, DTSTART, LOCATION, URL, DESCRIPTION).
"""

from __future__ import annotations

import re
from datetime import datetime

from . import Adapter
from ..fetch import PoliteFetcher
from ..schema import Tournament, normalize_game, parse_money

# TODO(owner): replace with the real feed/export URLs you want to pull.
# Each entry: (feed_url, default_city, default_state) — the defaults are used
# only when an event's LOCATION line doesn't include city/state itself.
FEED_URLS: list[tuple[str, str, str]] = [
    # ("https://thepokerlist.com/…/calendar.ics", "Cleveland", "OH"),
]


class ThePokerListFeedAdapter(Adapter):
    id = "thepokerlist"
    name = "The Poker List (feed)"
    method = "feed"
    tos_warning = ""  # set a note here if their terms turn out to restrict reuse

    def fetch(self, fetcher: PoliteFetcher) -> list[Tournament]:
        results: list[Tournament] = []
        for feed_url, default_city, default_state in FEED_URLS:
            try:
                body = fetcher.get(feed_url)
                if body:
                    results.extend(
                        self._parse_ical(body, feed_url, default_city, default_state)
                    )
            except Exception as exc:  # never let one feed kill the run
                print(f"  [{self.id}] error on {feed_url}: {exc}")
        if not FEED_URLS:
            print(f"  [{self.id}] no feed URLs configured yet (see FEED_URLS)")
        return results

    # -- iCal parsing (stdlib only) -----------------------------------------

    def _parse_ical(self, text: str, feed_url: str,
                    default_city: str, default_state: str) -> list[Tournament]:
        events, current = [], None
        # Unfold folded lines (iCal continuation lines start with a space)
        text = re.sub(r"\r?\n[ \t]", "", text)
        for line in text.splitlines():
            if line.startswith("BEGIN:VEVENT"):
                current = {}
            elif line.startswith("END:VEVENT") and current is not None:
                events.append(current)
                current = None
            elif current is not None and ":" in line:
                key, _, value = line.partition(":")
                current[key.split(";")[0].upper()] = value.strip()

        tournaments = []
        for ev in events:
            summary = ev.get("SUMMARY", "")
            dtstart = ev.get("DTSTART", "")
            if not summary or not dtstart:
                continue
            try:
                dt = datetime.strptime(dtstart[:15].rstrip("Z"),
                                       "%Y%m%dT%H%M%S" if "T" in dtstart else "%Y%m%d")
            except ValueError:
                continue

            venue, city, state = self._split_location(
                ev.get("LOCATION", ""), default_city, default_state)
            desc = ev.get("DESCRIPTION", "")

            tournaments.append(Tournament(
                name=summary,
                venue=venue or summary,
                city=city,
                state=state,
                date=dt.strftime("%Y-%m-%d"),
                start_time=dt.strftime("%H:%M") if "T" in dtstart else None,
                buyin=parse_money(self._find(r"buy[- ]?in[:\s]*(\$[\d,kK]+)", summary + " " + desc)),
                guarantee=parse_money(self._find(r"(\$[\d,.]+[kKmM]?)\s*(?:gtd|guarantee)", summary + " " + desc)),
                game=normalize_game(summary + " " + desc),
                url=ev.get("URL", feed_url),
                source=self.id,
            ))
        return tournaments

    @staticmethod
    def _split_location(location: str, default_city: str, default_state: str):
        """'MGM Grand\\, Las Vegas\\, NV' -> ('MGM Grand', 'Las Vegas', 'NV')"""
        parts = [p.strip() for p in location.replace("\\,", "|").split("|") if p.strip()]
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2][:2].upper()
        if len(parts) == 2:
            return parts[0], parts[1], default_state
        return (parts[0] if parts else ""), default_city, default_state

    @staticmethod
    def _find(pattern: str, text: str):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1) if m else None
