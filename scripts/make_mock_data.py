"""
Generate realistic mock data so the dashboard is fully usable before any
adapter is wired in. Run from the repo root:

    python scripts/make_mock_data.py

Writes docs/data/tournaments.json and seeds data/venues.json (including one
example of a hand-fixed, locked venue so the override format is documented
by a real entry).
"""

import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
random.seed(41)

# Real Ohio-region venues with real coordinates — dense around the default
# home view so clustering, popups, and filters can all be exercised.
VENUES = [
    ("JACK Cleveland Casino", "Cleveland", "OH", 41.4993, -81.6934),
    ("JACK Thistledown Racino", "North Randall", "OH", 41.4351, -81.5279),
    ("MGM Northfield Park", "Northfield", "OH", 41.3236, -81.5334),
    ("Hollywood Casino Columbus", "Columbus", "OH", 39.9481, -83.1156),
    ("Hollywood Casino Toledo", "Toledo", "OH", 41.6180, -83.5310),
    ("Hard Rock Casino Cincinnati", "Cincinnati", "OH", 39.1116, -84.5064),
    ("Rivers Casino Pittsburgh", "Pittsburgh", "PA", 40.4472, -80.0157),
    ("The Meadows Casino", "Washington", "PA", 40.1937, -80.2381),
    ("Wheeling Island Casino", "Wheeling", "WV", 40.0685, -80.7373),
    ("MGM Grand Detroit", "Detroit", "MI", 42.3320, -83.0602),
    ("MotorCity Casino", "Detroit", "MI", 42.3391, -83.0699),
    ("FireKeepers Casino", "Battle Creek", "MI", 42.2506, -85.1132),
    ("Seneca Niagara Casino", "Niagara Falls", "NY", 43.0870, -79.0616),
    ("Presque Isle Downs", "Erie", "PA", 42.0439, -80.0219),
    ("Horseshoe Indianapolis", "Shelbyville", "IN", 39.5647, -85.7891),
]

EVENTS = [
    ("Daily Deepstack NLHE", "NLHE", 150, 3000),
    ("Monday Night $10K GTD", "NLHE", 200, 10000),
    ("Big Stack Bounty", "NLHE", 250, 8000),
    ("PLO Wednesday", "PLO", 180, 5000),
    ("Weekend Warm-Up $25K GTD", "NLHE", 400, 25000),
    ("Seniors Event", "NLHE", 120, None),
    ("Turbo Tuesday", "NLHE", 100, 2000),
    ("Big O Special", "BIG O", 220, 4000),
    ("Monthly Main Event $100K GTD", "NLHE", 1100, 100000),
    ("Ladies Event", "NLHE", 130, None),
    ("Mixed Game Night (HORSE)", "MIXED", 200, None),
    ("Friday Night $15K GTD", "NLHE", 300, 15000),
]

TIMES = ["10:15", "11:00", "12:00", "17:00", "18:15", "19:00"]


def slug(s):
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


venues_out, venue_cache = [], {}
today = date.today()

for venue, city, state, lat, lon in VENUES:
    key = f"{slug(venue)}--{slug(city)}-{slug(state)}"
    venue_cache[key] = {
        "venue": venue, "city": city, "state": state,
        "lat": lat, "lon": lon, "locked": False,
        "geocoded_at": today.isoformat(),
    }
    tournaments = []
    for _ in range(random.randint(3, 8)):
        name, game, buyin, gtd = random.choice(EVENTS)
        d = today + timedelta(days=random.randint(0, 21))
        tournaments.append({
            "name": name,
            "date": d.isoformat(),
            "start_time": random.choice(TIMES),
            "buyin": float(buyin),
            "guarantee": float(gtd) if gtd else None,
            "game": game,
            "url": "https://www.pokeratlas.com/",  # placeholder outbound link
            "source": "mock",
        })
    tournaments.sort(key=lambda t: (t["date"], t["start_time"]))
    venues_out.append({
        "key": key, "venue": venue, "city": city, "state": state,
        "lat": lat, "lon": lon, "tournaments": tournaments,
    })

# Document the manual-override format with a real locked example.
venue_cache["example-hand-fixed-room--sometown-oh"] = {
    "venue": "Example Hand-Fixed Room",
    "city": "Sometown", "state": "OH",
    "lat": 41.0000, "lon": -81.0000,
    "locked": True,
    "_note": "locked: true means the pipeline will never re-geocode or overwrite this entry — edit lat/lon by hand and set locked to protect your fix.",
}

out = {
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "venue_count": len(venues_out),
    "tournament_count": sum(len(v["tournaments"]) for v in venues_out),
    "venues": venues_out,
}

(ROOT / "docs" / "data").mkdir(parents=True, exist_ok=True)
(ROOT / "docs" / "data" / "tournaments.json").write_text(json.dumps(out, indent=1) + "\n")
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "venues.json").write_text(json.dumps(venue_cache, indent=2, sort_keys=True) + "\n")
print(f"Wrote mock data: {out['venue_count']} venues, {out['tournament_count']} tournaments")
