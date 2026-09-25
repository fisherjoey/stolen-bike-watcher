"""Fetch Kijiji search results from the page's embedded Next.js data."""
import json
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
CALGARY = 1700199
BIKES = 644


def search(keywords, location_id=CALGARY, page=1):
    slug = urllib.parse.quote(keywords.lower().replace(" ", "-"))
    suffix = f"/page-{page}" if page > 1 else ""
    url = f"https://www.kijiji.ca/b-bikes/calgary/{slug}{suffix}/k0c{BIKES}l{location_id}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    root = json.loads(m.group(1))["props"]["pageProps"]["__APOLLO_STATE__"]
    page_data = next(v for k, v in root["ROOT_QUERY"].items() if k.startswith("searchResultsPageByUrl"))
    results = page_data["results"]
    raw = []
    for k, v in results.items():
        if k.startswith(("mainListings", "topListings")) and isinstance(v, list):
            raw += v
    # Listings may be inline or Apollo refs.
    return [root.get(x["__ref"], x) if isinstance(x, dict) and "__ref" in x else x for x in raw]
