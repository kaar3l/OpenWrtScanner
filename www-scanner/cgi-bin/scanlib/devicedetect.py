"""Pure parsing of `scanimage -L` output.

The scanner's SANE device string embeds a per-unit USB serial number
(e.g. "pixma:04A91912_43A16F"), so it differs between physically
identical scanners on different routers. Auto-detecting it at request
time (rather than hardcoding it) is what lets the same codebase deploy
unmodified to any router with exactly one attached scanner.
"""

import re

_DEVICE_RE = re.compile(r"device `([^']+)' is")


def parse_device_list(output):
    """Return every device string found in `scanimage -L` output, in order."""
    return _DEVICE_RE.findall(output)


def pick_device(output):
    """Return the device string to scan with.

    Picks the first device found. Raises ValueError if none were found -
    there's nothing sensible to scan with in that case.
    """
    devices = parse_device_list(output)
    if not devices:
        raise ValueError("No scanner detected (scanimage -L found nothing).")
    return devices[0]
