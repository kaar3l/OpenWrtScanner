import os
import subprocess
import sys
import threading
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
    def __init__(self, stderr_lines, returncode, pid=4242):
        self.stderr = iter(stderr_lines)
        self._returncode = returncode
        self.pid = pid

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

    def test_calls_on_start_with_pid(self):
        def fake_popen(cmd, stdout, stderr, text):
            return FakeStreamingProcess(["Progress: 5.00%\n"], returncode=0, pid=9999)

        seen_pids = []
        run_scan_streaming(
            ["scanimage"],
            "/tmp/progress.json",
            popen=fake_popen,
            write_progress=lambda p, s: None,
            on_start=seen_pids.append,
        )

        self.assertEqual(seen_pids, [9999])


class FakeHangingProcess:
    """Simulates a scanimage process that never produces output and never
    exits on its own - only reacts to kill(), like a real wedged process
    reacting to SIGKILL. Used to test the timeout watchdog without an
    actual multi-second sleep in the test."""

    def __init__(self):
        self.pid = 1234
        self._killed = threading.Event()
        self.stderr = self._stderr_iter()

    def _stderr_iter(self):
        # Blocks here exactly like a real blocked read would, until the
        # watchdog thread kills us - then stop, as EOF on a closed pipe would.
        self._killed.wait(timeout=5.0)
        return
        yield  # pragma: no cover - makes this a generator

    def kill(self):
        self._killed.set()

    def wait(self):
        return -9 if self._killed.is_set() else 0


class TestRunScanStreamingTimeout(unittest.TestCase):
    def test_kills_process_and_reports_timeout_status(self):
        def fake_popen(cmd, stdout, stderr, text):
            return FakeHangingProcess()

        returncode, last_percent, stderr_text = run_scan_streaming(
            ["scanimage"],
            "/tmp/progress.json",
            timeout=0.05,
            popen=fake_popen,
            write_progress=lambda p, s: None,
        )

        self.assertEqual(returncode, "timeout")
        self.assertEqual(last_percent, 0.0)
        self.assertEqual(stderr_text, "")

    def test_does_not_time_out_a_fast_scan(self):
        def fake_popen(cmd, stdout, stderr, text):
            return FakeStreamingProcess(["Progress: 100.00%\n"], returncode=0)

        returncode, last_percent, stderr_text = run_scan_streaming(
            ["scanimage"],
            "/tmp/progress.json",
            timeout=5,
            popen=fake_popen,
            write_progress=lambda p, s: None,
        )

        self.assertEqual(returncode, 0)


if __name__ == "__main__":
    unittest.main()
