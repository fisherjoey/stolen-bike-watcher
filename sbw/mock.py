"""Generate mock stolen reports + marketplace listings + ground-truth labels.

Hand-written hard cases sit on top of ~200 seeded random filler listings.
photo_tags simulates what a vision model would pull out of listing photos;
nothing here looks at real images.
"""
import json
import random
from pathlib import Path

from .catalog import MODELS
from .geo import CITIES

REPORTS = [
    {
        "id": "R1", "manufacturer_name": "Trek", "frame_model": "Marlin 7", "year": 2022,
        "frame_colors": ["red", "black"], "frame_size": "L", "serial": "WTU284C0412K",
        "stolen_city": "Calgary", "date_stolen": "2026-09-10",
        "features": ["white fizik saddle", "calgary bike co-op sticker", "bent front rotor",
                     "shimano deore"],
    },
    {
        "id": "R2", "manufacturer_name": "Specialized", "frame_model": "Sirrus X 3.0", "year": 2023,
        "frame_colors": ["black"], "frame_size": "M", "serial": "WSBC604177311",
        "stolen_city": "Calgary", "date_stolen": "2026-09-15",
        "features": ["rear rack", "full fenders", "brass bell", "ergon grips"],
    },
    {
        "id": "R3", "manufacturer_name": "Cannondale", "frame_model": "Topstone 2", "year": 2021,
        "frame_colors": ["green"], "frame_size": "54", "serial": "CD21TS009931",
        "stolen_city": "Airdrie", "date_stolen": "2026-09-01",
        "features": ["orange bar tape", "tubeless wheels", "frame bag", "wtb riddler tires"],
    },
    {
        "id": "R4", "manufacturer_name": "Rocky Mountain", "frame_model": "Element 30", "year": 2020,
        "frame_colors": ["blue"], "frame_size": "L", "serial": "RM20E30L7781",
        "stolen_city": "Cochrane", "date_stolen": "2026-08-20",
        "features": ["fox fork", "dropper post", "maxxis minion tires", "purple pedals"],
    },
    {
        "id": "R5", "manufacturer_name": "Giant", "frame_model": "Escape 3", "year": 2019,
        "frame_colors": ["grey"], "frame_size": "M", "serial": "GT19E3M22K",
        "stolen_city": "Calgary", "date_stolen": "2026-09-18",
        "features": ["kickstand", "black wire basket"],
    },
]

# (listing, truth) — truth is the report id this listing really is, or None.
HARD_CASES = [
    # R1: honest-ish listing, cheap
    ({"source": "kijiji", "title": "Trek Marlin 7 red large - quick sale",
      "description": "Red/black Trek Marlin 7 size L. Fizik saddle, Deore drivetrain. "
                     "Front rotor rubs a little. $300 firm, cash only.",
      "price": 300, "city": "Calgary", "posted_at": "2026-09-12",
      "photo_tags": ["red frame", "white saddle", "sticker on top tube", "hardtail"]}, "R1"),
    # R1: cross-post on FB, brand misspelled, no model
    ({"source": "fb_marketplace", "title": "Trec mountain bike",
      "description": "good bike rides well rotor needs tune. must go",
      "price": 250, "city": "Calgary", "posted_at": "2026-09-13",
      "photo_tags": ["red frame", "black accents", "white saddle", "co-op sticker", "hardtail"]}, "R1"),
    # R2: repainted grey, rack/fenders/bell kept
    ({"source": "fb_marketplace", "title": "Specialized hybrid, size M, rack + fenders",
      "description": "Matte grey Specialized commuter. Rear rack, full fenders, bell, "
                     "Ergon grips. Ready to ride.",
      "price": 350, "city": "Chestermere", "posted_at": "2026-09-20",
      "photo_tags": ["grey frame", "rear rack", "fenders", "bell", "flat bar"]}, "R2"),
    # R3: parted out — wheels + bar tape bundle, no brand
    ({"source": "kijiji", "title": "700c tubeless gravel wheels + orange bar tape bundle",
      "description": "Tubeless wheels with WTB Riddler tires, plus a roll of orange bar tape "
                     "and a frame bag. Selling as bundle.",
      "price": 120, "city": "Calgary", "posted_at": "2026-09-06",
      "photo_tags": ["wheels", "wtb tires", "orange bar tape", "frame bag"]}, "R3"),
    # R3: the frame turns up in Edmonton (outside default radius)
    ({"source": "kijiji", "title": "Cannondale Topstone gravel bike green 54",
      "description": "Green Cannondale Topstone 2, 54cm. New wheels. $600.",
      "price": 600, "city": "Edmonton", "posted_at": "2026-09-14",
      "photo_tags": ["green frame", "black bar tape", "drop bar"]}, "R3"),
    # R4: no brand at all, only photos give it away
    ({"source": "fb_marketplace", "title": "Full suspension mountain bike blue",
      "description": "Great shape, dropper, Fox fork. Must go today $400",
      "price": 400, "city": "Calgary", "posted_at": "2026-08-24",
      "photo_tags": ["blue frame", "full suspension", "fox fork", "purple pedals", "minion tires"]}, "R4"),
]

