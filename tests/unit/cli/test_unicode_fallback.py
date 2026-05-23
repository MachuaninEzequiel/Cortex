"""Tests for :mod:`cortex.cli._unicode_fallback`."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from cortex.cli._unicode_fallback import glyph, supports_unicode


class _CapturingFile:
    """File-like wrapper that exposes a settable ``encoding`` attribute.

    ``StringIO.encoding`` is read-only at the C level, so we wrap one
    instead of subclassing.
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        self._buffer = StringIO()
        self.encoding = encoding

    def write(self, value: str) -> int:
        return self._buffer.write(value)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False

    def getvalue(self) -> str:
        return self._buffer.getvalue()


def _console(encoding: str) -> Console:
    """Build a Console whose .file.encoding matches ``encoding``."""
    return Console(
        file=_CapturingFile(encoding),  # type: ignore[arg-type]
        force_terminal=True,
        width=80,
    )


class TestSupportsUnicode:
    def test_utf8_console_supports_unicode(self) -> None:
        assert supports_unicode(_console("utf-8")) is True

    def test_utf16_console_supports_unicode(self) -> None:
        assert supports_unicode(_console("utf-16-le")) is True

    def test_cp1252_console_does_not_support_unicode(self) -> None:
        assert supports_unicode(_console("cp1252")) is False

    def test_ascii_console_does_not_support_unicode(self) -> None:
        assert supports_unicode(_console("ascii")) is False

    def test_empty_encoding_does_not_support_unicode(self) -> None:
        assert supports_unicode(_console("")) is False


class TestGlyph:
    def test_returns_unicode_for_utf8_console(self) -> None:
        assert glyph("check", console=_console("utf-8")) == "✓"
        assert glyph("fail", console=_console("utf-8")) == "✗"
        assert glyph("pending", console=_console("utf-8")) == "⏸"
        assert glyph("warn", console=_console("utf-8")) == "⚠"
        assert glyph("arrow_right", console=_console("utf-8")) == "▶"
        assert glyph("ellipsis", console=_console("utf-8")) == "…"

    def test_returns_ascii_for_cp1252_console(self) -> None:
        assert glyph("check", console=_console("cp1252")) == "OK"
        assert glyph("fail", console=_console("cp1252")) == "FAIL"
        assert glyph("pending", console=_console("cp1252")) == "..."
        assert glyph("warn", console=_console("cp1252")) == "!"
        assert glyph("arrow_right", console=_console("cp1252")) == ">"
        assert glyph("ellipsis", console=_console("cp1252")) == "..."

    def test_unknown_glyph_returns_empty_string(self) -> None:
        assert glyph("does-not-exist", console=_console("utf-8")) == ""
        assert glyph("does-not-exist", console=_console("cp1252")) == ""
