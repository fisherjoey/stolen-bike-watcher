import math

CITIES = {
    "Calgary": (51.045, -114.057),
    "Airdrie": (51.292, -114.014),
    "Cochrane": (51.189, -114.467),
    "Okotoks": (50.726, -113.975),
    "Chestermere": (51.050, -113.822),
    "Canmore": (51.089, -115.358),
    "Red Deer": (52.268, -113.811),
    "Lethbridge": (49.694, -112.842),
    "Edmonton": (53.546, -113.494),
}


def km_between(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))
