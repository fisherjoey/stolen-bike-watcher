"""sbw: watch marketplace listings for bikes reported stolen on Bike Index."""
import argparse
import json
import sys
from pathlib import Path

from . import bikeindex, extract, kijiji, mock
from .evaluate import evaluate
from .run import run

MOCK_DIR = Path("data/mock")
REAL_DIR = Path("data/real")


def cmd_demo(a):
    if not (a.data / "listings.json").exists():
        mock.build(a.data)
    evaluate(a.data, radius=a.radius, verbose=a.verbose)


def cmd_fetch_reports(a):
    bikes = bikeindex.stolen_near(a.location, distance_km=a.distance, limit=a.limit)
    a.data.mkdir(parents=True, exist_ok=True)
    (a.data / "reports.json").write_text(json.dumps(bikes, indent=1))
    print(f"saved {len(bikes)} stolen reports to {a.data / 'reports.json'}")


def cmd_extract(a):
    reports = [bikeindex.report_text(b) for b in json.loads((a.data / "reports.json").read_text())]
    rows = extract.fallback(reports) if a.no_llm else extract.with_llm(reports, a.llm)
    (a.data / "extracted.json").write_text(json.dumps(rows, indent=1))
    with_features = sum(1 for r in rows if r["features"])
    print(f"extracted {len(rows)} reports, {with_features} with distinguishing features")


def cmd_sweep_kijiji(a):
    rows = kijiji.sweep(a.city, a.location_id, since=a.since, max_pages=a.max_pages)
    a.data.mkdir(parents=True, exist_ok=True)
    (a.data / "kijiji.json").write_text(json.dumps(rows, indent=1))
    print(f"saved {len(rows)} listings to {a.data / 'kijiji.json'}")


def cmd_run(a):
    run(a.data, radius_km=a.radius, verbose=a.verbose)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sbw", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("demo", help="run the matcher on generated mock data")
    p.add_argument("--data", type=Path, default=MOCK_DIR)
    p.add_argument("--radius", type=float, default=100, help="km (default 100)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("fetch-reports", help="download stolen reports near a place from Bike Index")
    p.add_argument("location", help='e.g. "Calgary, AB"')
    p.add_argument("--distance", type=float, default=60, help="km (default 60)")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--data", type=Path, default=REAL_DIR)
    p.set_defaults(fn=cmd_fetch_reports)

    p = sub.add_parser("extract", help="clean brand/model and pull out distinguishing features")
    p.add_argument("--llm", default="claude -p", help='command that reads a prompt on stdin (default "claude -p")')
    p.add_argument("--no-llm", action="store_true", help="rough cleanup only, no features")
    p.add_argument("--data", type=Path, default=REAL_DIR)
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("sweep-kijiji", help="download every bike listing in a Kijiji region")
    p.add_argument("--since", required=True, help="stop at listings older than this date (YYYY-MM-DD)")
    p.add_argument("--city", default="calgary", help="Kijiji URL slug (default calgary)")
    p.add_argument("--location-id", type=int, default=1700199, help="Kijiji location id (default Calgary)")
    p.add_argument("--max-pages", type=int, default=100)
    p.add_argument("--data", type=Path, default=REAL_DIR)
    p.set_defaults(fn=cmd_sweep_kijiji)

    p = sub.add_parser("run", help="score the downloaded listings against the downloaded reports")
    p.add_argument("--radius", type=float, default=60, help="km (default 60)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--data", type=Path, default=REAL_DIR)
    p.set_defaults(fn=cmd_run)

    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except FileNotFoundError as e:
        sys.exit(f"missing {e.filename}: run the earlier steps first (see README)")


if __name__ == "__main__":
    main()
