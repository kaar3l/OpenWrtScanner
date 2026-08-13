"""Build and execute the scanimage command line.

build_scan_command is pure. run_scan takes an injectable `runner` callable
(defaults to subprocess.run) so tests never invoke the real scanimage binary.
"""

import subprocess


def build_scan_command(device, resolution, mode_cli, scan_format, output_path):
    return [
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


def run_scan(cmd, timeout, runner=subprocess.run):
    return runner(cmd, capture_output=True, text=True, timeout=timeout)
