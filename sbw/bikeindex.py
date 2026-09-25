"""Stolen-bike reports from the public Bike Index API (https://bikeindex.org/documentation/api_v3)."""
import json
import time
import urllib.parse
import urllib.request
from datetime import date

API = "https://bikeindex.org/api/v3"
UA = "stolen-bike-watcher (+https://github.com/fisherjoey/stolen-bike-watcher)"
COLOR_MAP = {"Silver, gray or bare metal": "grey", "Yellow or Gold": "yellow", "Teal": "blue",
             "Stickers tape or other cover-up": None}
NO_SERIAL = ("unknown", "hidden", "made_without", "made without")


def _get(path, **params):
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30))


def stolen_near(location, distance_km=60, limit=100, pause=0.3, log=print):
    """Full records for bikes reported stolen near `location`, most recent first."""
    ids = [b["id"] for b in _get("/search", location=location, distance=round(distance_km / 1.609),
                                  stolenness="proximity", per_page=limit)["bikes"]]
    bikes = []
    for i, bid in enumerate(ids, 1):
        bikes.append(_get(f"/bikes/{bid}")["bike"])
        if i % 25 == 0:
            log(f"fetched {i}/{len(ids)}")
        time.sleep(pause)
    return bikes


def report_text(bike):
    """The raw fields the feature extractor reads."""
    stolen = bike.get("stolen_record") or {}
    return {
        "id": bike["id"], "manufacturer": bike["manufacturer_name"], "model": bike.get("frame_model"),
        "year": bike.get("year"), "colors": bike.get("frame_colors"), "paint": bike.get("paint_description"),
        "size": bike.get("frame_size"), "cycle": bike.get("type_of_cycle"),
        "propulsion": bike.get("propulsion_type_slug"), "description": bike.get("description"),
        "theft": stolen.get("theft_description"),
        "components": [" ".join(filter(None, [c.get("manufacturer_name"), c.get("component_type"),
                                              c.get("model_name"), c.get("description")]))
                       for c in bike.get("components") or []],
    }


def to_report(bike, extracted):
    """The matcher's report shape, or None if the report can't be matched on."""
    if not extracted.get("brand") or not bike.get("date_stolen") or not bike.get("stolen_coordinates"):
        return None
    size = (bike.get("frame_size") or "").lower()
    if size in {"xs", "s", "m", "l", "xl"}:
        size = size.upper()
    elif size.endswith("cm"):
        size = size.removesuffix("cm")
    else:
        size = None  # "29in" and similar are wheel sizes, not frame sizes
    serial = bike.get("serial") or ""
    colors = [COLOR_MAP.get(c, c.lower()) for c in bike["frame_colors"]]
    return {
        "id": bike["id"], "url": bike["url"],
        "manufacturer_name": extracted["brand"], "frame_model": extracted.get("model"),
        "frame_colors": [c for c in colors if c], "frame_size": size,
        "serial": "" if any(w in serial.lower() for w in NO_SERIAL) else serial,
        "stolen_coordinates": bike["stolen_coordinates"], "stolen_city": bike.get("stolen_location"),
        "date_stolen": date.fromtimestamp(bike["date_stolen"]).isoformat(),
        "features": extracted.get("features", []),
    }
