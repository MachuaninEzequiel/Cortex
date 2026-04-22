"""Tests for MarkdownParser."""

import pytest
from pathlib import Path


def test_parse_with_frontmatter(tmp_path, markdown_parser):
    note = tmp_path / "auth.md"
    note.write_text(
        "---\ntitle: Auth Guide\ntags: [auth, security]\n---\n\n"
        "# Auth Guide\n\nThis covers [[login]] and [[oauth]].\n"
    )
    doc = markdown_parser.parse(note)
    assert doc.title == "Auth Guide"
    assert "auth" in doc.tags
    assert "login" in doc.links
    assert "oauth" in doc.links


def test_parse_without_frontmatter(tmp_path, markdown_parser):
    note = tmp_path / "quick_note.md"
    note.write_text("# Quick Note\n\nSome content here.\n")
    doc = markdown_parser.parse(note)
    assert doc.title == "Quick Note"
    assert doc.links == []


def test_parse_inline_hashtags(tmp_path, markdown_parser):
    note = tmp_path / "tagged.md"
    note.write_text("Some text with #python and #ai tags.\n")
    doc = markdown_parser.parse(note)
    assert "python" in doc.tags
    assert "ai" in doc.tags


def test_parse_wiki_links_with_aliases(tmp_path, markdown_parser):
    note = tmp_path / "aliased.md"
    note.write_text("See [[auth|Authentication]] and [[api#section]].\n")
    doc = markdown_parser.parse(note)
    assert "auth" in doc.links
    assert "api" in doc.links
