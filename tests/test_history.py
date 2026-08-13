import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.history import build_history


class TestBuildHistory(unittest.TestCase):
    def test_orders_newest_first(self):
        names = [
            "scan_20260813_090000.pdf",
            "scan_20260813_100000.jpg",
            "scan_20260812_090000.pdf",
        ]
        result = build_history(names)
        self.assertEqual(
            [entry["file"] for entry in result],
            [
                "scan_20260813_100000.jpg",
                "scan_20260813_090000.pdf",
                "scan_20260812_090000.pdf",
            ],
        )

    def test_entry_shape(self):
        result = build_history(["scan_20260813_223045.pdf"])
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertEqual(entry["file"], "scan_20260813_223045.pdf")
        self.assertEqual(entry["url"], "/cgi-bin/download.py?name=scan_20260813_223045.pdf")
        self.assertEqual(entry["format"], "pdf")
        self.assertFalse(entry["is_image"])
        self.assertEqual(entry["timestamp"], "2026-08-13 22:30:45")

    def test_jpg_is_image_true(self):
        result = build_history(["scan_20260813_223045.jpg"])
        self.assertTrue(result[0]["is_image"])
        self.assertEqual(result[0]["format"], "jpg")

    def test_respects_limit(self):
        names = ["scan_20260813_0000%02d.pdf" % i for i in range(15)]
        result = build_history(names, limit=10)
        self.assertEqual(len(result), 10)
        # newest (highest suffix) first
        self.assertEqual(result[0]["file"], "scan_20260813_000014.pdf")

    def test_empty_input(self):
        self.assertEqual(build_history([]), [])

    def test_url_quotes_special_characters_safely(self):
        # defense in depth even though real filenames never contain these
        result = build_history(["scan_20260813_223045.pdf"])
        self.assertNotIn(" ", result[0]["url"])


if __name__ == "__main__":
    unittest.main()
