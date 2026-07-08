"""
Deduplicate tournaments that appear on multiple aggregators.

Two listings are considered the same tournament when they're at the same
venue on the same date with the same start time (or, if times are missing,
the same buy-in). When duplicates collide, the entry from the higher-priority
source wins (feeds are more structured than scrapes, so they rank higher),
but missing fields are backfilled from the losers so nothing is thrown away.
"""

from __future__ import annotations

import re

from .schema import Tournament

# Earlier = more trusted. Unlisted sources go last.
SOURCE_PRIORITY = ["thepokerlist", "pokernews", "cardplayer", "pokeratlas",
                   "pokerschedule", "my-local-room"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _dedupe_key(t: Tournament) -> tuple:
    return (
        t.venue_key,
        t.date,
        t.start_time or f"buyin:{t.buyin}",
    )


def _priority(t: Tournament) -> int:
    try:
        return SOURCE_PRIORITY.index(t.source)
    except ValueError:
        return len(SOURCE_PRIORITY)


def dedupe(tournaments: list[Tournament]) -> list[Tournament]:
    best: dict[tuple, Tournament] = {}
    for t in tournaments:
        key = _dedupe_key(t)
        existing = best.get(key)
        if existing is None:
            best[key] = t
            continue
        winner, loser = ((t, existing) if _priority(t) < _priority(existing)
                         else (existing, t))
        # Backfill any fields the winner is missing.
        for field in ("start_time", "buyin", "guarantee", "game",
                      "zip_code", "url"):
            if getattr(winner, field) in (None, "") and getattr(loser, field):
                setattr(winner, field, getattr(loser, field))
        best[key] = winner
    return list(best.values())
