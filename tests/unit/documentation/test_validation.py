"""Tests for cortex.documentation.validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import SchemaValidationError, UnknownDocTypeError
from cortex.documentation.schemas import (
    ADRFrontmatter,
    EnterpriseFrontmatter,
    SessionFrontmatterEnterprise,
)
from cortex.documentation.validation import (
    validate_frontmatter,
    validate_path_frontmatter,
)


_NOW_ISO = datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC).isoformat()
_FP = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


def _adr_yaml(
    *,
    vault_scope: str = "local",
    extras: dict | None = None,
) -> str:
    base = {
        "schema_version": 1,
        "doc_type": "adr",
        "title": "ADR-007 Test",
        "created_at": _NOW_ISO,
        "updated_at": _NOW_ISO,
        "status": "accepted",
        "fingerprint": _FP,
        "vault_scope": vault_scope,
        "adr_number": 7,
    }
    if extras:
        base.update(extras)
    return yaml.safe_dump(base, default_flow_style=False, sort_keys=False)


def test_validate_local_adr_returns_adr_frontmatter() -> None:
    fm = validate_frontmatter(_adr_yaml())
    assert isinstance(fm, ADRFrontmatter)
    assert fm.doc_type == DocType.ADR
    assert fm.adr_number == 7


def test_validate_enterprise_adr_returns_enterprise_frontmatter() -> None:
    yaml = _adr_yaml(
        vault_scope="enterprise",
        extras={
            "owner": "ezequiel@cortex.ai",
            "team": "cortex-core",
            "classification": "internal",
            "retention_days": 365,
        },
    )
    fm = validate_frontmatter(yaml)
    assert isinstance(fm, EnterpriseFrontmatter)


def test_validate_missing_doc_type_raises() -> None:
    yaml = f"title: Foo\nstatus: draft\nfingerprint: {_FP}"
    with pytest.raises(SchemaValidationError, match="doc_type"):
        validate_frontmatter(yaml)


def test_validate_unknown_doc_type_raises() -> None:
    yaml = "doc_type: bogus\ntitle: T"
    with pytest.raises(UnknownDocTypeError, match="bogus"):
        validate_frontmatter(yaml)


def test_validate_invalid_vault_scope_raises() -> None:
    yaml = _adr_yaml(vault_scope="shared")
    with pytest.raises(SchemaValidationError, match="vault_scope"):
        validate_frontmatter(yaml)


def test_validate_malformed_yaml_raises() -> None:
    with pytest.raises(SchemaValidationError, match="Invalid YAML"):
        validate_frontmatter("doc_type: adr\nbroken: [unclosed")


def test_validate_enterprise_missing_owner_raises() -> None:
    """Enterprise scope without owner field fails."""
    yaml = _adr_yaml(vault_scope="enterprise")
    with pytest.raises(SchemaValidationError, match="owner"):
        validate_frontmatter(yaml)


def test_validate_non_string_doc_type_raises() -> None:
    yaml = "doc_type: 42\ntitle: T"
    with pytest.raises(SchemaValidationError, match="string"):
        validate_frontmatter(yaml)


def test_validate_path_frontmatter_reads_file(tmp_path: Path) -> None:
    p = tmp_path / "adr.md"
    p.write_text(f"---\n{_adr_yaml()}\n---\nBody", encoding="utf-8")
    fm = validate_path_frontmatter(p)
    assert isinstance(fm, ADRFrontmatter)


def test_validate_path_no_frontmatter_raises(tmp_path: Path) -> None:
    p = tmp_path / "plain.md"
    p.write_text("Just body", encoding="utf-8")
    with pytest.raises(SchemaValidationError, match="No frontmatter"):
        validate_path_frontmatter(p)


def test_validate_path_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(SchemaValidationError, match="File not found"):
        validate_path_frontmatter(tmp_path / "nope.md")


def test_validate_routes_session_to_session_frontmatter() -> None:
    yaml = "\n".join([
        "doc_type: session",
        "title: T",
        f"created_at: {_NOW_ISO}",
        f"updated_at: {_NOW_ISO}",
        "status: completed",
        f"fingerprint: {_FP}",
        "session_id: abc123",
    ])
    fm = validate_frontmatter(yaml)
    assert fm.doc_type == DocType.SESSION


def test_validate_routes_session_enterprise() -> None:
    yaml = "\n".join([
        "doc_type: session",
        "title: T",
        f"created_at: {_NOW_ISO}",
        f"updated_at: {_NOW_ISO}",
        "status: completed",
        f"fingerprint: {_FP}",
        "vault_scope: enterprise",
        "session_id: abc",
        "owner: ezequiel@cortex.ai",
        "team: cortex-core",
        "classification: internal",
        "retention_days: 365",
    ])
    fm = validate_frontmatter(yaml)
    assert isinstance(fm, SessionFrontmatterEnterprise)