# Legit look-alikes. A naive keyword alert fires on all of these.
DECOYS = [
    ({"source": "kijiji", "title": "Trek Marlin 7 2022 blue medium",
      "description": "Original owner, receipt available. Blue, size M, Deore.",
      "price": 750, "city": "Calgary", "posted_at": "2026-09-14",
      "photo_tags": ["blue frame", "black saddle", "hardtail"]}, None),
    ({"source": "fb_marketplace", "title": "Trek Marlin 7 red small",
      "description": "Kids outgrew it. Red, size S, stock saddle. Serial WTU991A1180K.",
      "price": 650, "city": "Airdrie", "posted_at": "2026-09-16",
      "photo_tags": ["red frame", "black saddle", "hardtail"]}, None),
    ({"source": "fb_marketplace", "title": "Specialized Sirrus X 3.0 black M",
      "description": "Black Sirrus X, size M. Selling because I got an e-bike. $600.",
      "price": 600, "city": "Calgary", "posted_at": "2026-09-16",
      "photo_tags": ["black frame", "flat bar"]}, None),
    ({"source": "kijiji", "title": "Cannondale Topstone 2 green",
      "description": "Green Topstone 2, size 56, black bar tape. Listed since spring.",
      "price": 1300, "city": "Calgary", "posted_at": "2026-08-15",
      "photo_tags": ["green frame", "black bar tape", "drop bar"]}, None),
    ({"source": "kijiji", "title": "Rocky Mountain Element 30 blue L",
      "description": "Rocky Element, blue, L. Fox fork, dropper. Stored indoors. $2300.",
      "price": 2300, "city": "Canmore", "posted_at": "2026-08-10",
      "photo_tags": ["blue frame", "full suspension", "fox fork", "black pedals"]}, None),
    ({"source": "fb_marketplace", "title": "Giant Escape 3 grey M",
      "description": "Grey Giant Escape commuter, kickstand, no basket. $300.",
      "price": 300, "city": "Calgary", "posted_at": "2026-09-20",
      "photo_tags": ["grey frame", "kickstand", "flat bar"]}, None),
    ({"source": "kijiji", "title": "Giant Escape 3 hybrid",
      "description": "Grey Escape 3, size M, basket and kickstand included.",
      "price": 320, "city": "Okotoks", "posted_at": "2026-09-21",
      "photo_tags": ["grey frame", "kickstand", "wire basket", "silver basket"]}, None),
]

COLORS = ["red", "black", "blue", "green", "grey", "white", "orange", "yellow"]
SIZES = ["XS", "S", "M", "L", "XL"]
FILLER_EXTRAS = ["kickstand", "bell", "rack", "fenders", "dropper post", "new tires",
                 "clipless pedals", "lights", "bottle cage", "tubeless"]
CITY_WEIGHTS = {"Calgary": 10, "Airdrie": 2, "Cochrane": 2, "Okotoks": 2, "Chestermere": 1,
                "Canmore": 1, "Red Deer": 2, "Lethbridge": 2, "Edmonton": 6}


def filler(rng, n):
    models = list(MODELS.items())
    cities = list(CITY_WEIGHTS)
    weights = list(CITY_WEIGHTS.values())
    out = []
    for _ in range(n):
        (brand, model), (cat, value) = rng.choice(models)
        color = rng.choice(COLORS)
        size = rng.choice(SIZES)
        extras = rng.sample(FILLER_EXTRAS, k=rng.randint(0, 3))
        price = int(value * rng.uniform(0.55, 1.2) / 10) * 10
        day = rng.randint(1, 25)
        month = rng.choice([8, 9])
        title_brand = brand.title() if rng.random() > 0.15 else ""
        out.append(({
            "source": rng.choice(["kijiji", "fb_marketplace"]),
            "title": f"{title_brand} {model.title()} {color} {size}".strip(),
            "description": f"{color.title()} {cat} bike, size {size}. "
                           + (", ".join(extras) + "." if extras else "Stock."),
            "price": price,
            "city": rng.choices(cities, weights)[0],
            "posted_at": f"2026-{month:02d}-{day:02d}",
            "photo_tags": [f"{color} frame"] + extras,
        }, None))
    return out


def build(out: Path):
    rng = random.Random(42)
    rows = HARD_CASES + DECOYS + filler(rng, 200)
    rng.shuffle(rows)
    listings, labels = [], {}
    for i, (listing, truth) in enumerate(rows):
        lid = f"L{i:03d}"
        lat, lng = CITIES[listing["city"]]
        listings.append({"id": lid, **listing, "lat": lat, "lng": lng})
        if truth:
            labels[lid] = truth
    reports = [{**r, "stolen_coordinates": list(CITIES[r["stolen_city"]])} for r in REPORTS]

    out.mkdir(parents=True, exist_ok=True)
    (out / "stolen_reports.json").write_text(json.dumps(reports, indent=2))
    (out / "listings.json").write_text(json.dumps(listings, indent=2))
    (out / "labels.json").write_text(json.dumps(labels, indent=2))
    print(f"{len(reports)} reports, {len(listings)} listings, {len(labels)} true matches")

