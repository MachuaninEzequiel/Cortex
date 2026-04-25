"""
cortex.documentation
--------------------
Helpers for writing durable Cortex documentation artifacts into the vault.

This module powers the new Release 2 workflow:
- specs generated before execution
- session notes written as part of the "done" protocol
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from cortex.workitems.models import TrackedItem


def _slugify(value: str) -> str:
    """Convert free text into a filesystem-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", value.strip().lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or "untitled"


def _render_list(items: list[str], *, bullet: str = "-") -> str:
    clean = [item.strip() for item in items if item and item.strip()]
    if not clean:
        return f"{bullet} (none)"
    return "\n".join(f"{bullet} {item}" for item in clean)


def _frontmatter(*, title: str, today: date, tags: list[str], status: str) -> str:
    tag_text = ", ".join(dict.fromkeys(tags))
    return (
        "---\n"
        f'title: "{title}"\n'
        f"date: {today.isoformat()}\n"
        f"tags: [{tag_text}]\n"
        f"status: {status}\n"
        "---\n\n"
    )


def _frontmatter_with_fields(
    *,
    title: str,
    today: date,
    tags: list[str],
    status: str,
    extra_fields: list[tuple[str, str]] | None = None,
) -> str:
    tag_text = ", ".join(dict.fromkeys(tags))
    lines = [
        "---",
        f'title: "{title}"',
        f"date: {today.isoformat()}",
        f"tags: [{tag_text}]",
        f"status: {status}",
    ]
    for key, value in extra_fields or []:
        lines.append(f"{key}: {value}")
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def write_session_note(
    vault_path: str | Path,
    *,
    title: str,
    spec_summary: str,
    changes_made: list[str] | None = None,
    files_touched: list[str] | None = None,
    key_decisions: list[str] | None = None,
    next_steps: list[str] | None = None,
    tags: list[str] | None = None,
    note_date: date | None = None,
) -> Path:
    """
    Write a session note to ``vault/sessions/`` and return the file path.
    """
    today = note_date or date.today()
    vault = Path(vault_path)
    target_dir = vault / "sessions"
    target_dir.mkdir(parents=True, exist_ok=True)

    final_tags = ["session", "release-2"] + list(tags or [])
    filename = f"{today.isoformat()}_{_slugify(title)}.md"
    path = target_dir / filename

    content = _frontmatter(
        title=title,
        today=today,
        tags=final_tags,
        status="generated",
    )
    content += f"# Session: {title}\n\n"
    content += "## Original Specification\n"
    content += (spec_summary.strip() or "No specification summary was provided.") + "\n\n"
    content += "## Changes Made\n"
    content += _render_list(list(changes_made or [])) + "\n\n"
    content += "## Files Touched\n"
    content += _render_list(list(files_touched or [])) + "\n\n"
    content += "## Key Decisions\n"
    content += _render_list(list(key_decisions or [])) + "\n\n"
    content += "## Next Steps\n"
    content += _render_list(list(next_steps or []), bullet="- [ ]") + "\n"

    path.write_text(content, encoding="utf-8")
    return path


def write_spec_note(
    vault_path: str | Path,
    *,
    title: str,
    goal: str,
    requirements: list[str] | None = None,
    files_in_scope: list[str] | None = None,
    constraints: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    tags: list[str] | None = None,
    note_date: date | None = None,
) -> Path:
    """
    Write an implementation specification to ``vault/specs/``.
    """
    today = note_date or date.today()
    vault = Path(vault_path)
    target_dir = vault / "specs"
    target_dir.mkdir(parents=True, exist_ok=True)

    final_tags = ["spec", "release-2"] + list(tags or [])
    filename = f"{today.isoformat()}_{_slugify(title)}.md"
    path = target_dir / filename

    content = _frontmatter(
        title=title,
        today=today,
        tags=final_tags,
        status="draft",
    )
    content += f"# Specification: {title}\n\n"
    content += "## Goal\n"
    content += (goal.strip() or "No goal was provided.") + "\n\n"
    content += "## Requirements\n"
    content += _render_list(list(requirements or [])) + "\n\n"
    content += "## Files in Scope\n"
    content += _render_list(list(files_in_scope or [])) + "\n\n"
    content += "## Constraints\n"
    content += _render_list(list(constraints or [])) + "\n\n"
    content += "## Acceptance Criteria\n"
    content += _render_list(list(acceptance_criteria or [])) + "\n"

    path.write_text(content, encoding="utf-8")
    return path


def write_tracked_item_note(
    vault_path: str | Path,
    *,
    item: TrackedItem,
    note_date: date | None = None,
) -> Path:
    """Write a tracked item note to ``vault/hu/`` and return the file path."""
    today = note_date or date.today()
    vault = Path(vault_path)
    target_dir = vault / "hu"
    target_dir.mkdir(parents=True, exist_ok=True)

    title = f"{item.id}: {item.title}"
    final_tags = ["hu", item.source.value, item.kind.value] + list(item.labels)
    filename = f"{_slugify(item.id)}.md"
    path = target_dir / filename

    extra_fields = [
        ("external_id", f'"{item.external_id}"'),
        ("source", item.source.value),
        ("kind", item.kind.value),
        ("synced", item.sync_timestamp.date().isoformat()),
    ]
    if item.assignee:
        extra_fields.append(("assignee", f'"{item.assignee}"'))
    if item.external_url:
        extra_fields.append(("external_url", f'"{item.external_url}"'))

    content = _frontmatter_with_fields(
        title=title,
        today=today,
        tags=final_tags,
        status=item.status or "imported",
        extra_fields=extra_fields,
    )
    content += f"# {title}\n\n"
    content += "## Description\n"
    content += (item.description.strip() or "No description was provided.") + "\n\n"
    content += "## Acceptance Criteria\n"
    content += _render_list(item.acceptance_criteria) + "\n\n"
    content += "## Metadata\n"
    metadata_lines = [
        f"- Source: {item.source.value}",
        f"- Kind: {item.kind.value}",
        f"- Status: {item.status or 'unknown'}",
    ]
    if item.assignee:
        metadata_lines.append(f"- Assignee: {item.assignee}")
    if item.external_url:
        metadata_lines.append(f"- External: {item.external_url}")
    content += "\n".join(metadata_lines) + "\n"

    path.write_text(content, encoding="utf-8")
    return path
