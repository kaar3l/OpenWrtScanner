import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.naming import make_filename


class TestMakeFilename(unittest.TestCase):
    def test_formats_timestamp_and_extension(self):
        now = datetime.datetime(2026, 8, 13, 22, 30, 45)
        self.assertEqual(make_filename("pdf", now), "scan_20260813_223045.pdf")

    def test_jpg_extension(self):
        now = datetime.datetime(2026, 1, 1, 0, 0, 0)
        self.assertEqual(make_filename("jpg", now), "scan_20260101_000000.jpg")

    def test_zero_pads_single_digit_fields(self):
        now = datetime.datetime(2026, 3, 5, 9, 7, 2)
        self.assertEqual(make_filename("pdf", now), "scan_20260305_090702.pdf")


if __name__ == "__main__":
    unittest.main()
