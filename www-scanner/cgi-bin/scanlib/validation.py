"""Pure validation helpers for scan request parameters.

No I/O, no subprocess calls - safe to unit test without the router or scanner.
"""

ALLOWED_RESOLUTIONS = (150, 300, 600, 1200)

# UI label -> scanimage --mode value
ALLOWED_MODES = {
    "Color": "Color",
    "Grayscale": "Gray",
}

# UI label -> (scanimage --format value, saved file extension)
ALLOWED_FORMATS = {
    "PDF": ("pdf", "pdf"),
    "JPG": ("jpeg", "jpg"),
}


def validate_resolution(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError("resolution must be an integer, got %r" % (value,))
    if parsed not in ALLOWED_RESOLUTIONS:
        raise ValueError(
            "resolution must be one of %r, got %r" % (ALLOWED_RESOLUTIONS, parsed)
        )
    return parsed


def validate_mode(value):
    try:
        return ALLOWED_MODES[value]
    except KeyError:
        raise ValueError(
            "mode must be one of %r, got %r" % (sorted(ALLOWED_MODES), value)
        )


def validate_format(value):
    try:
        return ALLOWED_FORMATS[value]
    except KeyError:
        raise ValueError(
            "format must be one of %r, got %r" % (sorted(ALLOWED_FORMATS), value)
        )
