"""
Daily pipeline. Run from the repo root:

    python -m ingest.pipeline

Steps:
  1. run every enabled adapter (each returns [] on failure, never crashes)
  2. drop past tournaments, normalize, dedupe across sources
  3. geocode any venue not already in the permanent cache
  4. group tournaments by venue (one map pin per venue)
  5. write docs/data/tournaments.json — the file the map dashboard reads

Design rule: a broken source degrades coverage, never the tool. If every
source fails, the previous day's tournaments.json is left untouched.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from .adapters import get_enabled_adapters
from .dedupe import dedupe
from .fetch import PoliteFetcher
from .geocode import VenueGeocoder
from .schema import Tournament, venue_key

OUTPUT_FILE = ROOT / "docs" / "data" / "tournaments.json"
CONFIG_FILE = ROOT / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


def run() -> int:
    config = load_config()
    user_agent = config["user_agent"]
    fetcher = PoliteFetcher(user_agent)
    geocoder = VenueGeocoder(user_agent)

    # 1. Collect from all sources -------------------------------------------
    all_tournaments: list[Tournament] = []
    for adapter in get_enabled_adapters():
        print(f"[{adapter.id}] fetching ({adapter.method})…")
        if adapter.tos_warning:
            print(f"  ⚠ TOS: {adapter.tos_warning}")
        try:
            found = adapter.fetch(fetcher)
        except Exception as exc:
            print(f"  [{adapter.id}] adapter crashed: {exc} — continuing")
            found = []
        print(f"  [{adapter.id}] {len(found)} tournaments")
        all_tournaments.extend(found)

    # 2. Filter to upcoming, key venues, dedupe ------------------------------
    today = date.today().isoformat()
    upcoming = [t for t in all_tournaments if t.date >= today]
    for t in upcoming:
        t.venue_key = venue_key(t.venue, t.city, t.state)
    upcoming = dedupe(upcoming)
    print(f"[pipeline] {len(upcoming)} upcoming tournaments after dedupe")

    if not upcoming:
        print("[pipeline] no data collected — keeping yesterday's file as-is")
        geocoder.save()
        return 0

    # 3. Geocode (cache-first; almost always zero API calls) -----------------
    for t in upcoming:
        t.lat, t.lon = geocoder.lookup(t.venue_key, t.venue, t.city,
                                       t.state, t.zip_code)
    geocoder.save()
    placed = [t for t in upcoming if t.lat is not None]
    skipped = len(upcoming) - len(placed)
    if skipped:
        print(f"[pipeline] {skipped} tournaments skipped (venue not geocoded "
              f"yet — fix in data/venues.json)")

    # 4. Group by venue: one pin per venue ------------------------------------
    venues: dict[str, dict] = {}
    for t in sorted(placed, key=lambda t: (t.date, t.start_time or "")):
        v = venues.setdefault(t.venue_key, {
            "key": t.venue_key,
            "venue": t.venue,
            "city": t.city,
            "state": t.state,
            "lat": t.lat,
            "lon": t.lon,
            "tournaments": [],
        })
        v["tournaments"].append({
            "name": t.name, "date": t.date, "start_time": t.start_time,
            "buyin": t.buyin, "guarantee": t.guarantee, "game": t.game,
            "url": t.url, "source": t.source,
        })

    # 5. Write the dashboard's data file --------------------------------------
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "venue_count": len(venues),
        "tournament_count": len(placed),
        "venues": list(venues.values()),
    }, indent=1) + "\n")
    print(f"[pipeline] wrote {OUTPUT_FILE.relative_to(ROOT)} "
          f"({len(venues)} venues, {len(placed)} tournaments)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
