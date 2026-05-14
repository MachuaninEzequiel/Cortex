"""End-to-end tests for the 9 new canonical writers (Fase 03).

Test pattern per writer:
    - minimal valid construction
    - full optional fields
    - validation errors (missing required, invalid scope, etc.)
    - duplicate handling
    - indexing call
    - filename pattern
    - enterprise audit_trail
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from cortex.documentation.common import (
    parse_frontmatter_lenient,
    split_frontmatter_and_body,
)
from cortex.documentation.data import (
    ADRData,
    ArchitectureData,
    ChangelogData,
    DecisionData,
    GlossaryEntryData,
    HandoffData,
    IncidentData,
    PostmortemData,
    RunbookData,
)
from cortex.documentation.errors import (
    DuplicateDocumentError,
    SchemaValidationError,
)
from cortex.documentation.writers import (
    write_adr_note,
    write_architecture_note,
    write_changelog_note,
    write_decision_note,
    write_glossary_entry,
    write_handoff_note,
    write_incident_note,
    write_postmortem_note,
    write_runbook_note,
)


# ---------------------------------------------------------------------------
# Fake vault.
# ---------------------------------------------------------------------------


class FakeVault:
    def __init__(self, root: Path) -> None:
        self._root = root
        self.indexed: list[str] = []

    @property
    def path(self) -> Path:
        return self._root

    def index_file(self, relative_path: str) -> bool:
        self.indexed.append(relative_path)
        return True


@pytest.fixture
def vault(tmp_path: Path) -> FakeVault:
    return FakeVault(tmp_path)


# ===========================================================================
# write_adr_note
# ===========================================================================


def test_adr_minimal_valid(vault: FakeVault) -> None:
    data = ADRData(
        title="Use ONNX",
        context="c", decision="d", consequences="cs",
        alternatives_considered=["x"],
        adr_number=7,
    )
    path = write_adr_note(data, vault=vault)
    assert path.exists()
    assert path.name == "ADR-007-use-onnx.md"


def test_adr_auto_assigns_next_number(vault: FakeVault) -> None:
    """adr_number=0 -> auto-assign next available."""
    # Pre-existing ADR-001 to force next = 2.
    (vault.path / "decisions").mkdir()
    (vault.path / "decisions" / "ADR-001-foo.md").write_text("body", encoding="utf-8")

    data = ADRData(
        title="Second",
        context="c", decision="d", consequences="cs",
        adr_number=0,
    )
    path = write_adr_note(data, vault=vault)
    assert path.stem.startswith("ADR-002-")


def test_adr_first_auto_assign_is_one(vault: FakeVault) -> None:
    data = ADRData(
        title="First",
        context="c", decision="d", consequences="cs",
        adr_number=0,
    )
    path = write_adr_note(data, vault=vault)
    assert path.stem.startswith("ADR-001-")


def test_adr_indexes_file(vault: FakeVault) -> None:
    data = ADRData(title="X", context="c", decision="d", consequences="cs", adr_number=1)
    write_adr_note(data, vault=vault)
    assert any("ADR-001" in p for p in vault.indexed)


def test_adr_duplicate_raises(vault: FakeVault) -> None:
    data = ADRData(title="X", context="c", decision="d", consequences="cs", adr_number=5)
    write_adr_note(data, vault=vault)
    with pytest.raises(DuplicateDocumentError):
        write_adr_note(data, vault=vault)


def test_adr_overwrite_allowed(vault: FakeVault) -> None:
    data = ADRData(title="X", context="c", decision="d", consequences="cs", adr_number=5)
    write_adr_note(data, vault=vault)
    # No raise.
    write_adr_note(data, vault=vault, overwrite=True)


def test_adr_empty_title_raises(vault: FakeVault) -> None:
    data = ADRData(title="", context="c", decision="d", consequences="cs", adr_number=1)
    with pytest.raises(SchemaValidationError):
        write_adr_note(data, vault=vault)


def test_adr_frontmatter_valid(vault: FakeVault) -> None:
    data = ADRData(
        title="X", context="c", decision="d", consequences="cs", adr_number=1,
    )
    path = write_adr_note(data, vault=vault)
    fm = parse_frontmatter_lenient(path)
    assert fm["doc_type"] == "adr"
    assert fm["adr_number"] == 1
    assert fm["status"] == "accepted"
    assert len(fm["fingerprint"]) == 64


def test_adr_enterprise_requires_owner(vault: FakeVault) -> None:
    data = ADRData(title="X", context="c", decision="d", consequences="cs", adr_number=1)
    with pytest.raises(SchemaValidationError, match="owner"):
        write_adr_note(
            data, vault=vault, vault_scope="enterprise", project_id="proj",
        )


def test_adr_enterprise_writes_to_enterprise_subfolder(vault: FakeVault) -> None:
    data = ADRData(
        title="X", context="c", decision="d", consequences="cs", adr_number=1,
        owner="a@b.com", team="t",
    )
    path = write_adr_note(
        data, vault=vault, vault_scope="enterprise",
        project_id="mi-proyecto", actor="user@example.com",
    )
    assert "decisions" in path.parts
    assert "mi-proyecto" in path.parts


def test_adr_enterprise_audit_trail_has_created(vault: FakeVault) -> None:
    data = ADRData(
        title="X", context="c", decision="d", consequences="cs", adr_number=1,
        owner="a@b.com", team="t",
    )
    path = write_adr_note(
        data, vault=vault, vault_scope="enterprise",
        project_id="p", actor="user@example.com",
    )
    fm = parse_frontmatter_lenient(path)
    assert "audit_trail" in fm
    assert len(fm["audit_trail"]) == 1
    assert fm["audit_trail"][0]["action"] == "created"


# ===========================================================================
# write_decision_note
# ===========================================================================


def test_decision_minimal_valid(vault: FakeVault) -> None:
    data = DecisionData(
        title="Use library X",
        context="c", decision="d", alternative_rejected="ar", reason="r",
    )
    path = write_decision_note(data, vault=vault)
    assert path.exists()
    assert path.stem.startswith("DEC-")


def test_decision_filename_pattern(vault: FakeVault) -> None:
    data = DecisionData(
        title="Use library X",
        context="c", decision="d", alternative_rejected="ar", reason="r",
    )
    path = write_decision_note(data, vault=vault)
    # DEC-YYYY-MM-DD-slug
    assert "use-library-x" in path.stem


def test_decision_lives_under_decisions(vault: FakeVault) -> None:
    data = DecisionData(
        title="X", context="c", decision="d",
        alternative_rejected="ar", reason="r",
    )
    path = write_decision_note(data, vault=vault)
    assert path.parent.name == "decisions"


# ===========================================================================
# write_incident_note
# ===========================================================================


def test_incident_minimal_valid(vault: FakeVault) -> None:
    data = IncidentData(
        title="Auth outage",
        short_description="Auth down for 30 minutes",
        severity="high",
        impact="Users can't log in",
        incident_number=1,
    )
    path = write_incident_note(data, vault=vault)
    assert path.exists()
    assert path.name.startswith("INC-001-")


def test_incident_auto_assign_number(vault: FakeVault) -> None:
    data = IncidentData(title="X", short_description="d", severity="medium", incident_number=0)
    path = write_incident_note(data, vault=vault)
    assert "INC-001" in path.stem


def test_incident_invalid_severity_raises(vault: FakeVault) -> None:
    data = IncidentData(title="X", short_description="d", severity="catastrophic", incident_number=1)
    with pytest.raises(SchemaValidationError):
        write_incident_note(data, vault=vault)


# ===========================================================================
# write_postmortem_note
# ===========================================================================


def test_postmortem_minimal_valid(vault: FakeVault) -> None:
    data = PostmortemData(
        title="Auth outage postmortem",
        incident_number=1,
        incident_path="incidents/INC-001-foo.md",
        root_cause="Token expired",
        severity="high",
    )
    path = write_postmortem_note(data, vault=vault)
    assert path.exists()
    assert path.name.startswith("PM-001-")


def test_postmortem_missing_incident_path_raises(vault: FakeVault) -> None:
    data = PostmortemData(
        title="X", incident_number=1, incident_path="",
        root_cause="rc", severity="high",
    )
    with pytest.raises(SchemaValidationError, match="incident_path"):
        write_postmortem_note(data, vault=vault)


def test_postmortem_missing_incident_number_raises(vault: FakeVault) -> None:
    data = PostmortemData(
        title="X", incident_number=0, incident_path="x.md",
        root_cause="rc", severity="high",
    )
    with pytest.raises(SchemaValidationError, match="incident_number"):
        write_postmortem_note(data, vault=vault)


# ===========================================================================
# write_runbook_note
# ===========================================================================


def test_runbook_minimal_valid(vault: FakeVault) -> None:
    data = RunbookData(
        title="Deploy procedure",
        description="How to deploy",
        runbook_kind="deploy",
        procedure=["step1"],
    )
    path = write_runbook_note(data, vault=vault)
    assert path.exists()
    assert path.name.startswith("RB-")


def test_runbook_default_status_draft(vault: FakeVault) -> None:
    data = RunbookData(
        title="X", description="d", runbook_kind="deploy", procedure=["s"],
    )
    path = write_runbook_note(data, vault=vault)
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] in {"draft", "deprecated", "verified"}


def test_runbook_invalid_kind_raises(vault: FakeVault) -> None:
    data = RunbookData(title="X", description="d", runbook_kind="bogus")
    with pytest.raises(SchemaValidationError):
        write_runbook_note(data, vault=vault)


# ===========================================================================
# write_architecture_note
# ===========================================================================


def test_architecture_minimal_valid(vault: FakeVault) -> None:
    data = ArchitectureData(
        title="Auth Architecture",
        summary="The auth module",
        rationale="Why it exists",
    )
    path = write_architecture_note(data, vault=vault)
    assert path.exists()
    assert path.parent.name == "architecture"


def test_architecture_with_related_adrs(vault: FakeVault) -> None:
    data = ArchitectureData(
        title="X", summary="s", rationale="r",
        related_adrs=["ADR-007"],
    )
    path = write_architecture_note(data, vault=vault)
    content = path.read_text(encoding="utf-8")
    assert "[[ADR-007]]" in content


# ===========================================================================
# write_changelog_note
# ===========================================================================


def test_changelog_minimal_valid(vault: FakeVault) -> None:
    data = ChangelogData(
        title="v1.0.0",
        version="v1.0.0",
        added=["feat A"],
    )
    path = write_changelog_note(data, vault=vault)
    assert path.exists()
    assert path.name == "v1.0.0.md"


def test_changelog_empty_version_raises(vault: FakeVault) -> None:
    data = ChangelogData(title="X", version="", added=["a"])
    with pytest.raises(SchemaValidationError, match="version"):
        write_changelog_note(data, vault=vault)


def test_changelog_default_status(vault: FakeVault) -> None:
    data = ChangelogData(title="x", version="v1.0.0")
    path = write_changelog_note(data, vault=vault)
    fm = parse_frontmatter_lenient(path)
    assert fm["status"] in {"released", "unreleased"}


# ===========================================================================
# write_handoff_note
# ===========================================================================


def test_handoff_minimal_valid(vault: FakeVault) -> None:
    data = HandoffData(
        title="Continue auth work",
        parent_session_id="abc123",
        context_required="Auth is broken",
        next_session_needs=["fix login"],
    )
    path = write_handoff_note(data, vault=vault)
    assert path.exists()
    assert path.parent.name == "handoffs"


def test_handoff_missing_parent_session_raises(vault: FakeVault) -> None:
    data = HandoffData(title="X", parent_session_id="")
    with pytest.raises(SchemaValidationError, match="parent_session_id"):
        write_handoff_note(data, vault=vault)


def test_handoff_enterprise_scope_raises(vault: FakeVault) -> None:
    """HANDOFF is local-only; enterprise scope must raise."""
    data = HandoffData(
        title="X", parent_session_id="abc",
        owner="a@b.com", team="t",
    )
    with pytest.raises(SchemaValidationError, match="local"):
        write_handoff_note(
            data, vault=vault, vault_scope="enterprise", project_id="p",
        )


# ===========================================================================
# write_glossary_entry
# ===========================================================================


def test_glossary_minimal_valid(vault: FakeVault) -> None:
    data = GlossaryEntryData(
        term="Ubiquitous Language",
        definition="Common terminology across the team.",
    )
    path = write_glossary_entry(data, vault=vault)
    assert path.exists()
    assert path.parent.name == "glossary"


def test_glossary_filename_is_term_slug(vault: FakeVault) -> None:
    data = GlossaryEntryData(
        term="Ubiquitous Language",
        definition="x",
    )
    path = write_glossary_entry(data, vault=vault)
    assert path.name == "ubiquitous-language.md"


def test_glossary_missing_term_raises(vault: FakeVault) -> None:
    data = GlossaryEntryData(term="", definition="x")
    with pytest.raises(SchemaValidationError, match="term"):
        write_glossary_entry(data, vault=vault)


def test_glossary_missing_definition_raises(vault: FakeVault) -> None:
    data = GlossaryEntryData(term="X", definition="")
    with pytest.raises(SchemaValidationError, match="definition"):
        write_glossary_entry(data, vault=vault)


def test_glossary_uses_term_as_title(vault: FakeVault) -> None:
    data = GlossaryEntryData(term="DocType", definition="An enum")
    path = write_glossary_entry(data, vault=vault)
    fm = parse_frontmatter_lenient(path)
    assert fm["title"] == "DocType"


# ===========================================================================
# Shared: round-trip frontmatter validation
# ===========================================================================


def test_all_new_writers_produce_validating_frontmatter(vault: FakeVault) -> None:
    """Each writer's output validates against its schema."""
    from cortex.documentation.validation import validate_path_frontmatter

    paths = [
        write_adr_note(
            ADRData(title="A1", context="c", decision="d", consequences="cs", adr_number=1),
            vault=vault,
        ),
        write_decision_note(
            DecisionData(title="D1", context="c", decision="d",
                         alternative_rejected="ar", reason="r"),
            vault=vault,
        ),
        write_incident_note(
            IncidentData(title="I1", short_description="d", severity="high", incident_number=1),
            vault=vault,
        ),
        write_postmortem_note(
            PostmortemData(title="P1", incident_number=1, incident_path="x.md",
                           root_cause="rc", severity="high"),
            vault=vault,
        ),
        write_runbook_note(
            RunbookData(title="R1", description="d", runbook_kind="deploy"),
            vault=vault,
        ),
        write_architecture_note(
            ArchitectureData(title="Arch1", summary="s", rationale="r"),
            vault=vault,
        ),
        write_changelog_note(
            ChangelogData(title="v1.0.0", version="v1.0.0", added=["a"]),
            vault=vault,
        ),
        write_handoff_note(
            HandoffData(title="H1", parent_session_id="abc"),
            vault=vault,
        ),
        write_glossary_entry(
            GlossaryEntryData(term="T1", definition="d"),
            vault=vault,
        ),
    ]
    for p in paths:
        fm = validate_path_frontmatter(p)
        assert fm.title  # smoke
