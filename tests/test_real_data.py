"""Regressions from the first run on real data, and the Bike Index / Kijiji converters."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from sbw import bikeindex, extract, kijiji
from sbw.cli import main
from sbw.geo import CITIES
from sbw.matcher import score

REPORT = {
    "id": 1, "manufacturer_name": "Norco", "frame_model": "Storm 4", "frame_colors": ["black"],
    "frame_size": None, "serial": "", "stolen_coordinates": list(CITIES["Calgary"]),
    "date_stolen": "2026-09-05", "features": [],
}


def listing(title, description="", **extra):
    lat, lng = CITIES["Calgary"]
    return {"id": title, "source": "kijiji", "title": title, "description": description, "price": 300,
            "city": "Calgary", "lat": lat, "lng": lng, "posted_at": "2026-09-10", "photo_tags": [], **extra}


class RealDataRegressions(unittest.TestCase):
    def test_blank_serial_matches_nothing(self):
        m = score(REPORT, listing("random bike"))
        self.assertFalse(any("serial" in r for r in m.reasons))

    def test_brand_and_colour_alone_is_not_flagged(self):
        self.assertIsNone(score(REPORT, listing("Norco bike black")).tier)

    def test_accessory_listing_is_not_flagged_on_brand_and_model(self):
        m = score(REPORT, listing("Norco Storm 4 black stock saddle", is_parts=True))
        self.assertIsNone(m.tier)

    def test_generic_model_word_is_not_a_model_match(self):
        report = {**REPORT, "manufacturer_name": "Moose", "frame_model": "Fat Bike 2"}
        m = score(report, listing("fat bike for sale"))
        self.assertFalse(m.model_hit)


class Converters(unittest.TestCase):
    def test_bike_index_record_to_report(self):
        bike = {"id": 7, "url": "u", "frame_size": "56cm", "serial": "Unknown",
                "frame_colors": ["Silver, gray or bare metal", "Stickers tape or other cover-up"],
                "date_stolen": 1788000000, "stolen_coordinates": [51.0, -114.0], "stolen_location": "Calgary"}
        r = bikeindex.to_report(bike, {"brand": "Trek", "model": "FX 2", "features": ["red bell"]})
        self.assertEqual((r["frame_size"], r["serial"], r["frame_colors"]), ("56", "", ["grey"]))

    def test_report_without_brand_is_skipped(self):
        self.assertIsNone(bikeindex.to_report({"date_stolen": 1, "stolen_coordinates": [0, 0]}, {"brand": None}))

    def test_fallback_extract_cleans_brand_and_junk_model(self):
        rows = extract.fallback([{"id": 1, "manufacturer": "Norco Bikes", "model": "Norco"},
                                 {"id": 2, "manufacturer": "Trek", "model": "Marlin 5"}])
        self.assertEqual([(r["brand"], r["model"]) for r in rows], [("Norco", None), ("Trek", "Marlin 5")])

    def test_kijiji_listing_conversion(self):
        raw = {"id": "9", "url": "https://www.kijiji.ca/v-bike-frames-parts/calgary/x/9", "title": "Wheels",
               "description": "29er wheels", "price": {"amount": 12500}, "activationDate": "2026-09-01T00:00:00Z",
               "location": {"name": "Calgary", "coordinates": {"latitude": 51.0, "longitude": -114.0}},
               "attributes": {"all": [{"canonicalName": "framesize", "canonicalValues": ["m"]}]}}
        l = kijiji.to_listing(raw)
        self.assertEqual((l["price"], l["is_parts"], l["posted_at"]), (125.0, True, "2026-09-01"))
        self.assertIn("size m", l["description"])


class Cli(unittest.TestCase):
    def test_demo_builds_mock_data_and_runs(self):
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["demo", "--data", d])
            self.assertTrue((Path(d) / "labels.json").exists())


if __name__ == "__main__":
    unittest.main()
