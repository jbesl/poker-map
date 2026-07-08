# Poker Tournament Map

One map with every upcoming live poker tournament in the region. No searching
city by city — pan and zoom like a hotel-booking map, tap a pin, see what's
running, click through to register.

Built to run itself: a GitHub Action refreshes the data once a day and GitHub
Pages serves the map. No server, no database, no API keys, no bills.

## How it works (30-second version)

```
aggregator sites          GitHub Actions (daily, free)         GitHub Pages (free)
┌────────────────┐        ┌──────────────────────────┐        ┌──────────────────┐
│ PokerAtlas     │ ─────▶ │ ingest/pipeline.py       │ ─────▶ │ docs/ static map │
│ The Poker List │  pull  │  adapters → dedupe →     │ commit │  Leaflet + pins  │
│ (+ more later) │        │  geocode → group by venue│  JSON  │  filters, popups │
└────────────────┘        └──────────────────────────┘        └──────────────────┘
```

- **Adapters** (`ingest/adapters/`) each pull one source into a shared schema.
- **Dedupe** merges the same tournament listed on multiple sites.
- **Geocoding** happens once per venue, ever — results are cached permanently
  in `data/venues.json` (venues don't move).
- The pipeline writes `docs/data/tournaments.json`, which the map reads.
- If every source fails one day, yesterday's data stays up. A broken source
  can never take the map down.

The map ships with **mock data** so it works the moment you enable Pages;
real data replaces it automatically once you wire in source URLs.

## One-time setup (~10 minutes)

1. Push this folder to a new GitHub repository.
2. **Settings → Pages** → Source: "Deploy from a branch" → branch `main`,
   folder `/docs`. Your dashboard URL appears there — that's the link you
   give the recipient.
3. **Settings → Actions → General** → allow Actions, and under "Workflow
   permissions" pick **Read and write** (the job commits refreshed data).
4. Edit `config.json`: put a real contact email in `user_agent` (this is what
   makes the scraper an identifiable good citizen).
5. Set the home area — see next section.
6. Optional now, required eventually: wire in real sources (below). Until
   then the map shows mock Ohio-region data.

## Set the recipient's home city

The map *opens* centered on his area; he can pan anywhere from there.
Search never restricts results either — it only recenters.

Edit the clearly marked block in **`docs/config.js`** (and keep `config.json`
matching):

```js
home: { label: "Cleveland, OH", lat: 41.4993, lon: -81.6944, zoom: 8 }
```

Right-click his city in Google Maps to copy lat/lon. Zoom 8 shows roughly a
150-mile region; 10 is one metro.

## Running the daily job

- **Automatic:** `.github/workflows/daily.yml` runs every day at ~6am Eastern.
- **Manual:** repo → **Actions** tab → *Daily tournament refresh* → **Run
  workflow**. Do this once after setup to replace the mock data.
- **Locally:** `pip install -r requirements.txt` then `python -m ingest.pipeline`.

## Wiring in real sources

Two example adapters are scaffolded against the real target sites; each has
`TODO(owner)` markers showing exactly what to fill in:

- `ingest/adapters/thepokerlist_feed.py` — **feed** adapter (preferred
  method). Add feed/calendar URLs to `FEED_URLS`.
- `ingest/adapters/pokeratlas_scraper.py` — **scraper** adapter (fallback
  where no feed exists). Add schedule-page URLs to `ROOM_URLS` and adjust
  the CSS selectors after inspecting one page in your browser.

⚠️ Each adapter's docstring notes whether the source offers a feed and flags
terms-of-service concerns. **PokerAtlas's terms may restrict automated
collection — review them before enabling that adapter.** The pipeline prints
this reminder on every run as long as a flagged adapter is enabled.

Good-citizen behavior is built into `ingest/fetch.py` and applies to every
adapter automatically: honest User-Agent, robots.txt respected, one request
every few seconds, and unchanged pages aren't re-downloaded.

## Adding a new source

1. Copy the feed or scraper adapter as a template (there's also
   `my_local_room.py`, a template for one specific local card room).
2. Set `id`, `name`, `method` ("feed" or "scrape"), and `tos_warning` if the
   site's terms need review.
3. Implement `fetch()` returning `Tournament` objects (see `ingest/schema.py`
   — it has helpers for parsing money and normalizing game names).
4. Register it with one line in `ingest/adapters/__init__.py`.

Removing a source is commenting out that one line.

## Hand-fixing a venue's coordinates

If a pin lands in the wrong spot:

1. Open `data/venues.json` and find the venue's entry.
2. Right-click the correct spot in Google Maps, copy the coordinates.
3. Set `"lat"` / `"lon"`, and set `"locked": true` — locked entries are never
   re-geocoded or overwritten.
4. Commit. The next daily run uses your fix.

(Geocoder choice, documented: OSM Nominatim — free, no key, venue-level
accuracy — used well within its usage policy because each venue is geocoded
exactly once and cached forever. If a venue can't be found, it falls back to
the city center so it still appears on the map, and you can hand-fix it.)

## How the recipient uses it (share this bit with him)

- **Open the link.** The map starts on your home area — drag and zoom
  anywhere, like a hotel map.
- **Pins show the cheapest buy-in** at that casino (e.g. `$150+`). Numbered
  poker chips are groups of casinos — zoom in and they spread out.
- **Hover or tap a pin** for a quick peek at what's coming up there.
- **Click a pin** for the full list — every tournament with date, time,
  buy-in, guarantee, game, and a *Details & registration* link.
- **Filters** (top bar): buy-in range, dates, game type. Pins update live.
  *Clear all* resets everything.
- **The search box just moves the map** — type a city or ZIP to jump there.
  It never hides tournaments.
- **"Updated …"** in the corner shows when the data was last refreshed
  (every morning, automatically).

## Project structure

```
config.json                     contact email + home area (pipeline side)
requirements.txt                two dependencies: requests, beautifulsoup4
.github/workflows/daily.yml     the daily cron job
ingest/
  schema.py                     shared Tournament schema + parsing helpers
  fetch.py                      polite fetcher (UA, robots.txt, rate limit, cache)
  geocode.py                    Nominatim + permanent venue cache + overrides
  dedupe.py                     cross-source deduplication
  pipeline.py                   orchestrator (python -m ingest.pipeline)
  adapters/
    __init__.py                 adapter interface + the enabled-adapters list
    thepokerlist_feed.py        example FEED adapter
    pokeratlas_scraper.py       example SCRAPER adapter (TOS-flagged)
    my_local_room.py            template for a dedicated single-venue adapter
data/
  venues.json                   permanent geocode cache (hand-editable)
  http_cache.json               conditional-GET cache (auto-managed)
scripts/make_mock_data.py       regenerates demo data
docs/                           the static dashboard (served by GitHub Pages)
  index.html / style.css / app.js / config.js
  data/tournaments.json         what the map displays
```

## Troubleshooting

- **Map is blank:** check that Pages is serving `/docs` on `main`, and that
  `docs/data/tournaments.json` exists.
- **Data looks stale:** Actions tab → open the latest run's logs. One
  source failing is fine; the run says which and continues.
- **A pin is misplaced:** hand-fix it (section above).
- **GitHub disabled the schedule:** repos with no commits for ~60 days get
  their cron paused; the daily data commits normally prevent this, but if it
  happens, one click re-enables it in the Actions tab.
