"""cortex.documentation.inventory - Scan the vault to produce a diagnostic snapshot.

Used by migration tooling (Fase 11) and by ``cortex docs status`` reports.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from cortex.documentation.common import parse_frontmatter_lenient


# Map of subfolder name -> inferred doc_type slug.
# Lives here (string-valued) so this module can be imported without the
# ``doc_type`` module (which is introduced in Fase 01).
_SUBFOLDER_TO_DOC_TYPE: dict[str, str] = {
    "sessions": "session",
    "handoffs": "handoff",
    "specs": "spec",
    "decisions": "decision",  # ADR override happens below by filename pattern
    "incidents": "incident",
    "postmortems": "postmortem",
    "runbooks": "runbook",
    "architecture": "architecture",
    "changelog": "changelog",
    "hu": "hu",
    "glossary": "glossary",
}

_ADR_FILENAME_RE = re.compile(r"^ADR-\d+", re.IGNORECASE)


@dataclass
class VaultInventory:
    """Snapshot of a vault's current state.

    Used to power migration planning and the ``cortex docs status`` report.
    """

    total_files: int = 0
    by_subfolder: dict[str, int] = field(default_factory=dict)
    with_frontmatter: int = 0
    without_frontmatter: int = 0
    with_schema_version_1: int = 0
    classifiable: int = 0
    unclassifiable: list[str] = field(default_factory=list)
    legacy_frontmatter_keys: dict[str, int] = field(default_factory=dict)


def classify_path(path: Path, vault_root: Path) -> str | None:
    """Infer a doc_type slug from a markdown file's location in the vault.

    Returns the slug as a string (not a DocType enum, to keep this module
    independent of Fase 01).

    Rules:
        - ``vault_root/sessions/<file>``  -> ``"session"``
        - ``vault_root/decisions/ADR-*``  -> ``"adr"``
        - ``vault_root/decisions/<other>`` -> ``"decision"``
        - ``vault_root/<known-subfolder>/<file>`` -> mapped via table
        - Anything else                   -> ``None``
    """
    try:
        rel = path.resolve().relative_to(vault_root.resolve())
    except ValueError:
        return None

    parts = rel.parts
    if len(parts) < 2:
        # File directly in vault root; not classifiable by subfolder.
        return None

    subfolder = parts[0]
    if subfolder not in _SUBFOLDER_TO_DOC_TYPE:
        return None

    # Special case: ADR vs DECISION inside ``decisions/``.
    if subfolder == "decisions":
        if _ADR_FILENAME_RE.match(path.stem):
            return "adr"
        return "decision"

    return _SUBFOLDER_TO_DOC_TYPE[subfolder]


def inventory_vault(vault_path: Path) -> VaultInventory:
    """Scan a vault directory and produce a ``VaultInventory``.

    Walks ``vault_path`` recursively, classifies each ``.md`` file, and
    aggregates frontmatter key usage. Does not modify any file.
    """
    inventory = VaultInventory()

    if not vault_path.exists() or not vault_path.is_dir():
        return inventory

    per_subfolder: Counter[str] = Counter()
    legacy_keys: Counter[str] = Counter()

    for md_path in sorted(vault_path.rglob("*.md")):
        inventory.total_files += 1

        # Classify subfolder.
        try:
            rel = md_path.resolve().relative_to(vault_path.resolve())
        except ValueError:
            continue
        if len(rel.parts) >= 2:
            per_subfolder[rel.parts[0]] += 1
        else:
            per_subfolder["<root>"] += 1

        # Frontmatter analysis.
        fm = parse_frontmatter_lenient(md_path)
        if fm:
            inventory.with_frontmatter += 1
            if fm.get("schema_version") == 1:
                inventory.with_schema_version_1 += 1
            for key in fm:
                legacy_keys[key] += 1
        else:
            inventory.without_frontmatter += 1

        # Classification.
        if classify_path(md_path, vault_path) is not None:
            inventory.classifiable += 1
        else:
            inventory.unclassifiable.append(str(rel))

    inventory.by_subfolder = dict(per_subfolder)
    inventory.legacy_frontmatter_keys = dict(legacy_keys)
    return inventory
