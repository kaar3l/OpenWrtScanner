"""Pure helpers for tracking/reporting live scan progress.

scan.py streams scanimage's --progress stderr output and writes the
current state (as JSON) to a shared file; progress.py (a separate CGI
request) reads that file and returns it as-is. These functions build the
state dicts and parse the one line format scanimage emits:
"Progress: NN.NN%".
"""

import re

_PERCENT_RE = re.compile(r"Progress:\s*([\d.]+)%")


def extract_percent(line):
    match = _PERCENT_RE.search(line)
    if not match:
        return None
    return float(match.group(1))


def idle_state():
    return {"status": "idle", "percent": 0}


def running_state(percent):
    return {"status": "running", "percent": percent}


def done_state(file, url):
    return {"status": "done", "file": file, "url": url}


def error_state(message):
    return {"status": "error", "error": message}
