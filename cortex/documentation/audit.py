"""cortex.documentation.audit - Helpers for enterprise audit_trail.

The ``audit_trail`` field on ``EnterpriseFrontmatter`` is append-only. This
module provides the canonical way to add entries.
"""

from __future__ import annotations

from datetime import UTC, datetime

from cortex.documentation.schemas import AuditEvent, EnterpriseFrontmatter


def append_audit_event(
    frontmatter: EnterpriseFrontmatter,
    actor: str,
    action: str,
    reason: str | None = None,
) -> EnterpriseFrontmatter:
    """Return a NEW ``EnterpriseFrontmatter`` with one extra audit event.

    The trail is append-only; existing events are preserved.

    Args:
        frontmatter: existing enterprise frontmatter (frozen).
        actor: who performed the action (email or agent-id).
        action: short action verb ("created", "updated", "promoted", ...).
        reason: optional free-form rationale.

    Returns:
        A new validated EnterpriseFrontmatter instance with the appended event.
    """
    new_event = AuditEvent(
        actor=actor,
        action=action,
        timestamp=datetime.now(UTC),
        reason=reason,
    )
    updated = frontmatter.model_dump(mode="python")
    existing_trail = list(updated.get("audit_trail", []))
    existing_trail.append(new_event.model_dump(mode="python"))
    updated["audit_trail"] = existing_trail
    # Re-validate against the same class.
    return type(frontmatter).model_validate(updated)
