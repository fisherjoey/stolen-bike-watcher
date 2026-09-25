import unittest

from sbw.geo import CITIES
from sbw.matcher import feature_rarity, find_brands, score, watch

REPORT = {
    "id": "R", "manufacturer_name": "Specialized", "frame_model": "Sirrus X 3.0",
    "frame_colors": ["black"], "frame_size": "M", "serial": "WSBC604177311",
    "stolen_coordinates": list(CITIES["Calgary"]), "date_stolen": "2026-09-15",
    "features": ["rear rack", "ergon grips"],
}


def listing(title, description="", city="Calgary", posted="2026-09-20", price=500, tags=()):
    lat, lng = CITIES[city]
    return {"id": title, "source": "kijiji", "title": title, "description": description,
            "price": price, "city": city, "lat": lat, "lng": lng, "posted_at": posted,
            "photo_tags": list(tags)}


class Gates(unittest.TestCase):
    def test_listing_before_theft_is_ignored(self):
        self.assertIsNone(score(REPORT, listing("Specialized Sirrus X 3.0", posted="2026-09-01")))

    def test_listing_outside_radius_is_ignored(self):
        self.assertIsNone(score(REPORT, listing("Specialized Sirrus X 3.0", city="Edmonton")))


class Evidence(unittest.TestCase):
    def test_serial_match_is_near_certain(self):
        m = score(REPORT, listing("bike", "serial WSBC604177311"))
        self.assertEqual(m.tier, "near-certain")

    def test_different_serial_clears_the_listing(self):
        m = score(REPORT, listing("Specialized Sirrus X 3.0 black M", "serial WSBC999999999"))
        self.assertIsNone(m.tier)

    def test_mountain_is_not_a_misspelled_rocky_mountain(self):
        exact, fuzzy = find_brands("full suspension mountain bike")
        self.assertEqual((exact, fuzzy), (set(), set()))

    def test_parts_listing_gets_no_colour_penalty(self):
        m = score(REPORT, listing("wheelset bundle", "orange rims, rear rack, ergon grips"))
        self.assertFalse(any("colour" in r for r in m.reasons))

    def test_common_feature_does_not_count_as_distinguishing(self):
        filler = [listing(f"bike {i}", "rack") for i in range(20)]
        target = listing("Specialized hybrid", "has a rack")
        rarity = feature_rarity(REPORT, filler + [target])
        self.assertFalse(score(REPORT, target, rarity=rarity).distinguishing)

    def test_full_feature_phrase_stays_distinguishing_when_half_is_common(self):
        # 50 listings, so the one real "rear rack" is under the 3% common line.
        filler = [listing(f"bike {i}", "rack") for i in range(50)]
        target = listing("Specialized hybrid", "rear rack")
        rarity = feature_rarity(REPORT, filler + [target])
        self.assertTrue(score(REPORT, target, rarity=rarity).distinguishing)

    def test_repainted_bike_with_features_outranks_clean_lookalike(self):
        repaint = listing("Specialized hybrid M", "matte grey, rear rack, ergon grips", price=350)
        lookalike = listing("Specialized Sirrus X 3.0 black M", "selling, got an e-bike", price=600)
        hits = watch(REPORT, [lookalike, repaint])
        self.assertEqual(hits[0].listing["id"], repaint["id"])


if __name__ == "__main__":
    unittest.main()
