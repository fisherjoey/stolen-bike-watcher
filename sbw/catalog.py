"""Tiny mock bike catalogue. Stands in for a real make/model database.

used_value is a rough CAD resale price for a bike in good shape, used to spot
suspiciously cheap listings.
"""

BRAND_ALIASES = {
    "trek": ["trek", "trec", "treck"],
    "specialized": ["specialized", "specialised", "spesh", "speshy"],
    "cannondale": ["cannondale", "cannondal", "canondale", "cdale"],
    "rocky mountain": ["rocky mountain", "rockymountain", "rocky mtn"],
    "giant": ["giant"],
    "norco": ["norco"],
    "kona": ["kona"],
    "santa cruz": ["santa cruz"],
    "devinci": ["devinci"],
    "raleigh": ["raleigh"],
}

# (brand, model) -> category, used_value
MODELS = {
    ("trek", "marlin 7"): ("mtb", 800),
    ("trek", "fx 2"): ("hybrid", 550),
    ("trek", "domane al 2"): ("road", 800),
    ("specialized", "sirrus x 3.0"): ("hybrid", 900),
    ("specialized", "rockhopper"): ("mtb", 600),
    ("specialized", "allez"): ("road", 800),
    ("cannondale", "topstone 2"): ("gravel", 1400),
    ("cannondale", "trail 5"): ("mtb", 650),
    ("rocky mountain", "element 30"): ("mtb", 2400),
    ("rocky mountain", "soul"): ("mtb", 450),
    ("giant", "escape 3"): ("hybrid", 350),
    ("giant", "talon 2"): ("mtb", 600),
    ("giant", "contend 3"): ("road", 700),
    ("norco", "storm 2"): ("mtb", 550),
    ("norco", "fluid fs 3"): ("mtb", 1800),
    ("kona", "rove"): ("gravel", 1100),
    ("kona", "dew"): ("hybrid", 450),
    ("santa cruz", "chameleon"): ("mtb", 2200),
    ("devinci", "milano"): ("hybrid", 500),
    ("raleigh", "cadent 2"): ("hybrid", 400),
}

CATEGORY_WORDS = {
    "mtb": ["mountain", "mtb", "trail", "hardtail", "full suspension", "enduro"],
    "road": ["road bike", "road", "racing", "drop bar"],
    "gravel": ["gravel", "cyclocross", "cx", "adventure"],
    "hybrid": ["hybrid", "commuter", "city bike", "fitness"],
}

COLOR_SYNONYMS = {
    "grey": ["grey", "gray", "charcoal", "silver", "gunmetal"],
    "black": ["black", "matte black", "stealth"],
    "red": ["red", "crimson", "maroon"],
    "blue": ["blue", "navy", "teal"],
    "green": ["green", "olive", "alpine", "sage"],
    "white": ["white"],
    "orange": ["orange"],
    "yellow": ["yellow", "gold"],
    "brown": ["brown", "tan", "bronze"],
    "purple": ["purple", "violet"],
    "pink": ["pink"],
}

PARTS_WORDS = [
    "wheelset", "wheels", "groupset", "frame only", "frameset", "fork only",
    "parts", "crankset", "derailleur", "bundle",
]

URGENCY_WORDS = [
    "quick sale", "must go", "must sell", "cash only", "today only",
    "moving sale", "no questions", "firm today",
]
