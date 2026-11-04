"""Minimal text extraction for simple, uncompressed PDFs (Tj / TJ operators)."""

import re

_STR = re.compile(rb"\((?:\\.|[^\\()])*\)")
_OPS = re.compile(rb"(\[.*?\]|\((?:\\.|[^\\()])*\))\s*(TJ|Tj|'|\")", re.S)
_ESC = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"(": b"(", b")": b")", b"\\": b"\\"}


def _unescape(s: bytes) -> str:
    out, i = bytearray(), 0
    while i < len(s):
        if s[i : i + 1] == b"\\" and i + 1 < len(s):
            out += _ESC.get(s[i + 1 : i + 2], s[i + 1 : i + 2])
            i += 2
        else:
            out += s[i : i + 1]
            i += 1
    return out.decode("latin-1")


def pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise ValueError("not a PDF")
    lines = []
    for m in _OPS.finditer(data):
        parts = _STR.findall(m.group(1))
        lines.append("".join(_unescape(p[1:-1]) for p in parts))
    return "\n".join(lines)
