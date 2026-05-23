"""Tests para cortex.session.proposal (Pluggable Middle Phase 09.A+).

Garantiza:
    * Validacion estructural del modelo ``Proposal`` (alternativas unicas,
      recommendation_id valido, recommended sin rejected_reason, etc.).
    * El renderer ``format_proposal_card`` produce el header esperado, las
      lineas con marcadores ✅/❌, los riesgos cuando hay, y la senal
      explicita de "Esperando confirmacion" al final.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from cortex.session.proposal import (
    ALTERNATIVE_ID_PATTERN,
    Alternative,
    Proposal,
    format_proposal_card,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proposal(**overrides) -> Proposal:
    base = {
        "summary": "Refactor login flow into a stateful service",
        "alternatives": [
            {
                "id": "A",
                "description": "Inline rewrite of LoginController",
                "rejected_reason": "Couples auth state to the view layer.",
            },
            {
                "id": "B",
                "description": "Extract AuthService singleton",
                "rejected_reason": "",
            },
            {
                "id": "C",
                "description": "Full OAuth migration",
                "rejected_reason": "Too large for this iteration.",
            },
        ],
        "recommendation_id": "B",
        "risks": ["Touches session middleware", "Requires migration of tests"],
    }
    base.update(overrides)
    return Proposal.model_validate(base)


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


def test_proposal_valid_minimal():
    p = _make_proposal()
    assert p.recommendation_id == "B"
    assert len(p.alternatives) == 3
    assert p.risks == ["Touches session middleware", "Requires migration of tests"]


def test_alternative_id_pattern():
    assert ALTERNATIVE_ID_PATTERN.match("A")
    assert ALTERNATIVE_ID_PATTERN.match("OPT_1")
    assert ALTERNATIVE_ID_PATTERN.match("B2")
    assert not ALTERNATIVE_ID_PATTERN.match("lowercase")
    assert not ALTERNATIVE_ID_PATTERN.match("with spaces")
    assert not ALTERNATIVE_ID_PATTERN.match("")


def test_alternative_id_lowercase_rejected():
    with pytest.raises(ValidationError) as exc:
        Alternative(id="a", description="desc", rejected_reason="")
    assert "Alternative id" in str(exc.value)


def test_proposal_minimum_two_alternatives():
    with pytest.raises(ValidationError):
        _make_proposal(
            alternatives=[
                {"id": "A", "description": "only one", "rejected_reason": ""},
            ],
            recommendation_id="A",
        )


def test_proposal_maximum_five_alternatives():
    too_many = [
        {"id": chr(65 + i), "description": f"opt {i}", "rejected_reason": "x"}
        for i in range(6)
    ]
    too_many[0]["rejected_reason"] = ""
    with pytest.raises(ValidationError):
        _make_proposal(alternatives=too_many, recommendation_id="A")


def test_proposal_unique_alternative_ids():
    with pytest.raises(ValidationError) as exc:
        _make_proposal(
            alternatives=[
                {"id": "A", "description": "x", "rejected_reason": ""},
                {"id": "A", "description": "y", "rejected_reason": "dup"},
            ],
            recommendation_id="A",
        )
    assert "unique" in str(exc.value).lower()


def test_proposal_recommendation_must_exist():
    with pytest.raises(ValidationError) as exc:
        _make_proposal(recommendation_id="Z")
    assert "does not match" in str(exc.value)


def test_proposal_recommended_must_have_empty_rejection():
    with pytest.raises(ValidationError) as exc:
        _make_proposal(
            alternatives=[
                {"id": "A", "description": "x", "rejected_reason": "should be empty"},
                {"id": "B", "description": "y", "rejected_reason": "discarded"},
            ],
            recommendation_id="A",
        )
    assert "empty rejected_reason" in str(exc.value)


def test_proposal_non_recommended_must_have_non_empty_rejection():
    with pytest.raises(ValidationError) as exc:
        _make_proposal(
            alternatives=[
                {"id": "A", "description": "x", "rejected_reason": ""},
                {"id": "B", "description": "y", "rejected_reason": "   "},  # whitespace only
            ],
            recommendation_id="A",
        )
    assert "non-empty rejected_reason" in str(exc.value)


def test_proposal_risks_stripped_and_filtered():
    p = _make_proposal(risks=["  risk one  ", "", "   ", "risk two"])
    assert p.risks == ["risk one", "risk two"]


def test_proposal_summary_required():
    with pytest.raises(ValidationError):
        _make_proposal(summary="")


def test_proposal_is_immutable():
    p = _make_proposal()
    with pytest.raises(ValidationError):
        p.summary = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def test_format_proposal_card_header_and_recommendation_marker():
    card = format_proposal_card(_make_proposal())
    assert "🎯 PROPUESTA" in card
    assert "necesito tu confirmación" in card
    # The recommended option (B) must carry the ✅ marker; the others ❌.
    assert "✅ **[B]**" in card
    assert "❌ **[A]**" in card
    assert "❌ **[C]**" in card


def test_format_proposal_card_includes_summary_and_alternatives():
    card = format_proposal_card(_make_proposal())
    assert "Refactor login flow into a stateful service" in card
    assert "Extract AuthService singleton" in card
    assert "Descartada porque: Couples auth state to the view layer." in card


def test_format_proposal_card_includes_risks_when_present():
    card = format_proposal_card(_make_proposal())
    assert "**Riesgos / supuestos:**" in card
    assert "- Touches session middleware" in card


def test_format_proposal_card_omits_risks_section_when_empty():
    card = format_proposal_card(_make_proposal(risks=[]))
    assert "**Riesgos / supuestos:**" not in card


def test_format_proposal_card_ends_with_waiting_signal():
    card = format_proposal_card(_make_proposal())
    # Final line must explicitly tell the user to reply, citing the
    # recommended id so they know what they are confirming.
    assert "⏸" in card
    assert "Esperando confirmación" in card
    assert "**[B]**" in card
