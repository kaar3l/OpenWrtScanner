import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.progress import extract_percent, running_state, done_state, error_state, idle_state


class TestExtractPercent(unittest.TestCase):
    def test_matches_typical_progress_line(self):
        self.assertEqual(extract_percent("Progress: 45.00%\n"), 45.0)

    def test_matches_zero_percent(self):
        self.assertEqual(extract_percent("Progress: 0.00%"), 0.0)

    def test_matches_hundred_percent(self):
        self.assertEqual(extract_percent("Progress: 100.00%"), 100.0)

    def test_returns_none_for_non_progress_line(self):
        self.assertIsNone(extract_percent("scanimage: sane_read: Error during device I/O\n"))

    def test_returns_none_for_empty_line(self):
        self.assertIsNone(extract_percent(""))

    def test_matches_percent_without_decimal(self):
        self.assertEqual(extract_percent("Progress: 50%"), 50.0)


class TestStateBuilders(unittest.TestCase):
    def test_idle_state(self):
        self.assertEqual(idle_state(), {"status": "idle", "percent": 0})

    def test_running_state(self):
        self.assertEqual(running_state(42.5), {"status": "running", "percent": 42.5})

    def test_done_state(self):
        self.assertEqual(
            done_state("scan_20260814_101530.pdf", "/cgi-bin/download.py?name=scan_20260814_101530.pdf"),
            {
                "status": "done",
                "file": "scan_20260814_101530.pdf",
                "url": "/cgi-bin/download.py?name=scan_20260814_101530.pdf",
            },
        )

    def test_error_state(self):
        self.assertEqual(
            error_state("Scanner not found."),
            {"status": "error", "error": "Scanner not found."},
        )


if __name__ == "__main__":
    unittest.main()
