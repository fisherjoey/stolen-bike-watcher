"""Sweep every Calgary-region Kijiji bike listing, newest first, back to a cutoff date."""
import json
import re
import sys
import time
import urllib.request

from sbw.kijiji import UA

CUTOFF = sys.argv[1] if len(sys.argv) > 1 else "2026-07-01"
seen, rows = set(), []
for page in range(1, 101):
    suffix = f"/page-{page}" if page > 1 else ""
    url = f"https://www.kijiji.ca/b-bikes/calgary{suffix}/c644l1700199?sort=dateDesc"
    html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode()
    root = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S).group(1))
    state = root["props"]["pageProps"]["__APOLLO_STATE__"]
    res = next(v for k, v in state["ROOT_QUERY"].items() if k.startswith("searchResultsPageByUrl"))["results"]
    batch = [x for k, v in res.items() if k.startswith(("mainListings", "topListings")) and isinstance(v, list) for x in v]
    batch = [state.get(x["__ref"], x) if "__ref" in x else x for x in batch]
    new = [x for x in batch if x["id"] not in seen]
    for x in new:
        seen.add(x["id"])
    rows += new
    main_dates = [x["sortingDate"][:10] for x in new if x.get("adSource") != "TOP_AD"]
    print(page, len(new), min(main_dates) if main_dates else "-", flush=True)
    if not new or (main_dates and min(main_dates) < CUTOFF):
        break
    time.sleep(1.5)
json.dump(rows, open("data/real/kijiji_raw.json", "w"), indent=1)
print("total", len(rows))
