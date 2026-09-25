"""Read Kijiji bike listings from the Next.js data embedded in its pages.

Kijiji has no public API. Search and listing pages carry their data as JSON in
a <script id="__NEXT_DATA__"> tag, which is what this reads. Be polite: one
request at a time, with a pause between pages.
"""
import json
import re
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
BIKES_CATEGORY = 644
PARTS_CATEGORIES = ["bike-frames-parts", "bike-clothes-shoes-accessories"]


def _state(url):
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(m.group(1))["props"]["pageProps"]["__APOLLO_STATE__"]


def _results(state):
    page = next(v for k, v in state["ROOT_QUERY"].items() if k.startswith("searchResultsPageByUrl"))
    raw = [x for k, v in page["results"].items()
           if k.startswith(("mainListings", "topListings")) and isinstance(v, list) for x in v]
    # Listings are either inline or Apollo cache references.
    return [state.get(x["__ref"], x) if "__ref" in x else x for x in raw]


def search_url(city_slug, location_id, keywords=None, page=1):
    slug = f"/{urllib.parse.quote(keywords.lower().replace(' ', '-'))}" if keywords else ""
    suffix = f"/page-{page}" if page > 1 else ""
    code = f"k0c{BIKES_CATEGORY}" if keywords else f"c{BIKES_CATEGORY}"
    return f"https://www.kijiji.ca/b-bikes/{city_slug}{slug}{suffix}/{code}l{location_id}?sort=dateDesc"


def search(city_slug, location_id, keywords=None, page=1):
    return _results(_state(search_url(city_slug, location_id, keywords, page)))


def sweep(city_slug, location_id, since, max_pages=100, pause=1.5, log=print):
    """Every bike listing in the region, newest first, back to `since` (YYYY-MM-DD).

    Pages sort by sortingDate, which resets when a seller bumps an old ad, so
    that is the date to stop on. activationDate is when the ad first went up.
    """
    seen, rows = set(), []
    for page in range(1, max_pages + 1):
        new = [x for x in search(city_slug, location_id, page=page) if x["id"] not in seen]
        seen.update(x["id"] for x in new)
        rows += new
        dates = [x["sortingDate"][:10] for x in new if x.get("adSource") != "TOP_AD"]
        log(f"page {page}: {len(new)} listings, oldest {min(dates) if dates else '-'}")
        if not new or (dates and min(dates) < since):
            break
        time.sleep(pause)
    return rows


def detail(url):
    """Full description and photo URLs for one listing, or None if it's gone."""
    state = _state(url)
    lid = url.rstrip("/").split("/")[-1]
    node = next((v for k, v in state.items()
                 if k.endswith(lid) and isinstance(v, dict) and "description" in v), None)
    if node is None:
        return None
    return {"title": node.get("title"), "description": node.get("description"),
            "images": node.get("imageUrls") or []}


def to_listing(raw):
    """Convert a raw Kijiji listing to the matcher's listing shape, or None without coordinates."""
    attrs = {a["canonicalName"]: a["canonicalValues"] for a in (raw.get("attributes") or {}).get("all", [])}
    size = attrs.get("framesize", [None])[0]
    coords = (raw.get("location") or {}).get("coordinates") or {}
    if not coords:
        return None
    price = (raw.get("price") or {}).get("amount")
    return {
        "id": f"kijiji:{raw['id']}", "source": "kijiji", "url": raw["url"], "title": raw["title"],
        "description": (raw.get("description") or "") + (f" size {size}" if size else ""),
        "price": (price or 0) / 100, "city": raw["location"].get("name"),
        "lat": coords["latitude"], "lng": coords["longitude"],
        "posted_at": raw["activationDate"][:10], "photo_tags": [],
        "is_parts": any(f"/v-{c}/" in raw["url"] for c in PARTS_CATEGORIES),
    }
