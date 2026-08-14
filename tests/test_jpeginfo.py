import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.jpeginfo import get_jpeg_info


def _sof0_segment(marker, height, width, num_components):
    # marker: e.g. b"\xff\xc0"
    payload = bytearray()
    payload.append(0x08)  # precision
    payload += height.to_bytes(2, "big")
    payload += width.to_bytes(2, "big")
    payload.append(num_components)
    for i in range(num_components):
        payload += bytes([i + 1, 0x11, 0x00])
    length = len(payload) + 2
    return marker + length.to_bytes(2, "big") + bytes(payload)


def _app0_segment():
    # Minimal JFIF APP0 segment, content doesn't matter for our parser.
    payload = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    length = len(payload) + 2
    return b"\xff\xe0" + length.to_bytes(2, "big") + payload


class TestGetJpegInfo(unittest.TestCase):
    def test_reads_baseline_sof0_color(self):
        data = b"\xff\xd8" + _sof0_segment(b"\xff\xc0", height=10, width=20, num_components=3)
        info = get_jpeg_info(data)
        self.assertEqual(info, {"width": 20, "height": 10, "components": 3})

    def test_reads_grayscale_single_component(self):
        data = b"\xff\xd8" + _sof0_segment(b"\xff\xc0", height=50, width=40, num_components=1)
        info = get_jpeg_info(data)
        self.assertEqual(info["components"], 1)

    def test_skips_app0_before_sof(self):
        data = (
            b"\xff\xd8"
            + _app0_segment()
            + _sof0_segment(b"\xff\xc0", height=100, width=200, num_components=3)
        )
        info = get_jpeg_info(data)
        self.assertEqual(info, {"width": 200, "height": 100, "components": 3})

    def test_reads_progressive_sof2(self):
        data = b"\xff\xd8" + _sof0_segment(b"\xff\xc2", height=33, width=44, num_components=3)
        info = get_jpeg_info(data)
        self.assertEqual(info["width"], 44)
        self.assertEqual(info["height"], 33)

    def test_rejects_missing_soi(self):
        with self.assertRaises(ValueError):
            get_jpeg_info(b"not a jpeg at all")

    def test_rejects_no_sof_marker_found(self):
        data = b"\xff\xd8" + _app0_segment()  # no SOF, ends abruptly
        with self.assertRaises(ValueError):
            get_jpeg_info(data)


if __name__ == "__main__":
    unittest.main()
