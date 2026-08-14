"""Pure JPEG marker parsing: just enough to read the SOF segment.

No external imaging library needed - we only need width, height, and
component count to wrap a JPEG as a PDF page (see pdfwrap.py).
"""

_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
_NO_PAYLOAD_MARKERS = {0xD8, 0x01} | set(range(0xD0, 0xD8))


def get_jpeg_info(data):
    """Return {"width": int, "height": int, "components": int}.

    Raises ValueError if `data` isn't a JPEG or has no SOF segment.
    """
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        raise ValueError("not a JPEG: missing SOI marker")

    index = 2
    while True:
        if index + 1 >= len(data) or data[index] != 0xFF:
            raise ValueError("malformed JPEG: expected marker at offset %d" % index)

        marker = data[index + 1]

        if marker in _NO_PAYLOAD_MARKERS:
            index += 2
            continue

        if marker == 0xD9:  # EOI, no SOF found
            raise ValueError("no SOF segment found before end of JPEG")

        if index + 3 >= len(data):
            raise ValueError("malformed JPEG: truncated segment length")
        length = int.from_bytes(data[index + 2 : index + 4], "big")

        if marker in _SOF_MARKERS:
            payload = data[index + 4 : index + 2 + length]
            if len(payload) < 6:
                raise ValueError("malformed JPEG: SOF segment too short")
            height = int.from_bytes(payload[1:3], "big")
            width = int.from_bytes(payload[3:5], "big")
            components = payload[5]
            return {"width": width, "height": height, "components": components}

        index += 2 + length
