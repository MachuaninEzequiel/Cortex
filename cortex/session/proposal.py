"""cortex.session.proposal — Interactive proposal primitive (Phase 09.A+).

Models the artifact emitted by ``cortex-sync`` (and any future skill that
needs explicit user confirmation) when ``proposal_mode`` is ``optional``
or ``required``. The proposal is rendered as a Markdown "card" that the
MCP client surfaces to the user as a structured tool result, **forcing**
visual emphasis that a plain assistant message cannot guarantee.

Why this exists
---------------
Phase 09.A originally instructed the agent to emit the proposal as a
plain Markdown message and pause its turn. In practice that was fragile:
the LLM may forget to stop, the IDE may collapse the message under the
last MCP indicator, and there is no server-side audit trail.

By forcing the agent to call ``cortex_emit_proposal``, the proposal:
    * Is rendered consistently across IDEs (the tool result IS the card).
    * Is logged in ``mcp_calls_<timestamp>.log`` for audit.
    * Anchors the timestamp used to enforce the
      ``required`` → ``cortex_create_spec`` gate (see
      :class:`cortex.mcp.server.CortexMCPServer._create_spec_text`).

Model contract
--------------
- Exactly one alternative is the *recommendation*; the rest carry a
  ``rejected_reason`` explaining why they were not chosen.
- Alternative ids are short tokens (``A``, ``B``, ``C``…) so the user
  can reference them in plain language.
- ``risks`` is optional but encouraged — it surfaces the assumptions the
  user is implicitly accepting by saying ``ok``.

This module is **pure**: it does not touch the filesystem, MCP server, or
any session storage. Persistence (if ever needed) lives elsewhere; see
``docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md`` §12.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Short alternative ids: a single uppercase letter or a digit, optionally
# followed by more letters/digits. Keeps user-facing references simple
# ("voy con B", "prefiero la C") without forcing UUIDs.
ALTERNATIVE_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,15}$")


class Alternative(BaseModel):
    """One option presented to the user inside a :class:`Proposal`.

    Exactly one alternative per proposal has ``rejected_reason`` blank
    (the recommendation). Every other alternative carries a non-empty
    ``rejected_reason``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=16)
    # 1500-char ceiling lets agents describe alternatives with risks,
    # constraints and tradeoffs without truncating. The previous 500-char
    # cap rejected legitimate detailed alternatives (see incident
    # docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/, Fase 2
    # proposal rejected at the third alternative).
    description: str = Field(min_length=1, max_length=1500)
    rejected_reason: str = Field(default="", max_length=1500)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not ALTERNATIVE_ID_PATTERN.match(v):
            raise ValueError(
                f"Alternative id {v!r} must match {ALTERNATIVE_ID_PATTERN.pattern}"
            )
        return v


class Proposal(BaseModel):
    """A structured proposal awaiting user confirmation.

    Args:
        summary:           One-paragraph executive summary (2-3 lines).
        alternatives:      Between 2 and 5 distinct options.
        recommendation_id: Id of the chosen alternative; must appear in
                           ``alternatives`` and that entry must have an
                           empty ``rejected_reason``.
        risks:             Optional list of risks/assumptions the user
                           is implicitly accepting.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1, max_length=1000)
    alternatives: list[Alternative] = Field(min_length=2, max_length=5)
    recommendation_id: str = Field(min_length=1, max_length=16)
    risks: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("risks")
    @classmethod
    def _strip_empty_risks(cls, v: list[str]) -> list[str]:
        cleaned = [r.strip() for r in v if r and r.strip()]
        if any(len(r) > 300 for r in cleaned):
            raise ValueError("Each risk must be <= 300 characters.")
        return cleaned

    @model_validator(mode="after")
    def _validate_recommendation(self) -> Proposal:
        ids = [a.id for a in self.alternatives]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(
                f"Alternative ids must be unique; duplicates: {duplicates}"
            )
        if self.recommendation_id not in ids:
            raise ValueError(
                f"recommendation_id {self.recommendation_id!r} does not match "
                f"any alternative id (have: {ids})"
            )
        chosen = next(a for a in self.alternatives if a.id == self.recommendation_id)
        if chosen.rejected_reason.strip():
            raise ValueError(
                f"The recommended alternative ({chosen.id!r}) must have an "
                f"empty rejected_reason; got: {chosen.rejected_reason!r}"
            )
        for alt in self.alternatives:
            if alt.id == self.recommendation_id:
                continue
            if not alt.rejected_reason.strip():
                raise ValueError(
                    f"Non-recommended alternative {alt.id!r} must include a "
                    f"non-empty rejected_reason."
                )
        return self


def format_proposal_card(proposal: Proposal) -> str:
    """Render *proposal* as a Markdown card suitable for an MCP tool result.

    The card uses a fixed header so MCP clients (Claude Code, opencode,
    Cursor) can identify it visually and avoid collapsing it under the
    generic "tool result" affordance.
    """
    lines: list[str] = [
        "### 🎯 PROPUESTA — necesito tu confirmación",
        "",
        "**Resumen:**",
        proposal.summary.strip(),
        "",
        "**Alternativas consideradas:**",
    ]
    for alt in proposal.alternatives:
        marker = "✅" if alt.id == proposal.recommendation_id else "❌"
        lines.append(f"- {marker} **[{alt.id}]** {alt.description.strip()}")
        if alt.id == proposal.recommendation_id:
            lines.append("    - *(esta es la que recomiendo)*")
        else:
            lines.append(f"    - Descartada porque: {alt.rejected_reason.strip()}")

    if proposal.risks:
        lines.extend(["", "**Riesgos / supuestos:**"])
        lines.extend(f"- {r}" for r in proposal.risks)

    lines.extend(
        [
            "",
            "---",
            (
                f"⏸ **Esperando confirmación.** Respondé `ok` (o silencio) "
                f"para proceder con **[{proposal.recommendation_id}]**, "
                "o indicame qué cambiar / cuál elegís en su lugar."
            ),
        ]
    )
    return "\n".join(lines)


__all__ = [
    "ALTERNATIVE_ID_PATTERN",
    "Alternative",
    "Proposal",
    "format_proposal_card",
]
