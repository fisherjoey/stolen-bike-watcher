"""Run the watcher against the mock data and compare with a saved-search baseline."""
import argparse
import json
from pathlib import Path

from sbw.matcher import baseline_hit, feature_rarity, score, watch

DATA = Path(__file__).parent / "data"


def load():
    return (json.loads((DATA / "stolen_reports.json").read_text()),
            json.loads((DATA / "listings.json").read_text()),
            json.loads((DATA / "labels.json").read_text()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--radius", type=float, default=100)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    reports, listings, labels = load()

    totals = {"watcher": [0, 0, 0], "baseline": [0, 0, 0]}  # tp, fp, fn
    for r in reports:
        truth = {lid for lid, rid in labels.items() if rid == r["id"]}
        hits = watch(r, listings, args.radius)
        flagged = {m.listing["id"] for m in hits}
        base = {l["id"] for l in listings if baseline_hit(r, l, args.radius)}

        print(f"\n=== {r['id']} {r['manufacturer_name']} {r['frame_model']} "
              f"({', '.join(r['frame_colors'])}) stolen {r['date_stolen']} in {r['stolen_city']}")
        print(f"  true listings: {sorted(truth) or 'none'}")
        for m in hits:
            mark = "TRUE " if m.listing["id"] in truth else "false"
            print(f"  [{mark}] {m.listing['id']} {m.score:5.1f} {m.tier:<13} "
                  f"{m.listing['city']:<11} {m.listing['source']:<15} {m.listing['title']}")
            if args.verbose or m.listing["id"] in truth:
                for why in m.reasons:
                    print(f"          {why}")
        for lid in sorted(truth - flagged):
            l = next(x for x in listings if x["id"] == lid)
            m = score(r, l, args.radius, rarity=feature_rarity(r, listings))
            why = "outside radius or time window" if m is None else f"score {m.score:.1f} below threshold"
            print(f"  [MISS ] {lid} {l['city']:<11} {l['title']}  <- {why}")
        print(f"  baseline alert fired on {len(base)}: "
              f"{len(base & truth)} true, {len(base - truth)} false")

        for name, got in (("watcher", flagged), ("baseline", base)):
            totals[name][0] += len(got & truth)
            totals[name][1] += len(got - truth)
            totals[name][2] += len(truth - got)

    print(f"\n--- totals (radius {args.radius:.0f} km, {len(listings)} listings) ---")
    for name, (tp, fp, fn) in totals.items():
        print(f"  {name:<8} caught {tp}/{tp + fn} true listings, {fp} false flags")


if __name__ == "__main__":
    main()
