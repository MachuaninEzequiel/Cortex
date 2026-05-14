"""Tests for cortex.documentation.doc_type."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.documentation.doc_type import (
    VALID_STATUSES,
    DocType,
    all_doc_types,
    doc_type_from_path,
    doc_type_from_str,
    promotable_doc_types,
)
from cortex.documentation.errors import UnknownDocTypeError


# --- Enum integrity --------------------------------------------------------


def test_doc_type_enum_has_exactly_12_values() -> None:
    assert len(list(DocType)) == 12


def test_all_doc_types_have_string_value() -> None:
    for dt in DocType:
        assert isinstance(dt.value, str)
        assert len(dt.value) > 0


def test_doc_type_str_inheritance() -> None:
    """DocType inherits from str so it serializes directly."""
    assert isinstance(DocType.ADR, str)
    assert DocType.ADR == "adr"


# --- doc_type_from_str -----------------------------------------------------


def test_doc_type_from_str_valid() -> None:
    assert doc_type_from_str("adr") == DocType.ADR
    assert doc_type_from_str("session") == DocType.SESSION


def test_doc_type_from_str_invalid_raises() -> None:
    with pytest.raises(UnknownDocTypeError, match="bogus"):
        doc_type_from_str("bogus")


# --- doc_type_from_path ----------------------------------------------------


def test_doc_type_from_path_session() -> None:
    assert doc_type_from_path(Path("vault/sessions/2026-01-01_foo.md")) == DocType.SESSION


def test_doc_type_from_path_adr_by_filename_prefix() -> None:
    assert doc_type_from_path(Path("vault/decisions/ADR-007-foo.md")) == DocType.ADR


def test_doc_type_from_path_adr_case_insensitive() -> None:
    assert doc_type_from_path(Path("vault/decisions/adr-007-foo.md")) == DocType.ADR


def test_doc_type_from_path_decision_non_adr() -> None:
    assert doc_type_from_path(Path("vault/decisions/DEC-2026-05-14-foo.md")) == DocType.DECISION


def test_doc_type_from_path_runbook() -> None:
    assert doc_type_from_path(Path("vault/runbooks/RB-deploy.md")) == DocType.RUNBOOK


def test_doc_type_from_path_unknown_returns_none() -> None:
    assert doc_type_from_path(Path("vault/random/x.md")) is None


def test_doc_type_from_path_root_file_returns_none() -> None:
    assert doc_type_from_path(Path("CONTEXT.md")) is None


def test_doc_type_from_path_all_known_subfolders() -> None:
    cases = {
        "sessions": DocType.SESSION,
        "handoffs": DocType.HANDOFF,
        "specs": DocType.SPEC,
        "incidents": DocType.INCIDENT,
        "postmortems": DocType.POSTMORTEM,
        "runbooks": DocType.RUNBOOK,
        "architecture": DocType.ARCHITECTURE,
        "changelog": DocType.CHANGELOG,
        "hu": DocType.HU,
        "glossary": DocType.GLOSSARY,
    }
    for sub, expected in cases.items():
        assert doc_type_from_path(Path(f"vault/{sub}/foo.md")) == expected


# --- VALID_STATUSES --------------------------------------------------------


def test_valid_statuses_has_entry_for_each_doc_type() -> None:
    for dt in DocType:
        assert dt in VALID_STATUSES
        assert isinstance(VALID_STATUSES[dt], frozenset)
        assert len(VALID_STATUSES[dt]) > 0


# --- Helpers ---------------------------------------------------------------


def test_all_doc_types_returns_12() -> None:
    assert len(all_doc_types()) == 12


def test_promotable_doc_types_excludes_handoff_and_hu() -> None:
    promotable = promotable_doc_types()
    assert DocType.HANDOFF not in promotable
    assert DocType.HU not in promotable
    assert DocType.ADR in promotable
    assert DocType.SESSION in promotable  # promoted as summary
    assert len(promotable) == 10
