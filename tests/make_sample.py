#!/usr/bin/env python3
"""
Builds small synthetic press sheets for the tests and for the website's
"Try the sample" button. No third-party packages are needed.

    python tests/make_sample.py            # writes tests/sample/sample_bar.pdf

The sheet contains one real color bar plus decoys that a naive detector would
trip over: a row of equal squares in a dieline ink, a row of RGB squares,
a registration cross in the "All" separation, a filled panel and some text.
"""
import os
import sys

MM = 72.0 / 25.4

PATCH_ALONG = 4.0   # mm, along the bar
PATCH_ACROSS = 6.0  # mm, across the bar


def _n(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def _sep(name, c1, tint="1"):
    return ("[/Separation /%s /DeviceCMYK << /FunctionType 2 /Domain [0 1] "
            "/C0 [0 0 0 0] /C1 [%s] /N 1 >>]" % (name, c1))


def build_pdf(orientation="horizontal", with_bar=True, rgb_decoy=True):
    """Return the bytes of a one-page PDF. Sizes are in mm."""
    if orientation == "horizontal":
        page_w, page_h = 160.0, 70.0
    else:
        page_w, page_h = 70.0, 160.0

    c = []  # content stream lines

    def rect(x, y, w, h):
        c.append("%s %s %s %s re f" % (_n(x * MM), _n(y * MM), _n(w * MM), _n(h * MM)))

    def cmyk(*v):
        c.append("%s k" % " ".join(_n(x) for x in v))

    def spot(cs, tint):
        c.append("/%s cs %s scn" % (cs, _n(tint)))

    # --- decoy artwork ----------------------------------------------------
    cmyk(0.08, 0.03, 0, 0)
    rect(8, 28, 30, 22)                      # a plain panel
    cmyk(0, 0.6, 0.9, 0)
    rect(42, 30, 18, 18)                     # another plain shape

    # five equal squares in the dieline ink: would look like a bar if not excluded
    for i in range(5):
        spot("CSdie", 0.2 + 0.2 * i)
        rect(70 + i * 6, 40, 6, 6)

    # a row of RGB squares
    if rgb_decoy:
        for i, rgb in enumerate([(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1)]):
            c.append("%s rg" % " ".join(str(x) for x in rgb))
            rect(70 + i * 6, 50, 6, 6)

    # registration cross in "All"
    spot("CSall", 1)
    rect(140, 30, 8, 0.5)
    rect(143.75, 26.25, 0.5, 8)

    # text
    c.append("BT /F1 8 Tf 0 g %s %s Td (SAMPLE SHEET - DECOY ARTWORK) Tj ET" % (_n(8 * MM), _n(60 * MM)))

    # --- the real bar -----------------------------------------------------
    if with_bar:
        # (kind, values) per slot; None = empty slot
        group1 = [("k", (0, 0, 0, 1)), ("k", (1, 0, 0, 0)), ("k", (0, 1, 0, 0)), ("k", (0, 0, 1, 0)),
                  ("s", 1.0), ("k", (0.5, 0.4, 0.4, 0)), ("k", (0, 0, 0, 0.5)), ("k", (0, 0, 0, 0))]
        group2 = [("k", (0, 0, 0, 1)), ("k", (1, 0, 0, 0)), ("k", (0, 1, 0, 0)), ("k", (0, 0, 1, 0)),
                  ("s", 1.0), ("s", 0.25), ("s", 0.5), ("s", 0.75)]
        slots = group1 + [None, None] + group2
        x0, y0 = 14.0, 8.0  # bar start (left edge / bottom edge) in mm
        for i, s in enumerate(slots):
            if s is None:
                continue
            if s[0] == "k":
                cmyk(*s[1])
            else:
                spot("CSspot", s[1])
            if orientation == "horizontal":
                rect(x0 + i * PATCH_ALONG, y0, PATCH_ALONG, PATCH_ACROSS)
            else:
                # vertical: patches stack from the top down
                rect(8.0, page_h - 14.0 - (i + 1) * PATCH_ALONG, PATCH_ACROSS, PATCH_ALONG)

    stream = "\n".join(c).encode("latin-1")

    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    res = ("<< /Font << /F1 5 0 R >> /ColorSpace << /CSdie %s /CSall %s /CSspot %s >> >>" % (
        _sep("Dieline", "0 1 1 0"), _sep("All", "1 1 1 1"), _sep("Sample#20Orange", "0 0.52 1 0")))
    objs[3] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %s %s] /Resources %s /Contents 4 0 R >>" % (
        _n(page_w * MM), _n(page_h * MM), res)).encode("latin-1")
    objs[4] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
    objs[5] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + objs[num] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for num in sorted(objs):
        out += b"%010d 00000 n \n" % offsets[num]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "sample", "sample_bar.pdf")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as fh:
        fh.write(build_pdf("horizontal"))
    print("wrote", target)
    sys.exit(0)
