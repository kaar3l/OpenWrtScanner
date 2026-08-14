#!/usr/bin/env python3
"""CGI endpoint: GET ?name=<scan file>, serve its thumbnail.

- name ending in .jpg: the scan itself is the thumbnail - redirect to
  download.py so there's one code path for actually streaming bytes.
- name ending in .pdf: serve the "<stem>.thumb.jpg" sidecar written by
  scan.py. 404 if it's missing (e.g. a scan saved before this existed) -
  the frontend falls back to a plain document icon on that.
"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.safepath import is_safe_scan_filename

SCANS_DIR = "/overlay/scans"


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

    if name.endswith(".jpg"):
        print("Status: 302 Found")
        print("Location: /cgi-bin/download.py?name=%s" % urllib.parse.quote(name))
        print()
        return

    stem = name.rsplit(".", 1)[0]
    thumb_path = os.path.join(SCANS_DIR, stem + ".thumb.jpg")
    if not os.path.isfile(thumb_path):
        respond_error("404 Not Found", "No thumbnail for this scan.")
        return

    print("Content-Type: image/jpeg")
    print()
    sys.stdout.flush()
    with open(thumb_path, "rb") as fh:
        sys.stdout.buffer.write(fh.read())


if __name__ == "__main__":
    main()
