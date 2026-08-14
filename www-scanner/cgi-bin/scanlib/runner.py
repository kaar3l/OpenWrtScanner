"""Build and execute the scanimage command line.

build_scan_command is pure. run_scan and run_scan_streaming take an
injectable callable (defaulting to the real subprocess API) so tests never
invoke the real scanimage binary.
"""

import json
import subprocess
import threading

from .progress import extract_percent, running_state


def build_scan_command(device, resolution, mode_cli, scan_format, output_path, progress=False):
    cmd = [
        "scanimage",
        "-d",
        device,
        "--resolution",
        str(resolution),
        "--mode",
        mode_cli,
        "--format=%s" % scan_format,
        "-o",
        output_path,
    ]
    if progress:
        cmd.append("--progress")
    return cmd


def run_scan(cmd, timeout, runner=subprocess.run):
    return runner(cmd, capture_output=True, text=True, timeout=timeout)


def write_progress_file(path, state):
    with open(path, "w") as f:
        json.dump(state, f)


def run_scan_streaming(
    cmd,
    progress_path,
    timeout=300,
    popen=subprocess.Popen,
    write_progress=write_progress_file,
    on_start=None,
):
    """Run `cmd`, parsing scanimage's --progress stderr output as it streams.

    Returns (returncode, last_percent, stderr_text) where returncode is the
    process's real exit code, or the string "timeout" if it was killed for
    running past `timeout` seconds - a genuine hang (no output at all) can
    only be caught by a separate watchdog thread, since a blocking read on
    proc.stderr can't otherwise interrupt itself.

    Every "Progress: NN%" line seen is written to `progress_path` via
    `write_progress` as it arrives, so a concurrent reader (progress.py)
    can report live status. If `on_start` is given, it's called with the
    child's PID right after it launches (so a separate request can cancel
    it - see cancel.py).
    """
    proc = popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if on_start is not None:
        on_start(proc.pid)

    timed_out = {"flag": False}

    def _kill_on_timeout():
        timed_out["flag"] = True
        proc.kill()

    timer = threading.Timer(timeout, _kill_on_timeout)
    timer.start()

    stderr_lines = []
    last_percent = 0.0
    try:
        for line in proc.stderr:
            stderr_lines.append(line)
            percent = extract_percent(line)
            if percent is not None:
                last_percent = percent
                write_progress(progress_path, running_state(last_percent))
    finally:
        timer.cancel()

    returncode = proc.wait()
    stderr_text = "".join(stderr_lines)

    if timed_out["flag"]:
        return "timeout", last_percent, stderr_text
    return returncode, last_percent, stderr_text
