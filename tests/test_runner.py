import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.runner import build_scan_command, run_scan


class TestBuildScanCommand(unittest.TestCase):
    def test_builds_expected_argv(self):
        cmd = build_scan_command(
            device="pixma:04A91912_43A16F",
            resolution=150,
            mode_cli="Color",
            scan_format="pdf",
            output_path="/overlay/scans/scan_20260813_223045.pdf",
        )
        self.assertEqual(
            cmd,
            [
                "scanimage",
                "-d",
                "pixma:04A91912_43A16F",
                "--resolution",
                "150",
                "--mode",
                "Color",
                "--format=pdf",
                "-o",
                "/overlay/scans/scan_20260813_223045.pdf",
            ],
        )

    def test_grayscale_mode_passed_through_as_cli_value(self):
        cmd = build_scan_command(
            device="pixma:04A91912_43A16F",
            resolution=600,
            mode_cli="Gray",
            scan_format="jpeg",
            output_path="/overlay/scans/scan_20260813_223045.jpg",
        )
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "Gray")
        self.assertIn("--format=jpeg", cmd)


class FakeCompletedProcess:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


class TestRunScan(unittest.TestCase):
    def test_returns_runner_result_on_success(self):
        calls = []

        def fake_runner(cmd, capture_output, text, timeout):
            calls.append((cmd, capture_output, text, timeout))
            return FakeCompletedProcess(returncode=0)

        result = run_scan(["scanimage", "-d", "x"], timeout=300, runner=fake_runner)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        cmd, capture_output, text, timeout = calls[0]
        self.assertEqual(cmd, ["scanimage", "-d", "x"])
        self.assertTrue(capture_output)
        self.assertTrue(text)
        self.assertEqual(timeout, 300)

    def test_propagates_timeout_expired(self):
        def fake_runner(cmd, capture_output, text, timeout):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

        with self.assertRaises(subprocess.TimeoutExpired):
            run_scan(["scanimage"], timeout=5, runner=fake_runner)


if __name__ == "__main__":
    unittest.main()
