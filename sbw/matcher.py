"""Score how likely a marketplace listing is a specific stolen bike.

Evidence is added up as rough log-odds points. Every point comes with a
human-readable reason so a person can see why something was flagged.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache

from .catalog import (BRAND_ALIASES, CATEGORY_WORDS, COLOR_SYNONYMS, MODELS,
                      PARTS_WORDS, URGENCY_WORDS)
from .geo import km_between

STOPWORDS = {"a", "an", "the", "on", "with", "and", "bike"}
SIZE_WORDS = {"xs": "XS", "extra small": "XS", "small": "S", "medium": "M",
              "large": "L", "extra large": "XL", "xl": "XL"}
GENERIC_MODEL_WORDS = {"fat", "bike", "mountain", "road", "city", "electric", "e", "pro", "sport",
                       "hybrid", "cruiser", "kids", "junior", "mini", "classic", "comp"}
SERIAL_RE = re.compile(r"\b(?=[a-z0-9]*\d)(?=[a-z0-9]*[a-z])[a-z0-9]{9,}\b")

W = {
    "serial_match": 10.0, "serial_conflict": -6.0,
    "brand": 2.0, "brand_fuzzy": 1.5, "brand_conflict": -3.0,
    "model": 1.5, "model_partial": 1.0, "model_conflict": -1.0,
    "color": 1.0, "color_conflict": -0.5,
    "size": 0.5, "size_conflict": -1.5,
    "category": 0.3, "category_conflict": -1.0,
    "feature": 1.2,
    "cheap": 0.8, "cheapish": 0.3, "urgency": 0.3,
}


@dataclass
class Match:
    listing: dict
    score: float
    distance_km: float
    reasons: list = field(default_factory=list)
    distinguishing: bool = False  # evidence beyond make/model/colour
    model_hit: bool = False
    is_parts: bool = False

    @property
    def tier(self):
        if self.score >= 8:
            return "near-certain"
        if self.score >= 4 and self.distinguishing:
            return "strong"
        # A parts listing needs the owner's features; brand + colour alone
        # describes hundreds of listings.
        if self.score >= 3 and not self.is_parts and (self.model_hit or self.distinguishing):
            return "worth a look"
        return None


def norm(text):
    return re.sub(r"[^a-z0-9\-\. ]+", " ", text.lower())


def haystack(listing):
    return norm(" ".join([listing["title"], listing["description"],
                          " ".join(listing.get("photo_tags", []))]))


def has_phrase(text, phrase):
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def find_colors(text):
    return {c for c, syns in COLOR_SYNONYMS.items() if any(has_phrase(text, s) for s in syns)}


def find_size(text):
    m = re.search(r"\bsize\s+(xs|s|m|l|xl)\b", text) or re.search(r"\b(xs|s|m|l|xl)\s*$", text)
    if m:
        return m.group(1).upper()
    for word, size in SIZE_WORDS.items():
        if has_phrase(text, word):
            return size
    m = re.search(r"\b(4[4-9]|5\d|6[0-2])\s?(cm)?\b", text)
    return m.group(1) if m else None


@lru_cache(maxsize=None)
def find_brands(text):
    found = {b for b, aliases in BRAND_ALIASES.items() if any(has_phrase(text, a) for a in aliases)}
    fuzzy = set()
    tokens = set(text.split())
    for brand, aliases in BRAND_ALIASES.items():
        if brand in found:
            continue
        for alias in aliases:
            if " " in alias or len(alias) < 4:
                continue
            if any(len(t) >= 4 and abs(len(t) - len(alias)) <= 2
                   and SequenceMatcher(None, t, alias).ratio() >= 0.75 for t in tokens):
                fuzzy.add(brand)
    return found, fuzzy


def find_category(text):
    return {cat for cat, words in CATEGORY_WORDS.items() if any(has_phrase(text, w) for w in words)}


def feature_credit(feature, text):
    tokens = [t for t in norm(feature).split() if t not in STOPWORDS]
    if not tokens:
        return 0.0
    frac = sum(1 for t in tokens if has_phrase(text, t)) / len(tokens)
    return frac if frac >= 0.5 else 0.0


COMMON_FEATURE_SHARE = 0.03  # feature shows up in >3% of listings -> not distinguishing


def feature_rarity(report, listings):
    """Per feature, the credit every listing would earn for it. Kickstands are everywhere,
    and half of "rear rack" (just "rack") is everywhere too."""
    texts = [haystack(l) for l in listings]
    return {f: [feature_credit(f, t) for t in texts] for f in report.get("features", [])}


def share_at(credits, credit):
    """Share of listings that match a feature at least this well."""
    return sum(1 for c in credits if c >= credit) / max(len(credits), 1)


def score(report, listing, radius_km=100, max_days=120, rarity=None):
    """Return a Match, or None if the listing fails the hard gates."""
    stolen_on = date.fromisoformat(report["date_stolen"])
    posted_on = date.fromisoformat(listing["posted_at"])
    if not (0 <= (posted_on - stolen_on).days <= max_days):
        return None
    dist = km_between(report["stolen_coordinates"], (listing["lat"], listing["lng"]))
    if dist > radius_km:
        return None

    text = haystack(listing)
    brand = report["manufacturer_name"].lower()
    model = (report.get("frame_model") or "").lower()
    category, used_value = MODELS.get((brand, model), (None, None))
    m = Match(listing, 0.0, dist)

    def add(key, why, credit=1.0):
        m.score += W[key] * credit
        m.reasons.append(f"{W[key] * credit:+.1f} {why}")

    # Serial number: the only thing that proves it outright.
    serial = re.sub(r"[^a-z0-9]", "", (report.get("serial") or "").lower())
    if len(serial) >= 5 and serial in text.replace(" ", "").replace("-", ""):
        add("serial_match", "serial number matches")
    else:
        other = [s for s in SERIAL_RE.findall(text) if s != serial]
        if other:
            add("serial_conflict", f"listing shows a different serial ({other[0].upper()})")

    # Brand and model.
    brands, fuzzy_brands = find_brands(text)
    if brand in brands:
        add("brand", f"brand {report['manufacturer_name']}")
    elif brand in fuzzy_brands:
        add("brand_fuzzy", "brand misspelled but close")
    elif brands:
        add("brand_conflict", f"different brand ({', '.join(sorted(brands))})")

    if not model:
        pass
    elif has_phrase(text, model):
        add("model", f"model {report['frame_model']}")
        m.model_hit = True
    elif (len(model.split()[0]) >= 3 and model.split()[0] not in GENERIC_MODEL_WORDS
          and has_phrase(text, model.split()[0])):
        add("model_partial", f"model name '{model.split()[0]}'")
        m.model_hit = True
    elif brand in brands:
        others = [mo for (b, mo) in MODELS if b == brand and mo != model and has_phrase(text, mo.split()[0])]
        if others:
            add("model_conflict", f"different model ({others[0]})")

    is_parts = listing.get("is_parts") or any(has_phrase(text, w) for w in PARTS_WORDS)
    m.is_parts = bool(is_parts)

    # Colour: a mismatch is weak evidence, bikes get repainted.
    colors = set() if is_parts else find_colors(text)
    if colors & set(report["frame_colors"]):
        add("color", f"colour {', '.join(sorted(colors & set(report['frame_colors'])))}")
    elif colors:
        add("color_conflict", f"colour {', '.join(sorted(colors))} (repaint possible)")

    size = find_size(text)
    if size and report.get("frame_size"):
        if size == report["frame_size"]:
            add("size", f"size {size}")
        else:
            add("size_conflict", f"size {size} vs {report['frame_size']}")

    cats = find_category(text)
    if category and cats and not is_parts:
        if category in cats:
            add("category", f"{category} bike")
        else:
            add("category_conflict", f"listed as {', '.join(sorted(cats))}, stolen bike is {category}")

    # Distinguishing features: what survives a repaint or a part-out.
    for feature in report.get("features", []):
        credit = feature_credit(feature, text)
        if not credit:
            continue
        label = f"feature '{feature}'" + ("" if credit == 1 else f" ({credit:.0%})")
        share = share_at(rarity[feature], credit) if rarity else 0
        if share > COMMON_FEATURE_SHARE:
            add("feature", f"{label}, common ({share:.0%} of listings)", credit * 0.3)
        else:
            add("feature", label, credit)
            m.distinguishing = True

    # Price and tone.
    if used_value and not is_parts:
        if listing["price"] < 0.5 * used_value:
            add("cheap", f"${listing['price']} vs ~${used_value} typical")
            m.distinguishing = True
        elif listing["price"] < 0.7 * used_value:
            add("cheapish", f"${listing['price']} vs ~${used_value} typical")
    if any(has_phrase(text, w) for w in URGENCY_WORDS):
        add("urgency", "urgent-sale wording")

    if is_parts:
        m.reasons.append("  (parts listing: judged on features only)")
    return m


def baseline_hit(report, listing, radius_km=100, max_days=120):
    """What a saved-search alert does: brand + model keyword, in the area, after the theft."""
    stolen_on = date.fromisoformat(report["date_stolen"])
    posted_on = date.fromisoformat(listing["posted_at"])
    if not (0 <= (posted_on - stolen_on).days <= max_days):
        return False
    if km_between(report["stolen_coordinates"], (listing["lat"], listing["lng"])) > radius_km:
        return False
    text = haystack(listing)
    model = (report.get("frame_model") or "").lower()
    return (has_phrase(text, report["manufacturer_name"].lower())
            and bool(model) and has_phrase(text, model.split()[0]))


def watch(report, listings, radius_km=100):
    """All flagged listings for one report, best first."""
    rarity = feature_rarity(report, listings)
    hits = [m for m in (score(report, l, radius_km, rarity=rarity) for l in listings) if m and m.tier]
    return sorted(hits, key=lambda m: (-m.distinguishing, -m.score))
