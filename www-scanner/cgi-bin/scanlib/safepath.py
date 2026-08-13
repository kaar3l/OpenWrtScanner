"""Pure filename-safety check for the download endpoint.

Matches exactly the shape scanlib.naming.make_filename produces:
scan_<8 digits>_<6 digits>.<pdf|jpg>
"""

import re

_SAFE_NAME_RE = re.compile(r"^scan_\d{8}_\d{6}\.(pdf|jpg)$")


def is_safe_scan_filename(name):
    if not isinstance(name, str):
        return False
    return bool(_SAFE_NAME_RE.match(name))
