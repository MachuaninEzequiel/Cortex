"""Tests for :mod:`cortex.documenter.diff_parser` (T1.4 helper)."""

from __future__ import annotations

from pathlib import Path

from cortex.documenter.diff_parser import parse_name_status


def test_empty_input_returns_empty() -> None:
    assert parse_name_status("") == []


def test_added_modified_deleted() -> None:
    out = "A\tsrc/new.py\nM\tsrc/foo.py\nD\tsrc/old.py\n"
    entries = parse_name_status(out)
    assert [e.action for e in entries] == ["added", "modified", "deleted"]
    assert [e.path for e in entries] == [
        Path("src/new.py"),
        Path("src/foo.py"),
        Path("src/old.py"),
    ]
    assert all(e.old_path is None for e in entries)


def test_renamed_includes_old_and_new() -> None:
    entries = parse_name_status("R100\tsrc/old_name.py\tsrc/new_name.py\n")
    assert len(entries) == 1
    assert entries[0].action == "renamed"
    assert entries[0].path == Path("src/new_name.py")
    assert entries[0].old_path == Path("src/old_name.py")


def test_copied_treated_like_rename() -> None:
    entries = parse_name_status("C75\tsrc/template.py\tsrc/copy.py\n")
    assert entries[0].action == "copied"
    assert entries[0].old_path == Path("src/template.py")
    assert entries[0].path == Path("src/copy.py")


def test_type_change_treated_as_modified() -> None:
    entries = parse_name_status("T\tsrc/link.py\n")
    assert entries[0].action == "modified"


def test_unknown_status_falls_back_to_modified() -> None:
    entries = parse_name_status("X\tsrc/weird.py\n")
    assert entries[0].action == "modified"


def test_blank_and_malformed_lines_skipped() -> None:
    entries = parse_name_status("\n\nA\tok.py\n  \nbogus\n")
    assert [e.path for e in entries] == [Path("ok.py")]


def test_crlf_line_endings_ok() -> None:
    out = "A\tnew.py\r\nM\tfoo.py\r\n"
    entries = parse_name_status(out)
    assert [e.path for e in entries] == [Path("new.py"), Path("foo.py")]
