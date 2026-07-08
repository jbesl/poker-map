"""
Geocoding + venue cache.

WHY THIS DESIGN (documented choice):
Poker venues don't move, so we geocode each unique venue ONCE and cache the
result permanently in data/venues.json, which is committed to the repo. After
the first few runs the tool makes essentially zero geocoding calls, forever.

GEOCODER CHOICE: OpenStreetMap Nominatim (free, no API key). Chosen over a
bundled ZIP dataset because it gives venue-level accuracy (the actual casino,
not the city centroid), and our permanent cache keeps us far inside
Nominatim's usage policy (max 1 request/second, identifying User-Agent —
both enforced below; in practice we make a handful of calls ever).
FALLBACK: if Nominatim can't find the street address, we retry with just
"city, state", which always resolves — so every venue lands on the map, at
worst at city-level accuracy, and you can hand-fix it (see below).

MANUAL OVERRIDE — how to hand-fix a venue:
Open data/venues.json, find the venue's entry, set its "lat"/"lon" to the
correct values, and set "locked": true. Locked entries are never re-geocoded
or overwritten. Get coordinates by right-clicking the spot in Google Maps.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VENUES_FILE = DATA_DIR / "venues.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_MIN_INTERVAL = 1.1  # seconds — respects the 1 req/sec policy


class VenueGeocoder:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.venues = self._load()
        self._last_call = 0.0
        self._dirty = False

    def lookup(self, key: str, venue: str, city: str, state: str, zip_code=None):
        """Return (lat, lon) for a venue, geocoding only on first sight."""
        entry = self.venues.get(key)
        if entry and entry.get("lat") is not None:
            return entry["lat"], entry["lon"]

        # Not cached -> geocode once. Try full address, then city-level.
        latlon = (self._nominatim(f"{venue}, {city}, {state} {zip_code or ''}")
                  or self._nominatim(f"{city}, {state}, USA"))
        self.venues[key] = {
            "venue": venue,
            "city": city,
            "state": state,
            "lat": latlon[0] if latlon else None,
            "lon": latlon[1] if latlon else None,
            "locked": False,   # set true after hand-fixing to protect your edit
            "geocoded_at": time.strftime("%Y-%m-%d"),
        }
        self._dirty = True
        if latlon is None:
            print(f"  [geocode] FAILED for '{venue}' ({city}, {state}) — "
                  f"add lat/lon by hand in venues.json and set locked: true")
        return latlon or (None, None)

    def save(self):
        if self._dirty or not VENUES_FILE.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            VENUES_FILE.write_text(
                json.dumps(self.venues, indent=2, sort_keys=True) + "\n")

    # -- internals ----------------------------------------------------------

    def _nominatim(self, query: str):
        wait = NOMINATIM_MIN_INTERVAL - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
        try:
            resp = requests.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
                headers={"User-Agent": self.user_agent},
                timeout=30,
            )
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception as exc:
            print(f"  [geocode] error for '{query}': {exc}")
        return None

    def _load(self) -> dict:
        if VENUES_FILE.exists():
            try:
                return json.loads(VENUES_FILE.read_text())
            except json.JSONDecodeError:
                print("  [geocode] venues.json is corrupt — starting fresh "
                      "(the old file is still in git history)")
        return {}
