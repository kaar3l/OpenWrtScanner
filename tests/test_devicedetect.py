import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.devicedetect import parse_device_list, pick_device

ROUTER1_OUTPUT = "device `pixma:04A91912_43A16F' is a CANON CanoScan LiDE 400 multi-function peripheral\n"
ROUTER2_OUTPUT = "device `pixma:04A91912_4DEF44' is a CANON CanoScan LiDE 400 multi-function peripheral\n"


class TestParseDeviceList(unittest.TestCase):
    def test_parses_single_device(self):
        self.assertEqual(parse_device_list(ROUTER1_OUTPUT), ["pixma:04A91912_43A16F"])

    def test_parses_different_device_string(self):
        self.assertEqual(parse_device_list(ROUTER2_OUTPUT), ["pixma:04A91912_4DEF44"])

    def test_parses_multiple_devices(self):
        combined = ROUTER1_OUTPUT + ROUTER2_OUTPUT
        self.assertEqual(
            parse_device_list(combined),
            ["pixma:04A91912_43A16F", "pixma:04A91912_4DEF44"],
        )

    def test_empty_output_returns_empty_list(self):
        self.assertEqual(parse_device_list(""), [])

    def test_ignores_unrelated_lines(self):
        output = "No scanners were identified.\n" + ROUTER1_OUTPUT
        self.assertEqual(parse_device_list(output), ["pixma:04A91912_43A16F"])


class TestPickDevice(unittest.TestCase):
    def test_returns_the_only_device(self):
        self.assertEqual(pick_device(ROUTER1_OUTPUT), "pixma:04A91912_43A16F")

    def test_returns_first_of_several_devices(self):
        combined = ROUTER1_OUTPUT + ROUTER2_OUTPUT
        self.assertEqual(pick_device(combined), "pixma:04A91912_43A16F")

    def test_raises_when_no_device_found(self):
        with self.assertRaises(ValueError):
            pick_device("No scanners were identified.\n")

    def test_raises_on_empty_output(self):
        with self.assertRaises(ValueError):
            pick_device("")


if __name__ == "__main__":
    unittest.main()
