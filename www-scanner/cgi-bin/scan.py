#!/usr/bin/env python3
"""CGI endpoint: POST resolution/mode/format, run a scan, save it, return JSON."""

import datetime
import fcntl
import json
import os
import subprocess
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.naming import make_filename
from scanlib.rotation import filenames_to_delete
from scanlib.runner import build_scan_command, run_scan
from scanlib.safepath import is_safe_scan_filename
from scanlib.validation import validate_format, validate_mode, validate_resolution

DEVICE = "pixma:04A91912_43A16F"
SCANS_DIR = "/overlay/scans"
LOCK_FILE = "/tmp/scan.lock"
SCAN_TIMEOUT_SECONDS = 300
HISTORY_KEEP = 10


def prune_old_scans():
    """Delete scans beyond the newest HISTORY_KEEP. Best-effort - a file
    already gone (e.g. deleted by hand) is not an error."""
    existing = [
        name for name in os.listdir(SCANS_DIR) if is_safe_scan_filename(name)
    ]
    for name in filenames_to_delete(existing, keep=HISTORY_KEEP):
        try:
            os.remove(os.path.join(SCANS_DIR, name))
        except FileNotFoundError:
            pass


def read_form_body():
    try:
        length = int(os.environ.get("CONTENT_LENGTH", "0"))
    except ValueError:
        length = 0
    raw = sys.stdin.buffer.read(length) if length > 0 else b""
    parsed = urllib.parse.parse_qs(raw.decode("utf-8", errors="replace"))
    return {key: values[0] for key, values in parsed.items()}


def respond_json(status_line, payload):
    print("Status: %s" % status_line)
    print("Content-Type: application/json")
    print()
    print(json.dumps(payload))


def main():
    form = read_form_body()

    try:
        resolution = validate_resolution(form.get("resolution", ""))
        mode_cli = validate_mode(form.get("mode", ""))
        scan_format, extension = validate_format(form.get("format", ""))
    except ValueError as exc:
        respond_json("400 Bad Request", {"ok": False, "error": str(exc)})
        return

    os.makedirs(SCANS_DIR, exist_ok=True)
    filename = make_filename(extension, datetime.datetime.now())
    output_path = os.path.join(SCANS_DIR, filename)
    cmd = build_scan_command(DEVICE, resolution, mode_cli, scan_format, output_path)

    lock_fh = open(LOCK_FILE, "w")
    try:
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            respond_json(
                "409 Conflict", {"ok": False, "error": "Scan already in progress."}
            )
            return

        try:
            result = run_scan(cmd, timeout=SCAN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            respond_json(
                "504 Gateway Timeout",
                {"ok": False, "error": "Scan timed out after %ss." % SCAN_TIMEOUT_SECONDS},
            )
            return

        if result.returncode != 0:
            respond_json(
                "500 Internal Server Error",
                {
                    "ok": False,
                    "error": "Scanner not found or scan failed: %s"
                    % (result.stderr or "unknown error").strip(),
                },
            )
            return

        prune_old_scans()

        respond_json(
            "200 OK",
            {
                "ok": True,
                "file": filename,
                "url": "/cgi-bin/download.py?name=%s" % urllib.parse.quote(filename),
            },
        )
    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()


if __name__ == "__main__":
    main()
