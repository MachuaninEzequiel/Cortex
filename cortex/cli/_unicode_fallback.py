"""Cross-platform glyph helpers — fallback to ASCII when the console
encoding cannot render unicode (e.g. ``cmd.exe`` defaulting to cp1252).

The Phase 06 TUI uses a small set of decorative glyphs (✓, ✗, ⏸, ⚠, ▶, …).
Hard-coding them breaks on Windows legacy consoles where the unicode
points are replaced with ``?`` or raise ``UnicodeEncodeError`` from
``rich``'s file writer. ``glyph(name, console=...)`` returns the right
character for the active console.

This helper is intentionally cheap: a dict lookup plus a substring check
on ``console.file.encoding``. No locale probing, no platform branching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

_UNICODE_GLYPHS: dict[str, str] = {
    "check": "✓",
    "fail": "✗",
    "pending": "⏸",
    "warn": "⚠",
    "arrow_right": "▶",
    "ellipsis": "…",
}

_ASCII_FALLBACK: dict[str, str] = {
    "check": "OK",
    "fail": "FAIL",
    "pending": "...",
    "warn": "!",
    "arrow_right": ">",
    "ellipsis": "...",
}


def supports_unicode(console: Console) -> bool:
    """Return True if ``console.file.encoding`` clearly supports unicode.

    Errs on the safe side: any encoding string containing ``utf`` or
    ``unicode`` is accepted; anything else (cp1252, ascii, latin-1,
    empty, missing) falls back to ASCII.
    """
    raw = getattr(console.file, "encoding", None)
    encoding = (raw or "").lower()
    return any(token in encoding for token in ("utf", "unicode"))


def glyph(name: str, *, console: Console) -> str:
    """Return the unicode glyph for ``name``, or its ASCII fallback.

    Unknown names return an empty string — the caller can branch on
    truthiness without worrying about None-vs-empty handling.
    """
    if supports_unicode(console):
        return _UNICODE_GLYPHS.get(name, "")
    return _ASCII_FALLBACK.get(name, "")


__all__ = ["glyph", "supports_unicode"]
