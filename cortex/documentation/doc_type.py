"""cortex.documentation.doc_type - DocType enum and helpers.

The ``DocType`` enum is a closed list of 12 canonical document types in
Cortex. Any extension requires an ADR.

This module is the foundation of the canonical documentation system: all
schemas, routing, writers, retrieval filters and webgraph styling reference
``DocType`` values.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

from cortex.documentation.errors import UnknownDocTypeError


class DocType(str, Enum):
    """Canonical document types in Cortex.

    Closed list of 12 values. Inherits from ``str`` so the enum serializes
    directly to YAML/JSON without explicit conversion.
    """

    SESSION = "session"
    HANDOFF = "handoff"
    SPEC = "spec"
    ADR = "adr"
    DECISION = "decision"
    INCIDENT = "incident"
    POSTMORTEM = "postmortem"
    RUNBOOK = "runbook"
    ARCHITECTURE = "architecture"
    CHANGELOG = "changelog"
    HU = "hu"
    GLOSSARY = "glossary"


VALID_STATUSES: dict[DocType, frozenset[str]] = {
    DocType.SESSION: frozenset({
        "draft", "completed", "handoff", "fallback", "auto-draft",
    }),
    DocType.HANDOFF: frozenset({"open", "consumed", "stale"}),
    DocType.SPEC: frozenset({
        "draft", "approved", "implementing", "done", "abandoned",
    }),
    DocType.ADR: frozenset({"proposed", "accepted", "superseded", "rejected"}),
    DocType.DECISION: frozenset({"active", "reverted"}),
    DocType.INCIDENT: frozenset({"open", "mitigated", "closed"}),
    DocType.POSTMORTEM: frozenset({
        "draft", "published", "actions-tracked", "complete",
    }),
    DocType.RUNBOOK: frozenset({"draft", "verified", "deprecated"}),
    DocType.ARCHITECTURE: frozenset({"draft", "current", "deprecated"}),
    DocType.CHANGELOG: frozenset({"unreleased", "released"}),
    DocType.HU: frozenset({"backlog", "in-progress", "done", "cancelled"}),
    DocType.GLOSSARY: frozenset({"draft", "canonical", "deprecated"}),
}


# Doc types that can be promoted from local to enterprise vault.
_PROMOTABLE: frozenset[DocType] = frozenset({
    DocType.SESSION,   # promoted as summary
    DocType.SPEC,
    DocType.ADR,
    DocType.DECISION,
    DocType.INCIDENT,
    DocType.POSTMORTEM,
    DocType.RUNBOOK,
    DocType.ARCHITECTURE,
    DocType.CHANGELOG,
    DocType.GLOSSARY,
})

# Subfolder -> doc_type slug mapping for path inference.
_SUBFOLDER_TO_DOC_TYPE: dict[str, DocType] = {
    "sessions": DocType.SESSION,
    "handoffs": DocType.HANDOFF,
    "specs": DocType.SPEC,
    # 'decisions' resolved by filename below
    "incidents": DocType.INCIDENT,
    "postmortems": DocType.POSTMORTEM,
    "runbooks": DocType.RUNBOOK,
    "architecture": DocType.ARCHITECTURE,
    "changelog": DocType.CHANGELOG,
    "hu": DocType.HU,
    "glossary": DocType.GLOSSARY,
}

_ADR_FILENAME_RE = re.compile(r"^ADR-\d+", re.IGNORECASE)


def doc_type_from_str(value: str) -> DocType:
    """Parse a string to its DocType enum member.

    Raises:
        UnknownDocTypeError if the value is not a valid DocType.
    """
    try:
        return DocType(value)
    except ValueError as exc:
        raise UnknownDocTypeError(f"Unknown doc_type: {value!r}") from exc


def doc_type_from_path(path: Path) -> DocType | None:
    """Infer the DocType from a markdown file's path.

    Rules:
        - ``sessions/<file>``   -> SESSION
        - ``handoffs/<file>``   -> HANDOFF
        - ``specs/<file>``      -> SPEC
        - ``decisions/ADR-*``   -> ADR
        - ``decisions/<other>`` -> DECISION
        - ``incidents/<file>``  -> INCIDENT
        - ``postmortems/<file>``-> POSTMORTEM
        - ``runbooks/<file>``   -> RUNBOOK
        - ``architecture/<file>`` -> ARCHITECTURE
        - ``changelog/<file>``  -> CHANGELOG
        - ``hu/<file>``         -> HU
        - ``glossary/<file>``   -> GLOSSARY
        - anything else         -> None

    Note: this function expects ``path`` to contain a subfolder segment;
    it does not require ``path`` to be relative to a specific vault root.
    """
    parts = path.parts
    if len(parts) < 2:
        return None

    # Find the first segment that matches a known subfolder.
    subfolder: str | None = None
    for part in parts[:-1]:  # exclude filename
        if part in _SUBFOLDER_TO_DOC_TYPE or part == "decisions":
            subfolder = part
            break

    if subfolder is None:
        return None

    if subfolder == "decisions":
        if _ADR_FILENAME_RE.match(path.stem):
            return DocType.ADR
        return DocType.DECISION

    return _SUBFOLDER_TO_DOC_TYPE[subfolder]


def all_doc_types() -> list[DocType]:
    """Return all DocType enum members in declaration order."""
    return list(DocType)


def promotable_doc_types() -> list[DocType]:
    """Return doc types that can be promoted to enterprise vault.

    HANDOFF and HU are not promotable.
    """
    return [dt for dt in DocType if dt in _PROMOTABLE]
