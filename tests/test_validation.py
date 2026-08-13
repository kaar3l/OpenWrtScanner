import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.validation import validate_resolution, validate_mode, validate_format


class TestValidateResolution(unittest.TestCase):
    def test_accepts_all_allowed_values(self):
        for value, expected in [("150", 150), ("300", 300), ("600", 600), ("1200", 1200)]:
            self.assertEqual(validate_resolution(value), expected)

    def test_rejects_unlisted_value(self):
        with self.assertRaises(ValueError):
            validate_resolution("2400")

    def test_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            validate_resolution("abc")

    def test_rejects_missing(self):
        with self.assertRaises(ValueError):
            validate_resolution("")


class TestValidateMode(unittest.TestCase):
    def test_color_maps_to_cli_color(self):
        self.assertEqual(validate_mode("Color"), "Color")

    def test_grayscale_maps_to_cli_gray(self):
        self.assertEqual(validate_mode("Grayscale"), "Gray")

    def test_rejects_unknown_mode(self):
        with self.assertRaises(ValueError):
            validate_mode("Lineart")

    def test_rejects_cli_value_directly(self):
        # UI sends the label "Grayscale", not the CLI value "Gray" - reject the latter
        with self.assertRaises(ValueError):
            validate_mode("Gray")


class TestValidateFormat(unittest.TestCase):
    def test_pdf_maps_to_pdf_pdf(self):
        self.assertEqual(validate_format("PDF"), ("pdf", "pdf"))

    def test_jpg_maps_to_jpeg_jpg(self):
        self.assertEqual(validate_format("JPG"), ("jpeg", "jpg"))

    def test_rejects_unknown_format(self):
        with self.assertRaises(ValueError):
            validate_format("PNG")


if __name__ == "__main__":
    unittest.main()
