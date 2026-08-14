#!/usr/bin/env python3
"""CGI endpoint: GET, report current scan progress.

Reads the JSON state scan.py writes as it streams scanimage's --progress
output (see scanlib.progress and scanlib.runner.run_scan_streaming).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.progress import idle_state

PROGRESS_FILE = "/tmp/scan_progress.json"


def main():
    print("Content-Type: application/json")
    print()

    try:
        with open(PROGRESS_FILE) as f:
            text = f.read()
        json.loads(text)  # validate before forwarding verbatim
        print(text)
    except (OSError, ValueError):
        print(json.dumps(idle_state()))


if __name__ == "__main__":
    main()
