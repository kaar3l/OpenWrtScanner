#!/usr/bin/env python3
"""CGI endpoint: GET ?name=<file>, stream a previously saved scan back."""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.safepath import is_safe_scan_filename

SCANS_DIR = "/overlay/scans"

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
}


def respond_error(status_line, message):
    print("Status: %s" % status_line)
    print("Content-Type: text/plain")
    print()
    print(message)


def main():
    query = urllib.parse.parse_qs(os.environ.get("QUERY_STRING", ""))
    names = query.get("name", [])
    name = names[0] if names else ""

    if not is_safe_scan_filename(name):
        respond_error("400 Bad Request", "Invalid filename.")
        return

    path = os.path.join(SCANS_DIR, name)
    if not os.path.isfile(path):
        respond_error("404 Not Found", "No such scan.")
        return

    extension = name.rsplit(".", 1)[-1]
    content_type = CONTENT_TYPES.get(extension, "application/octet-stream")

    print("Content-Type: %s" % content_type)
    print("Content-Disposition: inline; filename=\"%s\"" % name)
    print()
    sys.stdout.flush()

    with open(path, "rb") as fh:
        sys.stdout.buffer.write(fh.read())


if __name__ == "__main__":
    main()
