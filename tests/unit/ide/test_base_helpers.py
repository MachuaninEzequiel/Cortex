"""Unit tests for shared marker-block editing helpers in cortex.ide.base.

Obra 02 / Fase 1 — generalization of the codex.py BEGIN/END marker pattern.
These helpers are pure (string in, string out); no I/O is tested here.
"""

from __future__ import annotations

import pytest

from cortex.ide.base import (
    CORTEX_MARKER_CLOSE,
    CORTEX_MARKER_OPEN,
    extract_marker_blocks,
    has_marker_block,
    is_content_identical_to_bundle,
    is_cortex_owned_file,
    strip_marker_blocks,
    upsert_marker_block,
)

TOML_OPEN = "# BEGIN CORTEX MCP (auto-generated, do not edit)"
TOML_CLOSE = "# END CORTEX MCP"


def _md_block(body: str = "cortex rules") -> str:
    return f"{CORTEX_MARKER_OPEN}\n{body}\n{CORTEX_MARKER_CLOSE}"


# ---------------------------------------------------------------------------
# roundtrip: insert -> extract -> strip
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_insert_then_extract_returns_block_verbatim(self):
        block = _md_block("workflow instructions")
        content = upsert_marker_block("# My project\n", block)
        found = extract_marker_blocks(content)
        assert len(found) == 1
        assert "workflow instructions" in found[0]
        assert found[0].startswith(CORTEX_MARKER_OPEN)
        assert found[0].endswith(CORTEX_MARKER_CLOSE)

    def test_strip_after_insert_restores_original(self):
        original = "# My project\n\nSome intro text.\n"
        content = upsert_marker_block(original, _md_block())
        cleaned = strip_marker_blocks(content)
        assert cleaned == original

    def test_strip_file_with_only_cortex_block_yields_empty(self):
        content = upsert_marker_block("", _md_block())
        assert strip_marker_blocks(content) == ""

    def test_extract_on_content_without_markers_is_empty(self):
        assert extract_marker_blocks("no markers here") == []
        assert strip_marker_blocks("no markers here") == "no markers here"


# ---------------------------------------------------------------------------
# upsert idempotencia (byte-equality)
# ---------------------------------------------------------------------------


class TestUpsertIdempotency:
    def test_double_upsert_empty_file_byte_equal(self):
        block = _md_block()
        once = upsert_marker_block("", block)
        twice = upsert_marker_block(once, block)
        assert once == twice

    def test_double_upsert_existing_file_byte_equal(self):
        existing = "# User header\n\nUser body line.\n"
        block = _md_block("v2")
        once = upsert_marker_block(existing, block)
        twice = upsert_marker_block(once, block)
        assert once == twice

    def test_upsert_replaces_block_not_duplicate(self):
        existing = "keep me\n" + _md_block("old version") + "\ntail\n"
        result = upsert_marker_block(existing, _md_block("new version"))
        assert result.count(CORTEX_MARKER_OPEN) == 1
        assert "new version" in result
        assert "old version" not in result

    def test_upsert_collapses_multiple_blocks_into_one(self):
        existing = _md_block("first") + "\nmid\n" + _md_block("second")
        result = upsert_marker_block(existing, _md_block("merged"))
        assert result.count(CORTEX_MARKER_OPEN) == 1
        assert "merged" in result


# ---------------------------------------------------------------------------
# contenido mixto preservado
# ---------------------------------------------------------------------------


class TestMixedContentPreserved:
    def test_strip_preserves_user_content_before_and_after(self):
        before = "# Title\nuser intro\n"
        after = "\nfooter kept\n"
        content = before + _md_block("junk") + after
        cleaned = strip_marker_blocks(content)
        assert "user intro" in cleaned
        assert "footer kept" in cleaned
        assert "junk" not in cleaned
        assert CORTEX_MARKER_OPEN not in cleaned

    def test_upsert_preserves_user_content_outside_markers(self):
        existing = "# User header\nuser body\n"
        result = upsert_marker_block(existing, _md_block("cortex"))
        assert result.startswith("# User header\nuser body")
        assert "cortex" in result

    def test_custom_toml_markers_do_not_touch_markdown_blocks(self):
        md_content = "x\n" + _md_block() + "\ny"
        result = strip_marker_blocks(md_content, TOML_OPEN, TOML_CLOSE)
        assert result == md_content  # untouched: different marker flavour

    def test_custom_toml_roundtrip(self):
        block = f"{TOML_OPEN}\n[mcp_servers.cortex]\nenabled = true\n{TOML_CLOSE}"
        content = upsert_marker_block("[other]\nkey = 1\n", block, TOML_OPEN, TOML_CLOSE)
        assert has_marker_block(content, TOML_OPEN, TOML_CLOSE)
        assert not has_marker_block(content)  # markdown markers absent
        cleaned = strip_marker_blocks(content, TOML_OPEN, TOML_CLOSE)
        assert cleaned == "[other]\nkey = 1\n"


# ---------------------------------------------------------------------------
# archivo 100% Cortex detectable
# ---------------------------------------------------------------------------


class TestCortexOwnedDetection:
    def test_markers_only_file_is_cortex_owned(self):
        assert is_cortex_owned_file(_md_block())

    def test_markers_only_with_surrounding_whitespace_is_cortex_owned(self):
        assert is_cortex_owned_file("\n\n" + _md_block() + "\n\n")

    def test_mixed_file_is_not_cortex_owned(self):
        mixed = "user text\n" + _md_block() + "\nmore user text"
        assert not is_cortex_owned_file(mixed)

    def test_empty_content_is_not_cortex_owned(self):
        assert not is_cortex_owned_file("")
        assert not is_cortex_owned_file("\n \n")

    def test_identical_bundle_detected_even_with_new_timestamp(self):
        bundle = (
            "header\nLast sync: 2026-08-01T10:00:00Z\ncore body\n"
            + CORTEX_MARKER_OPEN
            + "\nx\n"
            + CORTEX_MARKER_CLOSE
        )
        on_disk = (
            "header\nLast sync: 2026-08-09T23:59:59Z\ncore body\n"
            + CORTEX_MARKER_OPEN
            + "\nx\n"
            + CORTEX_MARKER_CLOSE
        )
        assert is_content_identical_to_bundle(on_disk, bundle)

    def test_different_body_is_not_identical_to_bundle(self):
        bundle = "generated by cortex\n"
        user_edited = "generated by cortex\nuser edit\n"
        assert not is_content_identical_to_bundle(user_edited, bundle)

    def test_timestamp_check_can_be_disabled(self):
        a = "Last sync: 2026-01-01T00:00:00Z\nbody\n"
        b = "Last sync: 2026-12-31T00:00:00Z\nbody\n"
        assert is_content_identical_to_bundle(a, b, ignore_timestamps=False) is False

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            ("", False),
            ("plain user file", False),
            (_md_block(), True),
        ],
    )
    def test_parametrized_ownership(self, content, expected):
        assert is_cortex_owned_file(content) is expected
