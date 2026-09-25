"""Score real stolen reports against real listings and print what's worth a look."""
import json
from pathlib import Path

from . import bikeindex, kijiji
from .catalog import BRAND_ALIASES
from .matcher import baseline_hit, watch


def load_reports(data_dir):
    bikes = {b["id"]: b for b in json.loads((data_dir / "reports.json").read_text())}
    extracted = json.loads((data_dir / "extracted.json").read_text())
    reports = [bikeindex.to_report(bikes[e["id"]], e) for e in extracted if e["id"] in bikes]
    return [r for r in reports if r]


def load_listings(data_dir):
    listings = []
    raw = data_dir / "kijiji.json"
    if raw.exists():
        listings += [l for l in map(kijiji.to_listing, json.loads(raw.read_text())) if l]
    # Listings from anywhere else, already in the matcher's shape.
    for extra in sorted(data_dir.glob("listings-*.json")):
        listings += json.loads(extra.read_text())
    return listings


def run(data_dir: Path, radius_km=60, verbose=False):
    reports = load_reports(data_dir)
    for r in reports:  # so a listing naming a different known brand counts against it
        BRAND_ALIASES.setdefault(r["manufacturer_name"].lower(), [r["manufacturer_name"].lower()])
    listings = load_listings(data_dir)
    print(f"{len(reports)} usable reports, {len(listings)} listings")

    flagged, baseline = [], 0
    for r in reports:
        baseline += sum(1 for l in listings if baseline_hit(r, l, radius_km))
        flagged += [(r, m) for m in watch(r, listings, radius_km=radius_km)]
    flagged.sort(key=lambda rm: -rm[1].score)
    print(f"saved-search baseline fired {baseline} times; watcher flagged {len(flagged)}\n")

    for r, m in flagged:
        l = m.listing
        print(f"{m.score:4.1f} {m.tier:<12} report {r['id']} {r['manufacturer_name']} "
              f"{r['frame_model'] or ''} (stolen {r['date_stolen']})")
        print(f"     -> {l['title']} | ${l['price']:.0f} | {l['city']} | posted {l['posted_at']}")
        print(f"     {l['url']}\n     report: {r['url']}")
        if verbose:
            for why in m.reasons:
                print(f"        {why}")
