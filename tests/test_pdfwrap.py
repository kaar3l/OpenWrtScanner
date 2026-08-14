import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.pdfwrap import wrap_jpeg_as_pdf
from tests.test_jpeginfo import _sof0_segment


def _fake_jpeg(height, width, components):
    # A byte-valid-enough JPEG for our purposes: SOI + SOF + EOI.
    # wrap_jpeg_as_pdf only needs get_jpeg_info to succeed on it; the bytes
    # are embedded as opaque DCTDecode data, never decoded by us.
    return b"\xff\xd8" + _sof0_segment(b"\xff\xc0", height, width, components) + b"\xff\xd9"


class TestWrapJpegAsPdf(unittest.TestCase):
    def test_starts_with_pdf_header(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(100, 200, 3), dpi=150)
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))

    def test_ends_with_eof_marker(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(100, 200, 3), dpi=150)
        self.assertTrue(pdf.rstrip(b"\n").endswith(b"%%EOF"))

    def test_embeds_declared_pixel_dimensions(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(150, 300, 3), dpi=150)
        self.assertIn(b"/Width 300", pdf)
        self.assertIn(b"/Height 150", pdf)

    def test_color_jpeg_uses_devicergb(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(100, 200, 3), dpi=150)
        self.assertIn(b"/ColorSpace /DeviceRGB", pdf)

    def test_grayscale_jpeg_uses_devicegray(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(100, 200, 1), dpi=150)
        self.assertIn(b"/ColorSpace /DeviceGray", pdf)

    def test_embeds_raw_jpeg_bytes_verbatim(self):
        jpeg = _fake_jpeg(100, 200, 3)
        pdf = wrap_jpeg_as_pdf(jpeg, dpi=150)
        self.assertIn(jpeg, pdf)

    def test_page_size_derived_from_dpi(self):
        # 300 px at 150 dpi -> 144pt (300 * 72 / 150)
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(150, 300, 3), dpi=150)
        self.assertIn(b"/MediaBox [0 0 144.0 72.0]", pdf)

    def test_uses_dctdecode_filter(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(100, 200, 3), dpi=150)
        self.assertIn(b"/Filter /DCTDecode", pdf)

    def test_xref_object_count_matches_five_objects(self):
        pdf = wrap_jpeg_as_pdf(_fake_jpeg(100, 200, 3), dpi=150)
        self.assertIn(b"xref\n0 6\n", pdf)
        self.assertIn(b"/Size 6", pdf)


if __name__ == "__main__":
    unittest.main()
