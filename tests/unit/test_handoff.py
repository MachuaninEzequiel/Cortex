"""Tests for cortex.handoff — structured agent handoff schema."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from cortex.handoff import AgentHandoff, ArtifactProduced, is_known_agent


class TestArtifactProduced:
    def test_minimal_artifact(self) -> None:
        art = ArtifactProduced(path="src/x.py", action="modified")
        assert art.lines_changed == 0
        assert art.lines_added == 0

    def test_invalid_action_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ArtifactProduced(path="x.py", action="banana")  # type: ignore[arg-type]


class TestAgentHandoff:
    def test_minimal_handoff_validates(self) -> None:
        h = AgentHandoff(agent="cortex-code-explorer", status="complete")
        assert h.agent == "cortex-code-explorer"
        assert h.status == "complete"
        assert h.verified_claims == []
        assert h.suggested_adr is False

    def test_full_handoff_round_trip(self) -> None:
        original = AgentHandoff(
            agent="cortex-code-implementer",
            status="partial",
            verified_claims=["auth.py modified", "tests added"],
            unverified_claims=["performance impact negligible"],
            artifacts_produced=[
                ArtifactProduced(path="src/auth.py", action="modified", lines_changed=47),
                ArtifactProduced(path="src/middleware.py", action="created", lines_added=89),
            ],
            context_for_next=["documenter: verify TTL hardcoding"],
            suggested_adr=True,
            suggested_adr_reason="TTL hardcoded with UX/security trade-off",
            suggested_context_terms=["JWT refresh window"],
        )

        yaml_text = original.to_yaml()
        roundtripped = AgentHandoff.from_yaml(yaml_text)
        assert roundtripped == original

    def test_invalid_agent_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentHandoff(agent="nonexistent", status="complete")  # type: ignore[arg-type]

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentHandoff(agent="cortex-documenter", status="weird")  # type: ignore[arg-type]

    def test_from_yaml_rejects_non_mapping_root(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            AgentHandoff.from_yaml("- just a list\n- not a mapping")

    def test_from_yaml_rejects_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            AgentHandoff.from_yaml("status: complete\n")  # missing agent

    def test_pi_only_agents_accepted(self) -> None:
        """security-auditor and test-verifier (Pi-only) are valid agent names."""
        h = AgentHandoff(agent="cortex-security-auditor", status="complete")
        assert h.agent == "cortex-security-auditor"
        h2 = AgentHandoff(agent="cortex-test-verifier", status="complete")
        assert h2.agent == "cortex-test-verifier"

    def test_yaml_serialization_uses_unicode(self) -> None:
        h = AgentHandoff(
            agent="cortex-documenter",
            status="complete",
            verified_claims=["TTL hardcodeado en línea 147"],
        )
        yaml_text = h.to_yaml()
        # Unicode characters preserved (not \u escapes)
        assert "línea" in yaml_text


class TestIsKnownAgent:
    def test_canonical_names(self) -> None:
        assert is_known_agent("cortex-sync") is True
        assert is_known_agent("cortex-documenter") is True
        assert is_known_agent("cortex-security-auditor") is True

    def test_unknown_name(self) -> None:
        assert is_known_agent("cortex-random") is False
        assert is_known_agent("") is False
