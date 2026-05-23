"""Tests for the Pluggable Middle Phase 09.B ``design`` doc type.

Covers:

* Schema validation (``DesignFrontmatter``).
* Routing entry (``DOC_TYPE_ROUTING[DocType.DESIGN]``).
* Canonical writer end-to-end (``write_design_note`` →
  ``vault/designs/<session_id>.md``).
* Template rendering (all four sections + empty-section omission).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.documentation import write_design_note, write_design_note_canonical
from cortex.documentation.data import DesignDocData
from cortex.documentation.doc_type import VALID_STATUSES, DocType
from cortex.documentation.errors import SchemaValidationError
from cortex.documentation.routing import resolve_route
from cortex.documentation.schemas import SCHEMA_BY_TYPE, DesignFrontmatter
from cortex.documentation.templates_engine import render_template


class _PathVault:
    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, rel_path: str) -> bool:  # noqa: ARG002
        return False


@pytest.fixture
def vault(tmp_path: Path) -> _PathVault:
    return _PathVault(tmp_path)


# ---------------------------------------------------------------------------
# Doc type / routing / schema registry
# ---------------------------------------------------------------------------


class TestDesignDocTypeWiring:
    def test_design_is_in_doc_type_enum(self) -> None:
        assert DocType.DESIGN.value == "design"

    def test_design_has_valid_statuses(self) -> None:
        assert VALID_STATUSES[DocType.DESIGN] == frozenset(
            {"draft", "approved", "superseded"}
        )

    def test_design_is_in_routing_table(self) -> None:
        route = resolve_route(DocType.DESIGN)
        assert route.subfolder == "designs"
        assert route.filename_template == "{session_id}.md"
        # Not promotable to enterprise.
        assert route.promotable is False

    def test_design_routes_to_canonical_writer(self) -> None:
        route = resolve_route(DocType.DESIGN)
        assert route.writer is write_design_note

    def test_design_schema_registered(self) -> None:
        assert SCHEMA_BY_TYPE[DocType.DESIGN] is DesignFrontmatter

    def test_canonical_alias_is_same_function(self) -> None:
        assert write_design_note_canonical is write_design_note


# ---------------------------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------------------------


class TestDesignFrontmatter:
    def test_requires_session_id(self) -> None:
        with pytest.raises(ValueError):
            DesignFrontmatter(
                schema_version=1,
                doc_type=DocType.DESIGN,
                title="x",
                created_at="2026-05-17T00:00:00Z",  # type: ignore[arg-type]
                updated_at="2026-05-17T00:00:00Z",  # type: ignore[arg-type]
                tags=[],
                status="draft",
                links=[],
                vault_scope="local",
                fingerprint="abc",
                session_id="",
                spec_path="x.md",
            )

    def test_requires_spec_path(self) -> None:
        with pytest.raises(ValueError):
            DesignFrontmatter(
                schema_version=1,
                doc_type=DocType.DESIGN,
                title="x",
                created_at="2026-05-17T00:00:00Z",  # type: ignore[arg-type]
                updated_at="2026-05-17T00:00:00Z",  # type: ignore[arg-type]
                tags=[],
                status="draft",
                links=[],
                vault_scope="local",
                fingerprint="abc",
                session_id="s",
                spec_path="",
            )


# ---------------------------------------------------------------------------
# Canonical writer end-to-end
# ---------------------------------------------------------------------------


class TestWriteDesignNote:
    def test_persists_to_vault_designs(self, vault: _PathVault, tmp_path: Path) -> None:
        data = DesignDocData(
            title="Add JWT refresh",
            session_id="2026-05-17_jwt",
            spec_path="vault/specs/2026-05-17_jwt.md",
            architecture_decision="Centralise refresh logic in middleware.",
            data_model_changes=["Add `refresh_token` column"],
            api_contracts=["def refresh(token: str) -> Token"],
            test_plan=["tests/auth/test_refresh.py"],
            risks=["Token rotation invalidates active sessions"],
        )
        path = write_design_note(data, vault=vault)
        assert path.is_file()
        assert path.parent == tmp_path / "designs"
        assert path.name == "2026-05-17_jwt.md"

    def test_default_status_is_draft(self, vault: _PathVault) -> None:
        data = DesignDocData(
            title="t",
            session_id="2026-05-17_a",
            spec_path="vault/specs/2026-05-17_a.md",
        )
        path = write_design_note(data, vault=vault)
        body = path.read_text(encoding="utf-8")
        assert "status: draft" in body

    def test_missing_session_id_raises(self, vault: _PathVault) -> None:
        data = DesignDocData(title="t", session_id="", spec_path="x.md")
        with pytest.raises(SchemaValidationError, match="session_id"):
            write_design_note(data, vault=vault)

    def test_missing_spec_path_raises(self, vault: _PathVault) -> None:
        data = DesignDocData(title="t", session_id="s", spec_path="")
        with pytest.raises(SchemaValidationError, match="spec_path"):
            write_design_note(data, vault=vault)

    def test_default_title_when_omitted(self, vault: _PathVault) -> None:
        data = DesignDocData(
            title="",
            session_id="2026-05-17_b",
            spec_path="vault/specs/x.md",
        )
        path = write_design_note(data, vault=vault)
        body = path.read_text(encoding="utf-8")
        assert "Design for 2026-05-17_b" in body


# ---------------------------------------------------------------------------
# Template rendering (in isolation, no writer)
# ---------------------------------------------------------------------------


class TestDesignTemplate:
    def _ctx(self, **overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "title": "Sample",
            "session_id": "2026-05-17_demo",
            "spec_path": "vault/specs/demo.md",
            "tags": ["design"],
            "links": [],
            "status": "draft",
            "owner": None,
            "team": None,
            "classification": None,
            "retention_days": None,
            "architecture_decision": "Use the existing middleware.",
            "data_model_changes": [],
            "api_contracts": [],
            "test_plan": [],
            "risks": [],
        }
        base.update(overrides)
        return base

    def test_renders_all_sections(self) -> None:
        out = render_template(
            "design.md.j2",
            self._ctx(
                data_model_changes=["Add column"],
                api_contracts=["fn foo()"],
                test_plan=["test_foo"],
                risks=["lock-in"],
            ),
        )
        assert "## Architecture decision" in out
        assert "Use the existing middleware." in out
        assert "## Data model changes" in out
        assert "Add column" in out
        assert "## API contracts" in out
        assert "fn foo()" in out
        assert "## Test plan" in out
        assert "test_foo" in out
        assert "## Risks" in out
        assert "lock-in" in out

    def test_omits_empty_sections(self) -> None:
        out = render_template("design.md.j2", self._ctx())
        assert "## Architecture decision" in out
        assert "## Data model changes" not in out
        assert "## API contracts" not in out
        assert "## Test plan" not in out
        assert "## Risks" not in out
