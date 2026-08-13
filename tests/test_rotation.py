import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.rotation import filenames_to_delete


class TestFilenamesToDelete(unittest.TestCase):
    def test_returns_empty_when_under_limit(self):
        names = [
            "scan_20260813_000001.pdf",
            "scan_20260813_000002.pdf",
        ]
        self.assertEqual(filenames_to_delete(names, keep=10), [])

    def test_returns_empty_when_exactly_at_limit(self):
        names = ["scan_20260813_0000%02d.pdf" % i for i in range(10)]
        self.assertEqual(filenames_to_delete(names, keep=10), [])

    def test_returns_oldest_entries_beyond_limit(self):
        # 12 files, oldest-sorting 2 should be marked for deletion
        names = ["scan_20260813_0000%02d.pdf" % i for i in range(12)]
        result = filenames_to_delete(names, keep=10)
        self.assertEqual(
            sorted(result),
            ["scan_20260813_000000.pdf", "scan_20260813_000001.pdf"],
        )

    def test_ignores_input_order(self):
        names = [
            "scan_20260813_000005.pdf",
            "scan_20260813_000001.pdf",
            "scan_20260813_000003.pdf",
        ]
        result = filenames_to_delete(names, keep=2)
        self.assertEqual(result, ["scan_20260813_000001.pdf"])

    def test_keep_zero_deletes_everything(self):
        names = ["scan_20260813_000001.pdf", "scan_20260813_000002.jpg"]
        self.assertEqual(
            sorted(filenames_to_delete(names, keep=0)), sorted(names)
        )


if __name__ == "__main__":
    unittest.main()
