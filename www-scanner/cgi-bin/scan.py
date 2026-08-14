#!/usr/bin/env python3
"""CGI endpoint: POST resolution/mode/format, run a scan, save it, return JSON.

Every scan is physically captured as a JPEG, regardless of the requested
output format:
- format=JPG: that JPEG *is* the saved file.
- format=PDF: the JPEG is scanned to "<stem>.thumb.jpg" (kept permanently as
  the history thumbnail), then wrapped into "<stem>.pdf" (see scanlib.pdfwrap).

While scanimage runs, its --progress output is streamed into PROGRESS_FILE
so a concurrent request to progress.py can report live status.
"""

import datetime
import fcntl
import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.naming import make_filename
from scanlib.pdfwrap import wrap_jpeg_as_pdf
from scanlib.progress import done_state, error_state, running_state
from scanlib.rotation import filenames_to_delete
from scanlib.runner import build_scan_command, run_scan_streaming, write_progress_file
from scanlib.safepath import is_safe_scan_filename
from scanlib.validation import validate_format, validate_mode, validate_resolution

DEVICE = "pixma:04A91912_43A16F"
SCANS_DIR = "/overlay/scans"
LOCK_FILE = "/tmp/scan.lock"
PROGRESS_FILE = "/tmp/scan_progress.json"
HISTORY_KEEP = 10


def prune_old_scans():
    """Delete scans (and their thumbnail sidecars) beyond the newest
    HISTORY_KEEP. Best-effort - a file already gone is not an error."""
    existing = [
        name for name in os.listdir(SCANS_DIR) if is_safe_scan_filename(name)
    ]
    for name in filenames_to_delete(existing, keep=HISTORY_KEEP):
        stem = name.rsplit(".", 1)[0]
        for path in (
            os.path.join(SCANS_DIR, name),
            os.path.join(SCANS_DIR, stem + ".thumb.jpg"),
        ):
            try:
                os.remove(path)
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
        _scan_format, extension = validate_format(form.get("format", ""))
    except ValueError as exc:
        respond_json("400 Bad Request", {"ok": False, "error": str(exc)})
        return

    os.makedirs(SCANS_DIR, exist_ok=True)
    filename = make_filename(extension, datetime.datetime.now())
    stem = filename.rsplit(".", 1)[0]
    output_path = os.path.join(SCANS_DIR, filename)

    # Always physically scan to JPEG. For PDF output, that JPEG lands in the
    # thumbnail sidecar path and gets wrapped into the real PDF afterwards;
    # for JPG output, it lands directly at the final output path.
    if extension == "pdf":
        jpeg_scan_path = os.path.join(SCANS_DIR, stem + ".thumb.jpg")
    else:
        jpeg_scan_path = output_path

    cmd = build_scan_command(DEVICE, resolution, mode_cli, "jpeg", jpeg_scan_path, progress=True)

    lock_fh = open(LOCK_FILE, "w")
    try:
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            respond_json(
                "409 Conflict", {"ok": False, "error": "Scan already in progress."}
            )
            return

        write_progress_file(PROGRESS_FILE, running_state(0.0))

        returncode, _percent, stderr_text = run_scan_streaming(cmd, PROGRESS_FILE)

        if returncode != 0:
            message = "Scanner not found or scan failed: %s" % (
                stderr_text or "unknown error"
            ).strip()
            write_progress_file(PROGRESS_FILE, error_state(message))
            respond_json("500 Internal Server Error", {"ok": False, "error": message})
            return

        if extension == "pdf":
            with open(jpeg_scan_path, "rb") as f:
                jpeg_bytes = f.read()
            pdf_bytes = wrap_jpeg_as_pdf(jpeg_bytes, dpi=resolution)
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)

        prune_old_scans()

        url = "/cgi-bin/download.py?name=%s" % urllib.parse.quote(filename)
        write_progress_file(PROGRESS_FILE, done_state(filename, url))
        respond_json("200 OK", {"ok": True, "file": filename, "url": url})
    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()


if __name__ == "__main__":
    main()
