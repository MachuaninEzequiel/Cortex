"""Tests for cortex.context_enricher.doc_intent (Fase 08)."""

from __future__ import annotations

import pytest

from cortex.context_enricher.doc_intent import (
    DocIntent,
    DocIntentDetector,
)


@pytest.fixture
def detector() -> DocIntentDetector:
    return DocIntentDetector()


# ---------------------------------------------------------------------------
# Per-intent recognition (English + Spanish samples)
# ---------------------------------------------------------------------------


def test_decision_intent_why_did(detector: DocIntentDetector) -> None:
    assert detector.detect("why did we choose JWT?").intent == DocIntent.DECISION


def test_decision_intent_rationale(detector: DocIntentDetector) -> None:
    assert detector.detect("what is the rationale for ADR-007?").intent == DocIntent.DECISION


def test_decision_intent_spanish(detector: DocIntentDetector) -> None:
    assert detector.detect("por que decidimos esta arquitectura").intent == DocIntent.DECISION


def test_architecture_intent(detector: DocIntentDetector) -> None:
    assert detector.detect("describe the auth architecture").intent == DocIntent.ARCHITECTURE
    assert detector.detect("show the design diagram").intent == DocIntent.ARCHITECTURE


def test_runbook_intent_how_to_deploy(detector: DocIntentDetector) -> None:
    assert detector.detect("how do I deploy the auth service").intent == DocIntent.RUNBOOK


def test_runbook_intent_kw(detector: DocIntentDetector) -> None:
    assert detector.detect("look up the runbook").intent == DocIntent.RUNBOOK


def test_incident_intent(detector: DocIntentDetector) -> None:
    assert detector.detect("auth outage yesterday").intent == DocIntent.INCIDENT


def test_postmortem_intent(detector: DocIntentDetector) -> None:
    assert detector.detect("what was the root cause").intent == DocIntent.POSTMORTEM


def test_spec_intent(detector: DocIntentDetector) -> None:
    assert detector.detect("what are the acceptance criteria").intent == DocIntent.SPEC


def test_recent_intent(detector: DocIntentDetector) -> None:
    assert detector.detect("latest changes to login").intent == DocIntent.RECENT


def test_history_intent(detector: DocIntentDetector) -> None:
    assert detector.detect("what did we do last sprint").intent == DocIntent.HISTORY


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def test_generic_for_no_signal(detector: DocIntentDetector) -> None:
    assert detector.detect("hello there").intent == DocIntent.GENERIC


def test_empty_query_returns_generic_zero_confidence(detector: DocIntentDetector) -> None:
    res = detector.detect("")
    assert res.intent == DocIntent.GENERIC
    assert res.confidence == 0.0
    assert res.matched_signals == []


def test_whitespace_only_query_returns_generic(detector: DocIntentDetector) -> None:
    assert detector.detect("   \n   ").intent == DocIntent.GENERIC


# ---------------------------------------------------------------------------
# Priority order
# ---------------------------------------------------------------------------


def test_postmortem_wins_over_incident_when_both_present(detector: DocIntentDetector) -> None:
    """``root cause`` triggers POSTMORTEM even alongside ``outage``."""
    res = detector.detect("root cause of the outage")
    assert res.intent == DocIntent.POSTMORTEM


def test_multiple_signals_boost_confidence(detector: DocIntentDetector) -> None:
    res1 = detector.detect("rationale")
    res2 = detector.detect("why did we, what is the rationale, and the decision")
    assert res2.confidence > res1.confidence
