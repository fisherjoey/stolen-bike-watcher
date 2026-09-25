"""Fetch one Kijiji listing's full description and photo URLs."""
import json
import re
import urllib.request

from .kijiji import UA


def detail(url):
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode()
    state = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S).group(1))
    state = state["props"]["pageProps"]["__APOLLO_STATE__"]
    lid = url.rstrip("/").split("/")[-1]
    node = next((v for k, v in state.items() if k.endswith(lid) and isinstance(v, dict) and "description" in v), None)
    if node is None:
        return None
    attrs = {a["canonicalName"]: a["canonicalValues"] for a in (node.get("attributes") or {}).get("all", [])}
    return {"title": node.get("title"), "description": node.get("description"),
            "images": node.get("imageUrls") or [], "attributes": attrs}
