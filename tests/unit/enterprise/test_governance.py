"""Tests for cortex.enterprise.governance (Fase 10)."""

from __future__ import annotations

import pytest

from cortex.enterprise.governance import (
    ADMIN_TEAM,
    GovernancePermissionError,
    allowed_classifications_for,
    assert_can_promote,
    assert_can_review,
    classification_visible_to,
    team_can_promote,
    team_can_review,
    user_team,
)
from cortex.enterprise.models import (
    EnterpriseOrgConfig,
    EnterprisePolicies,
    TeamConfig,
)


@pytest.fixture
def org() -> EnterpriseOrgConfig:
    return EnterpriseOrgConfig(
        teams=[
            TeamConfig(id="api-team", members=["alice@cx.com"], can_promote=True, can_review=True),
            TeamConfig(id="ml-team", members=["bob@cx.com"], can_promote=False),
        ],
        policies=EnterprisePolicies(confidential_visible_to=["api-team"]),
    )


# ---------------------------------------------------------------------------
# user_team
# ---------------------------------------------------------------------------


def test_user_team_resolves_member(org: EnterpriseOrgConfig) -> None:
    assert user_team("alice@cx.com", org) == "api-team"


def test_user_team_unknown_returns_none(org: EnterpriseOrgConfig) -> None:
    assert user_team("eve@external.com", org) is None


def test_user_team_empty_string_returns_none(org: EnterpriseOrgConfig) -> None:
    assert user_team("", org) is None


def test_user_team_none_returns_none(org: EnterpriseOrgConfig) -> None:
    assert user_team(None, org) is None


# ---------------------------------------------------------------------------
# team_can_promote / team_can_review
# ---------------------------------------------------------------------------


def test_team_can_promote_true(org: EnterpriseOrgConfig) -> None:
    assert team_can_promote("api-team", org) is True


def test_team_can_promote_false(org: EnterpriseOrgConfig) -> None:
    assert team_can_promote("ml-team", org) is False


def test_team_can_promote_unknown_team(org: EnterpriseOrgConfig) -> None:
    assert team_can_promote("unknown", org) is False


def test_team_can_promote_admin_always_true(org: EnterpriseOrgConfig) -> None:
    assert team_can_promote(ADMIN_TEAM, org) is True


def test_team_can_promote_permissive_when_no_teams_configured() -> None:
    empty = EnterpriseOrgConfig(teams=[])
    assert team_can_promote(None, empty) is True


def test_team_can_review_true(org: EnterpriseOrgConfig) -> None:
    assert team_can_review("api-team", org) is True


def test_team_can_review_false_for_promotor_without_reviewer_flag(org: EnterpriseOrgConfig) -> None:
    assert team_can_review("ml-team", org) is False


def test_team_can_review_admin_always_true(org: EnterpriseOrgConfig) -> None:
    assert team_can_review(ADMIN_TEAM, org) is True


def test_team_can_review_permissive_when_no_teams_configured() -> None:
    empty = EnterpriseOrgConfig(teams=[])
    assert team_can_review(None, empty) is True


# ---------------------------------------------------------------------------
# classification_visible_to
# ---------------------------------------------------------------------------


def test_public_visible_to_everyone(org: EnterpriseOrgConfig) -> None:
    assert classification_visible_to("public", "api-team", org)
    assert classification_visible_to("public", "ml-team", org)
    assert classification_visible_to("public", None, org)


def test_internal_visible_to_everyone(org: EnterpriseOrgConfig) -> None:
    assert classification_visible_to("internal", "ml-team", org)


def test_confidential_visible_only_to_allowed(org: EnterpriseOrgConfig) -> None:
    assert classification_visible_to("confidential", "api-team", org)
    assert not classification_visible_to("confidential", "ml-team", org)


def test_confidential_admin_sees_everything(org: EnterpriseOrgConfig) -> None:
    assert classification_visible_to("confidential", ADMIN_TEAM, org)


def test_unknown_classification_falls_back_to_confidential_rules(org: EnterpriseOrgConfig) -> None:
    """A non-listed classification behaves like confidential (deny by default)."""
    assert not classification_visible_to("secret", "ml-team", org)
    assert classification_visible_to("secret", "api-team", org)


# ---------------------------------------------------------------------------
# allowed_classifications_for
# ---------------------------------------------------------------------------


def test_allowed_classifications_for_api_team(org: EnterpriseOrgConfig) -> None:
    out = allowed_classifications_for("api-team", org)
    assert "public" in out
    assert "internal" in out
    assert "confidential" in out


def test_allowed_classifications_for_ml_team(org: EnterpriseOrgConfig) -> None:
    out = allowed_classifications_for("ml-team", org)
    assert "confidential" not in out


# ---------------------------------------------------------------------------
# assert helpers
# ---------------------------------------------------------------------------


def test_assert_can_promote_passes_for_authorised(org: EnterpriseOrgConfig) -> None:
    assert assert_can_promote("alice@cx.com", org) == "api-team"


def test_assert_can_promote_raises_for_unauthorised(org: EnterpriseOrgConfig) -> None:
    with pytest.raises(GovernancePermissionError, match="cannot promote"):
        assert_can_promote("bob@cx.com", org)


def test_assert_can_review_passes(org: EnterpriseOrgConfig) -> None:
    assert assert_can_review("alice@cx.com", org) == "api-team"


def test_assert_can_review_raises(org: EnterpriseOrgConfig) -> None:
    with pytest.raises(GovernancePermissionError):
        assert_can_review("bob@cx.com", org)
