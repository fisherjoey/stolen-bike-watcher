"""Run the watcher on real Bike Index reports against real marketplace listings."""
import json
import sys
from datetime import date
from pathlib import Path

from sbw.catalog import BRAND_ALIASES
from sbw.matcher import baseline_hit, watch

REAL = Path(__file__).parent / "data" / "real"
PARTS_CATEGORIES = ["bike-frames-parts", "bike-clothes-shoes-accessories"]
COLOR_MAP = {"Silver, gray or bare metal": "grey", "Yellow or Gold": "yellow", "Teal": "blue",
             "Stickers tape or other cover-up": None}


def reports():
    bikes = {b["id"]: b for b in json.loads((REAL / "bi_bikes.json").read_text())}
    out = []
    for e in json.loads((REAL / "extracted.json").read_text()):
        b = bikes[e["id"]]
        if not e["brand"] or not b.get("date_stolen") or not b.get("stolen_coordinates"):
            continue
        size = (b.get("frame_size") or "").lower()
        size = size.upper() if size in {"xs", "s", "m", "l", "xl"} else size.removesuffix("cm") if size.endswith("cm") else None
        serial = b.get("serial") or ""
        colors = [COLOR_MAP.get(c, c.lower()) for c in b["frame_colors"]]
        out.append({
            "id": b["id"], "url": b["url"], "manufacturer_name": e["brand"], "frame_model": e["model"],
            "frame_colors": [c for c in colors if c], "frame_size": size,
            "serial": "" if any(w in serial.lower() for w in ("unknown", "hidden", "made_without")) else serial,
            "stolen_coordinates": b["stolen_coordinates"], "stolen_city": b.get("stolen_location"),
            "date_stolen": date.fromtimestamp(b["date_stolen"]).isoformat(), "features": e["features"],
        })
    return out


def kijiji_listings():
    out = []
    for x in json.loads((REAL / "kijiji_raw.json").read_text()):
        attrs = {a["canonicalName"]: a["canonicalValues"] for a in (x.get("attributes") or {}).get("all", [])}
        size = attrs.get("framesize", [None])[0]
        coords = (x.get("location") or {}).get("coordinates") or {}
        if not coords:
            continue
        price = (x.get("price") or {}).get("amount")
        out.append({
            "id": f"kijiji:{x['id']}", "source": "kijiji", "url": x["url"], "title": x["title"],
            "description": (x.get("description") or "") + (f" size {size}" if size else ""),
            "price": (price or 0) / 100, "city": x["location"].get("name"),
            "lat": coords["latitude"], "lng": coords["longitude"],
            "posted_at": x["activationDate"][:10], "photo_tags": [],
            "is_parts": any(f"/v-{c}/" in x["url"] for c in PARTS_CATEGORIES),
        })
    return out


def main():
    R = reports()
    for r in R:  # so a different known brand counts against a listing
        BRAND_ALIASES.setdefault(r["manufacturer_name"].lower(), [r["manufacturer_name"].lower()])
    L = kijiji_listings()
    extra = REAL / "fb_listings.json"
    if extra.exists():
        L += json.loads(extra.read_text())
    print(f"{len(R)} usable reports, {len(L)} listings")
    flagged, base_total = [], 0
    for r in R:
        base_total += sum(1 for l in L if baseline_hit(r, l, 60))
        for m in watch(r, L, radius_km=60):
            flagged.append((r, m))
    flagged.sort(key=lambda rm: -rm[1].score)
    print(f"saved-search baseline fired {base_total} times; watcher flagged {len(flagged)}\n")
    for r, m in flagged:
        l = m.listing
        print(f"{m.score:4.1f} {m.tier:<12} report {r['id']} {r['manufacturer_name']} {r['frame_model']} "
              f"(stolen {r['date_stolen']})\n     -> {l['title']} | ${l['price']:.0f} | {l['city']} | "
              f"posted {l['posted_at']}\n     {l['url']}")
        if "-v" in sys.argv:
            for why in m.reasons:
                print(f"        {why}")


if __name__ == "__main__":
    main()
