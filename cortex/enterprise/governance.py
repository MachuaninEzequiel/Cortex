"""cortex.enterprise.governance - Multi-tenant permissions and visibility.

Resolves *who can do what* and *who can see what* inside an enterprise
deployment, based on the ``teams`` / ``classifications`` / ``policies``
sections of ``org.yaml``.

The module is intentionally pure: it does not read filesystem, does not
import the writer or retrieval layers. It only reasons over the
``EnterpriseOrgConfig`` instance the caller already loaded.

Usage::

    org = EnterpriseOrgConfig.model_validate(yaml.safe_load(...))
    team_id = user_team("alice@cortex.ai", org)
    if not team_can_promote(team_id, org):
        raise PermissionError(...)
"""

from __future__ import annotations

from typing import Iterable

from cortex.enterprise.models import EnterpriseOrgConfig

# Built-in pseudo-team that gets access to everything.
ADMIN_TEAM = "admin"


class GovernancePermissionError(PermissionError):
    """Raised when a governance check denies an action."""


# ---------------------------------------------------------------------------
# Team resolution
# ---------------------------------------------------------------------------


def user_team(actor: str | None, org: EnterpriseOrgConfig) -> str | None:
    """Resolve which team ``actor`` belongs to.

    Returns the team id, the ``ADMIN_TEAM`` sentinel if no team matches but
    actor is the admin, or ``None`` if actor is unknown.
    """
    if not actor:
        return None
    for team in org.teams:
        if actor in team.members:
            return team.id
    return None


def team_can_promote(team_id: str | None, org: EnterpriseOrgConfig) -> bool:
    """``True`` if the team is allowed to promote knowledge."""
    if team_id == ADMIN_TEAM:
        return True
    if team_id is None:
        # No teams configured at all -> permissive (back-compat).
        return not org.teams
    for team in org.teams:
        if team.id == team_id:
            return team.can_promote
    return False


def team_can_review(team_id: str | None, org: EnterpriseOrgConfig) -> bool:
    """``True`` if the team can approve/reject pending promotions."""
    if team_id == ADMIN_TEAM:
        return True
    if team_id is None:
        return not org.teams
    for team in org.teams:
        if team.id == team_id:
            return team.can_review
    return False


# ---------------------------------------------------------------------------
# Classification visibility
# ---------------------------------------------------------------------------


def classification_visible_to(
    classification: str,
    team_id: str | None,
    org: EnterpriseOrgConfig,
) -> bool:
    """Return ``True`` if ``team_id`` can see notes with the given classification.

    Rules:
        - ``public`` and ``internal`` are visible to everyone.
        - ``confidential`` is visible only to teams listed in
          ``policies.confidential_visible_to`` or to the ``ADMIN_TEAM``.
        - Unknown classifications behave like ``confidential``.
    """
    if classification in {"public", "internal"}:
        return True
    # confidential / unknown:
    if team_id == ADMIN_TEAM:
        return True
    if not team_id:
        return False
    allowed = org.policies.confidential_visible_to or []
    return team_id in allowed


# ---------------------------------------------------------------------------
# Filter helpers (consumed by retrieval to scope multi-tenant search)
# ---------------------------------------------------------------------------


def allowed_classifications_for(
    team_id: str | None, org: EnterpriseOrgConfig,
) -> list[str]:
    """Return the list of classifications a team is allowed to see."""
    return [
        c for c in org.classifications
        if classification_visible_to(c, team_id, org)
    ]


def assert_can_promote(actor: str, org: EnterpriseOrgConfig) -> str:
    """Validate that ``actor`` can promote; return the resolved team id.

    Raises ``GovernancePermissionError`` otherwise.
    """
    team_id = user_team(actor, org)
    if not team_can_promote(team_id, org):
        raise GovernancePermissionError(
            f"actor {actor!r} (team={team_id!r}) cannot promote"
        )
    return team_id or ""


def assert_can_review(actor: str, org: EnterpriseOrgConfig) -> str:
    """Validate that ``actor`` can review; return the resolved team id."""
    team_id = user_team(actor, org)
    if not team_can_review(team_id, org):
        raise GovernancePermissionError(
            f"actor {actor!r} (team={team_id!r}) cannot review"
        )
    return team_id or ""


__all__ = [
    "ADMIN_TEAM",
    "GovernancePermissionError",
    "allowed_classifications_for",
    "assert_can_promote",
    "assert_can_review",
    "classification_visible_to",
    "team_can_promote",
    "team_can_review",
    "user_team",
]
