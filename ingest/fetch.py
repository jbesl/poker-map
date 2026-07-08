"""
Polite HTTP fetching shared by all adapters.

Good-citizen defaults, all in one place so no adapter can forget them:
  * honest, identifying User-Agent (set your contact email in config.json)
  * robots.txt is checked before every request; disallowed URLs are skipped
  * a gentle global rate limit (one request every few seconds)
  * conditional GETs (ETag / Last-Modified) so unchanged pages aren't
    re-downloaded — the daily run mostly gets cheap 304s
"""

from __future__ import annotations

import json
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HTTP_CACHE_FILE = DATA_DIR / "http_cache.json"

SECONDS_BETWEEN_REQUESTS = 4.0   # gentle, human pace
TIMEOUT = 30


class PoliteFetcher:
    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last_request_at = 0.0
        self._cache = self._load_cache()

    # -- public ------------------------------------------------------------

    def get(self, url: str) -> str | None:
        """Fetch a URL politely. Returns body text, cached text if the page
        is unchanged (HTTP 304), or None if disallowed/failed."""
        if not self._robots_allow(url):
            print(f"  [robots.txt] disallows {url} — skipping")
            return None

        self._rate_limit()

        headers = {}
        entry = self._cache.get(url, {})
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]

        try:
            resp = self.session.get(url, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as exc:
            print(f"  [fetch error] {url}: {exc}")
            return entry.get("body")  # stale copy is better than nothing

        if resp.status_code == 304 and entry.get("body") is not None:
            print(f"  [unchanged] {url}")
            return entry["body"]
        if resp.status_code != 200:
            print(f"  [HTTP {resp.status_code}] {url}")
            return entry.get("body")

        self._cache[url] = {
            "etag": resp.headers.get("ETag"),
            "last_modified": resp.headers.get("Last-Modified"),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "body": resp.text,
        }
        self._save_cache()
        return resp.text

    # -- internals -----------------------------------------------------------

    def _rate_limit(self):
        wait = SECONDS_BETWEEN_REQUESTS - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _robots_allow(self, url: str) -> bool:
        origin = "{0.scheme}://{0.netloc}".format(urlparse(url))
        rp = self._robots.get(origin)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser(origin + "/robots.txt")
            try:
                rp.read()
            except Exception:
                # robots.txt unreachable -> be conservative but don't hard-fail
                rp.allow_all = True
            self._robots[origin] = rp
        return rp.can_fetch(self.session.headers["User-Agent"], url)

    def _load_cache(self) -> dict:
        if HTTP_CACHE_FILE.exists():
            try:
                return json.loads(HTTP_CACHE_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _save_cache(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        HTTP_CACHE_FILE.write_text(json.dumps(self._cache, indent=1))
