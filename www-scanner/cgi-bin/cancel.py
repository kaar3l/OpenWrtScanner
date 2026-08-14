#!/usr/bin/env python3
"""CGI endpoint: POST, cancel the currently-running scan.

Writes CANCEL_FLAG before signalling so scan.py's loop can tell a
user-requested stop apart from a real device failure (see was_cancelled()
in scan.py). Sends SIGTERM rather than SIGKILL - scanimage/sane-backends
gets a chance to close the USB device cleanly, which matters: this
scanner is known to wedge (needing a physical replug) if left in a bad
state mid-transaction.
"""

import json
import os
import signal
import sys

sys.path.insert(0, os.path.dirname(__file__))

from scanlib.pidfile import read_pid

PID_FILE = "/tmp/scan.pid"
CANCEL_FLAG = "/tmp/scan_cancel"


def respond(status_line, payload):
    print("Status: %s" % status_line)
    print("Content-Type: application/json")
    print()
    print(json.dumps(payload))


def main():
    if os.environ.get("REQUEST_METHOD") != "POST":
        respond("405 Method Not Allowed", {"ok": False, "error": "Method not allowed."})
        return

    pid = read_pid(PID_FILE)
    if pid is None:
        respond("404 Not Found", {"ok": False, "error": "No scan in progress."})
        return

    with open(CANCEL_FLAG, "w") as f:
        f.write("1")

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        respond("404 Not Found", {"ok": False, "error": "No scan in progress."})
        return

    respond("200 OK", {"ok": True})


if __name__ == "__main__":
    main()
