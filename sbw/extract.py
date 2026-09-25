"""Turn messy Bike Index report text into clean brand, model and distinguishing features.

Owners type anything into these fields ("Stolen 09/15/26", "Norco Bikes",
a model field that just repeats the brand), so a language model does the
cleanup. Any command that reads a prompt on stdin and prints text works; the
default is the Claude Code CLI. Without one, `fallback` gives a rough version
with no features.
"""
import json
import re
import shlex
import subprocess

PROMPT = """You get Bike Index stolen-bike reports as JSON. For each report, output what a matcher needs to recognise the bike in a used-bike listing (title, description, photos).

Return ONLY a JSON array, one object per report, same order, with keys:
- "id": the report id
- "brand": clean brand name as a seller would write it ("Norco" not "Norco Bikes", "Aventon" not "Aventón"), or null if unknown
- "model": clean model name as a seller would write it (e.g. "Marlin 5", "Shuttle LT"), or null if the field is junk (a brand repeat, a year, a code, "mountain / hybrid")
- "category": one of mtb, road, gravel, hybrid, cruiser, ebike, bmx, kids, folding, other
- "features": 0-6 short phrases (2-4 words, lowercase) for things that would show in a listing or photo and set THIS bike apart: added accessories, aftermarket parts, damage, stickers, unusual colours or paint details. Exclude generic stock traits (disc brakes, 21 speed, aluminium frame), exclude the brand/model/colour already given, exclude things that were not on the bike ("bags not on bike"). Empty list if nothing distinctive is known.

Reports:
"""

BRAND_SUFFIXES = re.compile(r"\s+(bikes|bicycles|cycles|bicycle company)$", re.I)


def with_llm(reports, command="claude -p", timeout=600):
    out = subprocess.run(shlex.split(command), input=PROMPT + json.dumps(reports, indent=1),
                         capture_output=True, text=True, timeout=timeout, check=True).stdout
    return json.loads(out[out.index("["):out.rindex("]") + 1])


def fallback(reports):
    rows = []
    for r in reports:
        brand = BRAND_SUFFIXES.sub("", r["manufacturer"] or "").strip() or None
        model = (r.get("model") or "").strip()
        junk = not model or model.lower() == (brand or "").lower() or model.isdigit()
        rows.append({"id": r["id"], "brand": brand, "model": None if junk else model,
                     "category": None, "features": []})
    return rows
