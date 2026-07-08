// ============================================================
//  SET THE RECIPIENT'S HOME AREA HERE
//  The map OPENS centered on this spot at this zoom — he can
//  then pan and zoom anywhere; nothing is ever filtered by it.
//  Get lat/lon by right-clicking his city in Google Maps.
//  Zoom 8 ≈ a 150-mile region; 10 ≈ one metro area.
//  (Keep this in sync with the "home" block in ../config.json.)
// ============================================================
window.POKER_MAP_CONFIG = {
  home: {
    label: "Cleveland, OH",
    lat: 41.4993,
    lon: -81.6944,
    zoom: 8
  }
};
