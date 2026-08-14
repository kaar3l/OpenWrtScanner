import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "www-scanner", "cgi-bin"))

from scanlib.runner import build_scan_command, run_scan, run_scan_streaming


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

    def test_omits_progress_flag_by_default(self):
        cmd = build_scan_command(
            device="pixma:04A91912_43A16F",
            resolution=150,
            mode_cli="Color",
            scan_format="pdf",
            output_path="/overlay/scans/x.pdf",
        )
        self.assertNotIn("--progress", cmd)

    def test_includes_progress_flag_when_requested(self):
        cmd = build_scan_command(
            device="pixma:04A91912_43A16F",
            resolution=150,
            mode_cli="Color",
            scan_format="pdf",
            output_path="/overlay/scans/x.pdf",
            progress=True,
        )
        self.assertIn("--progress", cmd)


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


class FakeStreamingProcess:
    def __init__(self, stderr_lines, returncode):
        self.stderr = iter(stderr_lines)
        self._returncode = returncode

    def wait(self):
        return self._returncode


class TestRunScanStreaming(unittest.TestCase):
    def test_parses_progress_lines_and_writes_each_update(self):
        lines = ["Progress: 0.00%\n", "Progress: 50.00%\n", "Progress: 100.00%\n"]
        written = []

        def fake_popen(cmd, stdout, stderr, text):
            return FakeStreamingProcess(lines, returncode=0)

        def fake_write_progress(path, state):
            written.append((path, state))

        returncode, last_percent, stderr_text = run_scan_streaming(
            ["scanimage"], "/tmp/progress.json", popen=fake_popen, write_progress=fake_write_progress
        )

        self.assertEqual(returncode, 0)
        self.assertEqual(last_percent, 100.0)
        self.assertEqual(stderr_text, "".join(lines))
        self.assertEqual(len(written), 3)
        self.assertEqual(written[-1], ("/tmp/progress.json", {"status": "running", "percent": 100.0}))

    def test_ignores_non_progress_lines_but_keeps_them_in_stderr_text(self):
        lines = ["Progress: 10.00%\n", "scanimage: some warning\n", "Progress: 20.00%\n"]
        written = []

        def fake_popen(cmd, stdout, stderr, text):
            return FakeStreamingProcess(lines, returncode=0)

        returncode, last_percent, stderr_text = run_scan_streaming(
            ["scanimage"],
            "/tmp/progress.json",
            popen=fake_popen,
            write_progress=lambda path, state: written.append(state),
        )

        self.assertEqual(last_percent, 20.0)
        self.assertIn("scanimage: some warning\n", stderr_text)
        self.assertEqual(len(written), 2)  # only the two Progress lines triggered a write

    def test_failure_exit_code_still_returns_accumulated_stderr(self):
        lines = ["scanimage: sane_read: Error during device I/O\n"]

        def fake_popen(cmd, stdout, stderr, text):
            return FakeStreamingProcess(lines, returncode=9)

        returncode, last_percent, stderr_text = run_scan_streaming(
            ["scanimage"], "/tmp/progress.json", popen=fake_popen, write_progress=lambda p, s: None
        )

        self.assertEqual(returncode, 9)
        self.assertEqual(last_percent, 0.0)
        self.assertEqual(stderr_text, lines[0])


if __name__ == "__main__":
    unittest.main()
