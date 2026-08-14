#!/usr/bin/env python3
"""CGI endpoint: DELETE (or POST) ?name=<file>, remove a saved scan.

Also removes the "<stem>.thumb.jpg" sidecar for PDF scans, if present.
"""

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.safepath import is_safe_scan_filename

SCANS_DIR = "/overlay/scans"


def respond(status_line, payload):
    print("Status: %s" % status_line)
    print("Content-Type: application/json")
    print()
    print(json.dumps(payload))


def main():
    method = os.environ.get("REQUEST_METHOD", "")
    if method not in ("DELETE", "POST"):
        respond("405 Method Not Allowed", {"ok": False, "error": "Method not allowed."})
        return

    query = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))
    names = query.get("name", [])
    name = names[0] if names else ""

    if not is_safe_scan_filename(name):
        respond("400 Bad Request", {"ok": False, "error": "Invalid filename."})
        return

    path = os.path.join(SCANS_DIR, name)
    try:
        os.remove(path)
    except FileNotFoundError:
        respond("404 Not Found", {"ok": False, "error": "No such scan."})
        return

    stem = name.rsplit(".", 1)[0]
    try:
        os.remove(os.path.join(SCANS_DIR, stem + ".thumb.jpg"))
    except FileNotFoundError:
        pass

    respond("200 OK", {"ok": True})


if __name__ == "__main__":
    main()
