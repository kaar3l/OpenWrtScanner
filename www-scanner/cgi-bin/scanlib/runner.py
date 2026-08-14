"""Build and execute the scanimage command line.

build_scan_command is pure. run_scan and run_scan_streaming take an
injectable callable (defaulting to the real subprocess API) so tests never
invoke the real scanimage binary.
"""

import json
import subprocess

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


def run_scan_streaming(cmd, progress_path, popen=subprocess.Popen, write_progress=write_progress_file):
    """Run `cmd`, parsing scanimage's --progress stderr output as it streams.

    Returns (returncode, last_percent, stderr_text). Every "Progress: NN%"
    line seen is written to `progress_path` via `write_progress` as it
    arrives, so a concurrent reader (progress.py) can report live status.
    """
    proc = popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

    stderr_lines = []
    last_percent = 0.0
    for line in proc.stderr:
        stderr_lines.append(line)
        percent = extract_percent(line)
        if percent is not None:
            last_percent = percent
            write_progress(progress_path, running_state(last_percent))

    returncode = proc.wait()
    return returncode, last_percent, "".join(stderr_lines)
