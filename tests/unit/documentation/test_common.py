"""Tests for cortex.documentation.common."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.documentation.common import (
    compute_fingerprint,
    has_frontmatter,
    parse_frontmatter_lenient,
    slugify,
    split_frontmatter_and_body,
    yaml_dump_safe,
    yaml_load_safe,
)


# --- slugify ----------------------------------------------------------------


def test_slugify_basic() -> None:
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_chars() -> None:
    assert slugify("Hello! World? Foo&Bar") == "hello-world-foobar"


def test_slugify_unicode_accents_stripped() -> None:
    assert slugify("Cafe & Sueno") == "cafe-sueno"
    assert slugify("Café & Sueño") == "cafe-sueno"


def test_slugify_empty_returns_empty() -> None:
    assert slugify("") == ""


def test_slugify_only_special_chars_returns_empty() -> None:
    assert slugify("!@#$%") == ""


def test_slugify_collapses_repeated_separators() -> None:
    assert slugify("foo   bar___baz") == "foo-bar-baz"


def test_slugify_trims_edges() -> None:
    assert slugify("  -hello-  ") == "hello"


def test_slugify_preserves_existing_dashes() -> None:
    assert slugify("foo-bar") == "foo-bar"


# --- compute_fingerprint ----------------------------------------------------


def test_compute_fingerprint_deterministic() -> None:
    assert compute_fingerprint("test") == compute_fingerprint("test")


def test_compute_fingerprint_length_is_64_hex() -> None:
    fp = compute_fingerprint("anything")
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_compute_fingerprint_different_content_different_fp() -> None:
    assert compute_fingerprint("a") != compute_fingerprint("b")


def test_compute_fingerprint_handles_unicode() -> None:
    fp = compute_fingerprint("Cafe ñu")
    assert len(fp) == 64


def test_compute_fingerprint_empty_string() -> None:
    # SHA-256 of empty string is a well-known constant.
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_fingerprint("") == expected


# --- yaml_dump_safe / yaml_load_safe ---------------------------------------


def test_yaml_dump_safe_basic() -> None:
    out = yaml_dump_safe({"title": "Foo", "tags": ["a", "b"]})
    assert "title: Foo" in out
    assert "- a" in out
    assert "- b" in out


def test_yaml_dump_safe_preserves_insertion_order() -> None:
    out = yaml_dump_safe({"z": 1, "a": 2, "m": 3})
    lines = [line for line in out.strip().split("\n") if line]
    assert lines[0].startswith("z:")
    assert lines[1].startswith("a:")
    assert lines[2].startswith("m:")


def test_yaml_dump_safe_unicode() -> None:
    out = yaml_dump_safe({"title": "Café"})
    assert "Café" in out  # allow_unicode=True


def test_yaml_load_safe_empty_returns_empty_dict() -> None:
    assert yaml_load_safe("") == {}
    assert yaml_load_safe("   ") == {}
    assert yaml_load_safe("\n\n") == {}


def test_yaml_load_safe_basic() -> None:
    assert yaml_load_safe("title: Foo\ntags: [a, b]") == {
        "title": "Foo",
        "tags": ["a", "b"],
    }


def test_yaml_load_safe_rejects_non_mapping() -> None:
    with pytest.raises(ValueError, match="mapping"):
        yaml_load_safe("- one\n- two\n")


def test_yaml_dump_then_load_roundtrip() -> None:
    data = {"title": "Foo", "tags": ["a"], "count": 3, "status": "draft"}
    loaded = yaml_load_safe(yaml_dump_safe(data))
    assert loaded == data


# --- split_frontmatter_and_body / has_frontmatter --------------------------


def test_split_frontmatter_basic() -> None:
    content = "---\ntitle: Foo\n---\nBody text"
    fm, body = split_frontmatter_and_body(content)
    assert "title: Foo" in fm
    assert body == "Body text"


def test_split_frontmatter_with_blank_line_after() -> None:
    content = "---\ntitle: Foo\n---\n\nBody text"
    fm, body = split_frontmatter_and_body(content)
    assert "title: Foo" in fm
    assert body == "Body text"


def test_split_frontmatter_no_frontmatter() -> None:
    fm, body = split_frontmatter_and_body("Just body")
    assert fm == ""
    assert body == "Just body"


def test_split_frontmatter_open_no_close_returns_no_split() -> None:
    """Malformed: open --- without close."""
    fm, body = split_frontmatter_and_body("---\ntitle: Foo\nNo close")
    assert fm == ""


def test_has_frontmatter_true() -> None:
    assert has_frontmatter("---\nkey: val\n---\nbody")


def test_has_frontmatter_false_plain_body() -> None:
    assert not has_frontmatter("Just body")


def test_has_frontmatter_false_unclosed() -> None:
    assert not has_frontmatter("---\nkey: val\nNo close")


# --- parse_frontmatter_lenient ---------------------------------------------


def test_parse_frontmatter_lenient_basic(tmp_path: Path) -> None:
    p = tmp_path / "note.md"
    p.write_text("---\ntitle: Foo\ntags: [a, b]\n---\nbody", encoding="utf-8")
    fm = parse_frontmatter_lenient(p)
    assert fm == {"title": "Foo", "tags": ["a", "b"]}


def test_parse_frontmatter_lenient_missing_file_returns_empty(tmp_path: Path) -> None:
    assert parse_frontmatter_lenient(tmp_path / "nope.md") == {}


def test_parse_frontmatter_lenient_no_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "plain.md"
    p.write_text("Just body, no frontmatter.", encoding="utf-8")
    assert parse_frontmatter_lenient(p) == {}


def test_parse_frontmatter_lenient_malformed_yaml_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "bad.md"
    p.write_text("---\nbad yaml: [unclosed\n---\nbody", encoding="utf-8")
    assert parse_frontmatter_lenient(p) == {}


def test_parse_frontmatter_lenient_non_mapping_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "list.md"
    p.write_text("---\n- one\n- two\n---\nbody", encoding="utf-8")
    assert parse_frontmatter_lenient(p) == {}
