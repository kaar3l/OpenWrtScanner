"""Wrap a single JPEG as a one-page PDF, by hand - no external PDF library.

We always scan to JPEG (see scan.py); when the user asked for PDF output we
wrap that same JPEG into a minimal PDF here. This means the JPEG we scanned
doubles as the thumbnail source for both formats, and avoids adding a PDF
toolchain (poppler/ghostscript/img2pdf) to the router.
"""

from .jpeginfo import get_jpeg_info


def wrap_jpeg_as_pdf(jpeg_bytes, dpi):
    info = get_jpeg_info(jpeg_bytes)
    width_pt = info["width"] * 72.0 / dpi
    height_pt = info["height"] * 72.0 / dpi
    colorspace = "DeviceGray" if info["components"] == 1 else "DeviceRGB"

    content_stream = ("q %s 0 0 %s 0 0 cm /Im0 Do Q" % (width_pt, height_pt)).encode("ascii")

    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj3 = (
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] "
        "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
        % (width_pt, height_pt)
    ).encode("ascii")
    obj4_dict = (
        "<< /Type /XObject /Subtype /Image /Width %d /Height %d "
        "/ColorSpace /%s /BitsPerComponent 8 /Filter /DCTDecode /Length %d >>"
        % (info["width"], info["height"], colorspace, len(jpeg_bytes))
    ).encode("ascii")
    obj4 = obj4_dict + b"\nstream\n" + jpeg_bytes + b"\nendstream"
    obj5_dict = ("<< /Length %d >>" % len(content_stream)).encode("ascii")
    obj5 = obj5_dict + b"\nstream\n" + content_stream + b"\nendstream"

    parts = [obj1, obj2, obj3, obj4, obj5]

    buf = bytearray()
    buf += b"%PDF-1.4\n"
    offsets = [0] * (len(parts) + 1)
    for i, body in enumerate(parts, start=1):
        offsets[i] = len(buf)
        buf += ("%d 0 obj\n" % i).encode("ascii")
        buf += body
        buf += b"\nendobj\n"

    xref_offset = len(buf)
    count = len(parts) + 1  # + the free object 0
    buf += ("xref\n0 %d\n" % count).encode("ascii")
    buf += b"0000000000 65535 f \n"
    for i in range(1, len(parts) + 1):
        buf += ("%010d 00000 n \n" % offsets[i]).encode("ascii")
    buf += b"trailer\n"
    buf += ("<< /Size %d /Root 1 0 R >>\n" % count).encode("ascii")
    buf += b"startxref\n"
    buf += ("%d\n" % xref_offset).encode("ascii")
    buf += b"%%EOF"

    return bytes(buf)
