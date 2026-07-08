/* Poker Tournament Map — dashboard logic.
 *
 * Reads data/tournaments.json (written by the daily pipeline), draws one
 * pin per venue (a pill showing the lowest matching buy-in, hotel-map
 * style), clusters dense areas into poker-chip badges, and re-renders
 * whenever a filter changes. The search box only RECENTERS the map — it
 * never restricts which tournaments are shown.
 */
(function () {
  "use strict";

  var HOME = (window.POKER_MAP_CONFIG || {}).home ||
             { label: "USA", lat: 39.5, lon: -95.0, zoom: 4 };

  // ---------------- map setup ----------------
  var map = L.map("map", { zoomControl: true })
             .setView([HOME.lat, HOME.lon], HOME.zoom);

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  var cluster = L.markerClusterGroup({
    maxClusterRadius: 46,
    showCoverageOnHover: false,
    iconCreateFunction: function (c) {
      return L.divIcon({
        html: '<div class="chip-cluster">' + c.getChildCount() + "</div>",
        className: "",
        iconSize: [44, 44],
        iconAnchor: [22, 22]
      });
    }
  });
  map.addLayer(cluster);

  // ---------------- state ----------------
  var VENUES = [];
  var filters = { buyinMin: null, buyinMax: null, dateFrom: null, dateTo: null, games: {} };

  var $ = function (id) { return document.getElementById(id); };

  // ---------------- helpers ----------------
  function money(n) {
    if (n == null) return null;
    if (n >= 1000 && n % 1000 === 0) return "$" + (n / 1000) + "K";
    return "$" + Math.round(n).toLocaleString();
  }

  function niceDate(iso) {
    var p = iso.split("-");
    var d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2]));
    return d.toLocaleDateString(undefined,
      { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
  }

  function niceTime(hm) {
    if (!hm) return "";
    var h = +hm.split(":")[0], m = hm.split(":")[1];
    var ap = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return h + ":" + m + " " + ap;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function matches(t) {
    if (filters.buyinMin != null && (t.buyin == null || t.buyin < filters.buyinMin)) return false;
    if (filters.buyinMax != null && (t.buyin == null || t.buyin > filters.buyinMax)) return false;
    if (filters.dateFrom && t.date < filters.dateFrom) return false;
    if (filters.dateTo && t.date > filters.dateTo) return false;
    var active = Object.keys(filters.games).filter(function (g) { return filters.games[g]; });
    if (active.length && active.indexOf(t.game || "OTHER") === -1) return false;
    return true;
  }

  // ---------------- rendering ----------------
  function render() {
    cluster.clearLayers();
    var shownVenues = 0, shownTournaments = 0;

    VENUES.forEach(function (v) {
      var ts = v.tournaments.filter(matches);
      if (!ts.length) return;
      shownVenues++;
      shownTournaments += ts.length;

      var minBuyin = ts.reduce(function (m, t) {
        return t.buyin != null && (m == null || t.buyin < m) ? t.buyin : m;
      }, null);
      var label = minBuyin != null ? money(minBuyin) + "+" : ts.length + " events";

      var icon = L.divIcon({
        html: '<span class="venue-pill"><span class="dot"></span>' + esc(label) + "</span>",
        className: "",
        iconSize: null,
        iconAnchor: [30, 14]
      });

      var marker = L.marker([v.lat, v.lon], {
        icon: icon,
        title: v.venue,
        keyboard: true,
        alt: v.venue
      });

      marker.bindTooltip(tooltipHtml(v, ts), {
        className: "venue-tip",
        direction: "top",
        offset: [0, -12],
        opacity: 1
      });

      marker.on("click", function () { openPanel(v, ts); });
      cluster.addLayer(marker);
    });

    $("empty-state").hidden = shownVenues > 0;
    var active = countActiveFilters();
    $("filter-count").textContent = active
      ? "· " + active + " active · " + shownTournaments + " tournaments shown"
      : "· " + shownTournaments + " tournaments";
  }

  function tooltipHtml(v, ts) {
    var rows = ts.slice(0, 3).map(function (t) {
      return "<li><strong>" + esc(t.name) + "</strong><br>" +
        esc(niceDate(t.date)) + (t.start_time ? " · " + esc(niceTime(t.start_time)) : "") +
        (t.buyin != null ? ' · <span class="money">' + esc(money(t.buyin)) + "</span>" : "") +
        (t.guarantee != null ? ' · <span class="money">' + esc(money(t.guarantee)) + " GTD</span>" : "") +
        "</li>";
    }).join("");
    var more = ts.length > 3
      ? '<li class="tip-more">+ ' + (ts.length - 3) + " more — click for all</li>" : "";
    return "<h3>" + esc(v.venue) + "</h3>" +
      '<p class="tip-city">' + esc(v.city) + ", " + esc(v.state) + " · " +
      ts.length + " upcoming</p><ul>" + rows + more + "</ul>";
  }

  // ---------------- drill-down panel ----------------
  function openPanel(v, ts) {
    $("panel-venue").textContent = v.venue;
    $("panel-city").textContent = v.city + ", " + v.state + " · " +
      ts.length + " upcoming tournament" + (ts.length === 1 ? "" : "s");

    $("panel-list").innerHTML = ts.map(function (t) {
      var tags = "";
      if (t.buyin != null) tags += '<span class="tag buyin">' + esc(money(t.buyin)) + "</span>";
      if (t.guarantee != null) tags += '<span class="tag gtd">' + esc(money(t.guarantee)) + " GTD</span>";
      if (t.game) tags += '<span class="tag">' + esc(t.game) + "</span>";
      return "<li>" +
        '<p class="t-name">' + esc(t.name) + "</p>" +
        '<p class="t-when">' + esc(niceDate(t.date)) +
          (t.start_time ? " · " + esc(niceTime(t.start_time)) : "") + "</p>" +
        '<div class="t-tags">' + tags + "</div>" +
        '<a class="t-link" href="' + esc(t.url) + '" target="_blank" rel="noopener">' +
          "Details &amp; registration →</a>" +
        "</li>";
    }).join("");

    $("panel").hidden = false;
    $("panel-close").focus();
  }

  $("panel-close").addEventListener("click", function () { $("panel").hidden = true; });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") $("panel").hidden = true;
  });

  // ---------------- filters ----------------
  function countActiveFilters() {
    var n = 0;
    if (filters.buyinMin != null) n++;
    if (filters.buyinMax != null) n++;
    if (filters.dateFrom) n++;
    if (filters.dateTo) n++;
    n += Object.keys(filters.games).filter(function (g) { return filters.games[g]; }).length;
    return n;
  }

  function readInputs() {
    var min = $("buyin-min").value, max = $("buyin-max").value;
    filters.buyinMin = min === "" ? null : +min;
    filters.buyinMax = max === "" ? null : +max;
    filters.dateFrom = $("date-from").value || null;
    filters.dateTo = $("date-to").value || null;
    render();
  }

  ["buyin-min", "buyin-max", "date-from", "date-to"].forEach(function (id) {
    $(id).addEventListener("input", readInputs);
  });

  function buildGameChips() {
    var games = {};
    VENUES.forEach(function (v) {
      v.tournaments.forEach(function (t) { games[t.game || "OTHER"] = true; });
    });
    var box = $("game-chips");
    box.innerHTML = "";
    Object.keys(games).sort().forEach(function (g) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "game-chip";
      btn.textContent = g;
      btn.setAttribute("aria-pressed", "false");
      btn.addEventListener("click", function () {
        filters.games[g] = !filters.games[g];
        btn.setAttribute("aria-pressed", String(!!filters.games[g]));
        render();
      });
      box.appendChild(btn);
    });
  }

  function clearFilters() {
    ["buyin-min", "buyin-max", "date-from", "date-to"].forEach(function (id) { $(id).value = ""; });
    filters = { buyinMin: null, buyinMax: null, dateFrom: null, dateTo: null, games: {} };
    document.querySelectorAll(".game-chip").forEach(function (b) {
      b.setAttribute("aria-pressed", "false");
    });
    render();
  }
  $("clear-filters").addEventListener("click", clearFilters);
  $("empty-clear").addEventListener("click", clearFilters);

  // ---------------- search = recenter only ----------------
  $("search-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var q = $("search-input").value.trim();
    if (!q) return;
    // Free OSM Nominatim geocoding for a single user-triggered lookup.
    fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=us&q=" +
          encodeURIComponent(q))
      .then(function (r) { return r.json(); })
      .then(function (results) {
        if (results && results.length) {
          map.flyTo([+results[0].lat, +results[0].lon], Math.max(map.getZoom(), 9));
        } else {
          $("search-input").value = "";
          $("search-input").placeholder = "Place not found — try city, state";
        }
      })
      .catch(function () {
        $("search-input").placeholder = "Search unavailable right now";
      });
  });

  // ---------------- load data ----------------
  fetch("data/tournaments.json", { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (data) {
      VENUES = (data.venues || []).filter(function (v) {
        return v.lat != null && v.lon != null;
      });
      var when = data.generated_at ? new Date(data.generated_at) : null;
      $("refreshed").textContent = when
        ? "Updated " + when.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
          " " + when.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
        : "Updated recently";
      buildGameChips();
      render();
    })
    .catch(function (err) {
      $("refreshed").textContent = "Couldn't load tournament data";
      console.error("Failed to load data/tournaments.json:", err);
    });

  // Collapse the filter tray by default on small screens.
  if (window.matchMedia("(max-width: 700px)").matches) {
    $("filters").open = false;
  }
})();
