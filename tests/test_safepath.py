import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.safepath import is_safe_scan_filename


class TestIsSafeScanFilename(unittest.TestCase):
    def test_accepts_well_formed_pdf_name(self):
        self.assertTrue(is_safe_scan_filename("scan_20260813_223045.pdf"))

    def test_accepts_well_formed_jpg_name(self):
        self.assertTrue(is_safe_scan_filename("scan_20260101_000000.jpg"))

    def test_rejects_path_traversal(self):
        self.assertFalse(is_safe_scan_filename("../../etc/passwd"))

    def test_rejects_embedded_slash(self):
        self.assertFalse(is_safe_scan_filename("scans/scan_20260813_223045.pdf"))

    def test_rejects_wrong_extension(self):
        self.assertFalse(is_safe_scan_filename("scan_20260813_223045.exe"))

    def test_rejects_missing_prefix(self):
        self.assertFalse(is_safe_scan_filename("20260813_223045.pdf"))

    def test_rejects_empty_string(self):
        self.assertFalse(is_safe_scan_filename(""))

    def test_rejects_non_digit_timestamp(self):
        self.assertFalse(is_safe_scan_filename("scan_aaaaaaaa_bbbbbb.pdf"))


if __name__ == "__main__":
    unittest.main()
