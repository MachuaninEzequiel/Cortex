"""
cortex.doc_validator
--------------------
Validates agent-generated documentation in the vault.

Checks:
- Valid YAML frontmatter (``---`` delimiters)
- Required properties present (``title``, ``tags`` or ``date``)
- Wikilinks syntax (``[[note]]``)
- No broken embeds (``![[note]]`` referencing non-existent files)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DocValidationIssue:
    """A single validation problem."""

    file: str
    field: str
    message: str
    severity: str = "warning"  # "error" | "warning" | "info"


@dataclass
class DocValidationResult:
    """Result of validating a single document or a batch."""

    is_valid: bool = True
    issues: list[DocValidationIssue] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    wikilinks: list[str] = field(default_factory=list)
    embeds: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[DocValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[DocValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "properties": self.properties,
            "wikilinks": self.wikilinks,
            "embeds": self.embeds,
            "issues": [
                {"file": i.file, "field": i.field, "message": i.message, "severity": i.severity}
                for i in self.issues
            ],
        }


# Regex for Obsidian wikilinks and embeds
_WIKILINK_RE = re.compile(r"!\?\[\[([^\]]+)\]\]")
_EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class DocValidator:
    """
    Validates agent-generated markdown docs in the vault.

    Parameters
    ----------
    vault_path : str | Path
        Path to the vault directory. Used to resolve wikilink targets.
    """

    def __init__(self, vault_path: str | Path):
        self.vault_path = Path(vault_path)

    def validate_file(self, filepath: str | Path) -> DocValidationResult:
        """Validate a single markdown file."""
        path = Path(filepath)
        result = DocValidationResult()
        result.issues = []

        if not path.exists():
            result.is_valid = False
            result.issues.append(DocValidationIssue(
                file=str(path),
                field="file",
                message="File does not exist",
                severity="error",
            ))
            return result

        if not str(path).endswith(".md"):
            result.issues.append(DocValidationIssue(
                file=str(path),
                field="file",
                message="Not a markdown file",
                severity="warning",
            ))
            return result

        content = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(self.vault_path)) if str(path).startswith(str(self.vault_path)) else str(path)

        # Check frontmatter
        self._parse_frontmatter(content, rel, result)

        # Extract wikilinks
        result.wikilinks = self._extract_wikilinks(content)

        # Extract embeds
        result.embeds = self._extract_embeds(content)

        # Check for broken embeds
        self._check_embeds(result, rel)

        # Final validity
        result.is_valid = len(result.errors) == 0
        return result

    def validate_batch(self, filepaths: list[str | Path]) -> list[DocValidationResult]:
        """Validate multiple files."""
        return [self.validate_file(fp) for fp in filepaths]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_frontmatter(
        self, content: str, rel_path: str, result: DocValidationResult
    ) -> dict | None:
        """Parse and validate YAML frontmatter."""
        m = _FRONTMATTER_RE.match(content)
        if not m:
            result.issues.append(DocValidationIssue(
                file=rel_path,
                field="frontmatter",
                message="No YAML frontmatter found (expected --- delimiters)",
                severity="warning",
            ))
            return None

        try:
            fm: dict = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as exc:
            result.issues.append(DocValidationIssue(
                file=rel_path,
                field="frontmatter",
                message=f"Invalid YAML: {exc}",
                severity="error",
            ))
            return None

        result.properties = fm

        # Required: title
        if not fm.get("title"):
            result.issues.append(DocValidationIssue(
                file=rel_path,
                field="title",
                message="Missing 'title' property in frontmatter",
                severity="warning",
            ))

        # Required: date or created
        if not (fm.get("date") or fm.get("created")):
            result.issues.append(DocValidationIssue(
                file=rel_path,
                field="date",
                message="Missing 'date' or 'created' property in frontmatter",
                severity="info",
            ))

        return fm

    def _extract_wikilinks(self, content: str) -> list[str]:
        """Extract all wikilinks (non-embed) from content."""
        # Remove embeds first to avoid false positives
        clean = _EMBED_RE.sub("", content)
        links = re.findall(r"\[\[([^\]]+)\]\]", clean)
        # Clean up: remove display text part
        return [link.split("|")[0].split("#")[0].split("^")[0].strip() for link in links]

    def _extract_embeds(self, content: str) -> list[str]:
        """Extract all embeds from content."""
        return [m.split("|")[0].split("#")[0].split("^")[0].strip() for m in _EMBED_RE.findall(content)]

    def _check_embeds(self, result: DocValidationResult, current_file: str) -> None:
        """Check that embed targets exist."""
        for embed in result.embeds:
            target = self.vault_path / embed
            # Try with and without .md extension
            if not target.exists() and not target.with_suffix(".md").exists():
                result.issues.append(DocValidationIssue(
                    file=current_file,
                    field="embed",
                    message=f"Embed target not found: {embed}",
                    severity="warning",
                ))
