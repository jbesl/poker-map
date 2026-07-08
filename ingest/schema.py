"""
Shared tournament schema.

Every adapter must return a list of Tournament objects. This is the single
contract between "where the data comes from" and everything downstream
(dedupe, geocoding, the map). If a source doesn't have a field, leave it None —
the dashboard degrades gracefully.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Tournament:
    # --- required ---
    name: str                    # "Monday $10K GTD NLHE"
    venue: str                   # "MGM Grand Poker Room"
    city: str                    # "Las Vegas"
    state: str                   # "NV" (2-letter for US; region name otherwise)
    date: str                    # ISO date "2026-07-10"
    source: str                  # adapter id, e.g. "pokeratlas"
    url: str                     # link back to register/info on the source site

    # --- optional ---
    start_time: Optional[str] = None   # "18:00" 24h local, or None
    zip_code: Optional[str] = None
    buyin: Optional[float] = None      # total buy-in in USD (None = unknown)
    guarantee: Optional[float] = None  # prize pool / guarantee in USD
    game: Optional[str] = None         # normalized: "NLHE", "PLO", "MIXED", ...

    # --- filled in later by the pipeline, not by adapters ---
    lat: Optional[float] = None
    lon: Optional[float] = None
    venue_key: str = ""                # stable key into venues.json

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Normalization helpers adapters can (and should) use
# ---------------------------------------------------------------------------

_GAME_PATTERNS = [
    (r"\bP\.?L\.?O\.?8\b|omaha\s*(hi[- /]?lo|8)", "PLO8"),
    (r"\bP\.?L\.?O\.?\b|pot\s*limit\s*omaha", "PLO"),
    (r"\bN\.?L\.?H\.?E?\.?\b|no[- ]?limit\s*hold", "NLHE"),
    (r"\blimit\s*hold", "LHE"),
    (r"\bstud\b", "STUD"),
    (r"\bmix(ed)?\b|\bH\.?O\.?R\.?S\.?E\b|8[- ]game", "MIXED"),
    (r"\bbig\s*o\b", "BIG O"),
]


def normalize_game(text: Optional[str]) -> Optional[str]:
    """Map a source's free-text game description to a small canonical set."""
    if not text:
        return None
    for pattern, canon in _GAME_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return canon
    return text.strip().upper()[:20] or None


def parse_money(text) -> Optional[float]:
    """'$1,100', '$10K GTD', '250' -> float dollars. None if unparseable."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)\s*([kKmM]?)", str(text))
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    mult = {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1)
    return value * mult


def venue_key(venue: str, city: str, state: str) -> str:
    """Stable, human-readable key for the venue geocode cache."""
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return f"{slug(venue)}--{slug(city)}-{slug(state)}"
