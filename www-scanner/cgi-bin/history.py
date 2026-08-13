#!/usr/bin/env python3
"""CGI endpoint: GET, list the last HISTORY_KEEP saved scans as JSON."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.history import build_history
from scanlib.safepath import is_safe_scan_filename

SCANS_DIR = "/overlay/scans"
HISTORY_KEEP = 10


def main():
    try:
        existing = [
            name for name in os.listdir(SCANS_DIR) if is_safe_scan_filename(name)
        ]
    except FileNotFoundError:
        existing = []

    entries = build_history(existing, limit=HISTORY_KEEP)

    print("Content-Type: application/json")
    print()
    print(json.dumps(entries))


if __name__ == "__main__":
    main()
