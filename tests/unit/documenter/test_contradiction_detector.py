"""Tests for :mod:`cortex.documenter.contradiction_detector` (T1.4 helper)."""

from __future__ import annotations

from cortex.documenter.contradiction_detector import (
    ContradictionDetector,
    ContradictionFinding,
    NoOpContradictionDetector,
)


def test_noop_returns_empty_list() -> None:
    detector = NoOpContradictionDetector()
    assert detector.find_contradictions("summary", "diff", []) == []


def test_noop_conforms_to_protocol() -> None:
    detector = NoOpContradictionDetector()
    assert isinstance(detector, ContradictionDetector)


def test_finding_severity_default_info() -> None:
    finding = ContradictionFinding(
        prior_record="ADR-2026-04-01: bcrypt",
        current_claim="Using argon2",
        evidence="src/auth.py +argon2",
    )
    assert finding.severity == "info"
