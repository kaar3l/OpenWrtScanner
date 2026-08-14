"""Pure logic for building the recent-scans list shown on the page.

Takes already-validated filenames (scan_<YYYYmmdd>_<HHMMSS>.<pdf|jpg>) and
turns them into JSON-able dicts the frontend renders as a thumbnail grid.

Every scan is physically captured as a JPEG (scan.py always scans to JPEG,
wrapping it into a PDF afterwards when that's the requested format - see
scan.py and scanlib.pdfwrap), so every entry has a real thumbnail available:
- JPG-format scans: the saved file itself is the thumbnail.
- PDF-format scans: a "<stem>.thumb.jpg" sidecar is the thumbnail, served
  by thumb.py. It may be missing for scans saved before this existed, or
  if something went wrong writing it - thumb.py 404s in that case and the
  frontend falls back to a plain document icon.
"""

import urllib.parse


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
        quoted = urllib.parse.quote(name)
        thumb_url = (
            "/cgi-bin/download.py?name=%s"
            if extension == "jpg"
            else "/cgi-bin/thumb.py?name=%s"
        ) % quoted
        entries.append(
            {
                "file": name,
                "url": "/cgi-bin/download.py?name=%s" % quoted,
                "thumb_url": thumb_url,
                "format": extension,
                "timestamp": _parse_timestamp(name),
            }
        )
    return entries
