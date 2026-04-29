from __future__ import annotations

from cortex.enterprise.knowledge_promotion import PromotionRulesEngine


def test_promotion_rules_engine_excludes_sessions_by_default() -> None:
    rules = PromotionRulesEngine(allowed_doc_types={"spec", "decision", "runbook", "hu", "incident"})
    ok, reason = rules.is_promotable("sessions/2026-01-01_test.md")
    assert ok is False
    assert "sessions" in reason.lower()


def test_promotion_rules_engine_allows_spec_family() -> None:
    rules = PromotionRulesEngine(allowed_doc_types={"spec"})
    ok, reason = rules.is_promotable("specs/2026-01-01_feature.md")
    assert ok is True
    assert reason == "allowed"


def test_promotion_rules_engine_excludes_internal_metadata() -> None:
    rules = PromotionRulesEngine(allowed_doc_types={"spec"})
    ok, reason = rules.is_promotable(".cortex/promotion/records.jsonl")
    assert ok is False
    assert "internal" in reason.lower()

