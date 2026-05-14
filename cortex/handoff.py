"""cortex.handoff — Structured agent handoff schema.

Replaces prose handoffs between subagents with verifiable YAML contracts.
Validated by the ``cortex_validate_handoff`` MCP tool (Plan 02 §1).

The schema is intentionally permissive on optional fields and strict on the
two anchors (``agent`` and ``status``) so that a downstream consumer can
always identify the producing agent and its completion state without
parsing prose.

Usage::

    handoff = AgentHandoff(
        agent="cortex-code-implementer",
        status="complete",
        verified_claims=["auth.py refactored to JWT"],
        artifacts_produced=[
            ArtifactProduced(path="src/auth.py", action="modified", lines_changed=47),
        ],
    )
    yaml_text = handoff.to_yaml()
    # Send yaml_text downstream. The next agent calls:
    parsed = AgentHandoff.from_yaml(yaml_text)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ArtifactProduced(BaseModel):
    """A single file produced or touched by an agent during its run."""

    path: str
    action: Literal["created", "modified", "deleted", "renamed"]
    lines_changed: int = 0
    lines_added: int = 0


# ---------------------------------------------------------------------------
# AgentHandoff
# ---------------------------------------------------------------------------


_KNOWN_AGENTS = {
    "cortex-sync",
    "cortex-SDDwork",
    "cortex-code-explorer",
    "cortex-code-implementer",
    "cortex-documenter",
    # Pi-only agents (allowed because they participate in agent-chain.yaml)
    "cortex-security-auditor",
    "cortex-test-verifier",
}


class AgentHandoff(BaseModel):
    """Structured handoff produced by every subagent at completion.

    Every Cortex subagent (sync, SDDwork, explorer, implementer, documenter,
    plus the Pi-only security-auditor and test-verifier) must emit one of
    these objects as its final message. The orchestrator passes it to the
    next agent in the chain unchanged.

    Validation rules:
    - ``agent`` must be one of the known canonical names.
    - ``status`` must be ``complete | partial | blocked``.
    - ``artifacts_produced[].action`` must be ``created | modified | deleted | renamed``.
    - Other lists default to empty (it is valid for an agent to produce
      a handoff with no verified claims if it merely read).
    """

    agent: Literal[
        "cortex-sync",
        "cortex-SDDwork",
        "cortex-code-explorer",
        "cortex-code-implementer",
        "cortex-documenter",
        "cortex-security-auditor",
        "cortex-test-verifier",
    ]
    status: Literal["complete", "partial", "blocked"]
    verified_claims: list[str] = Field(default_factory=list)
    unverified_claims: list[str] = Field(default_factory=list)
    artifacts_produced: list[ArtifactProduced] = Field(default_factory=list)
    context_for_next: list[str] = Field(default_factory=list)
    suggested_adr: bool = False
    suggested_adr_reason: str = ""
    suggested_context_terms: list[str] = Field(default_factory=list)

    def to_yaml(self) -> str:
        """Serialize the handoff to a YAML string (stable key order)."""
        import yaml

        return yaml.safe_dump(
            self.model_dump(mode="json"),
            sort_keys=False,
            allow_unicode=True,
        )

    @classmethod
    def from_yaml(cls, text: str) -> "AgentHandoff":
        """Parse and validate a YAML handoff.

        Raises ``pydantic.ValidationError`` if the schema is violated,
        or ``yaml.YAMLError`` on malformed YAML.
        """
        import yaml

        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise ValueError("Handoff YAML must be a mapping at the root")
        return cls.model_validate(data)


def is_known_agent(name: str) -> bool:
    """Return True when *name* matches one of the canonical agent names."""
    return name in _KNOWN_AGENTS
