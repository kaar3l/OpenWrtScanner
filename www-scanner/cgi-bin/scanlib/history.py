"""Pure logic for building the recent-scans list shown on the page.

Takes already-validated filenames (scan_<YYYYmmdd>_<HHMMSS>.<pdf|jpg>) and
turns them into JSON-able dicts the frontend renders as a thumbnail grid.
"""

import urllib.parse

_IMAGE_FORMATS = {"jpg"}


def _parse_timestamp(filename):
    # scan_20260813_223045.pdf -> "2026-08-13 22:30:45"
    stem = filename.split(".", 1)[0]  # scan_20260813_223045
    _, date_part, time_part = stem.split("_")
    return "%s-%s-%s %s:%s:%s" % (
        date_part[0:4],
        date_part[4:6],
        date_part[6:8],
        time_part[0:2],
        time_part[2:4],
        time_part[4:6],
    )


def build_history(filenames, limit=10):
    ordered = sorted(filenames, reverse=True)  # newest first
    entries = []
    for name in ordered[:limit]:
        extension = name.rsplit(".", 1)[-1]
        entries.append(
            {
                "file": name,
                "url": "/cgi-bin/download.py?name=%s" % urllib.parse.quote(name),
                "format": extension,
                "is_image": extension in _IMAGE_FORMATS,
                "timestamp": _parse_timestamp(name),
            }
        )
    return entries
