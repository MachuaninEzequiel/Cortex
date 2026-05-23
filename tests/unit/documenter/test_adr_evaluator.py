"""Tests for :mod:`cortex.documenter.adr_evaluator` (T1.4 helper)."""

from __future__ import annotations

from datetime import UTC, datetime

from cortex.documenter.adr_evaluator import suggest_adrs
from cortex.session.models import Checkpoint, CheckpointSource


def _cp(note: str) -> Checkpoint:
    return Checkpoint(
        timestamp=datetime(2026, 5, 16, 12, tzinfo=UTC),
        source=CheckpointSource.CORTEX_SDDWORK,
        note=note,
    )


def test_no_checkpoints_yields_no_suggestions() -> None:
    assert suggest_adrs([]) == []


def test_empty_note_skipped() -> None:
    assert suggest_adrs([_cp(""), _cp("   ")]) == []


def test_note_without_decision_keywords_skipped() -> None:
    assert suggest_adrs([_cp("Just a normal note about progress.")]) == []


def test_one_keyword_low_confidence() -> None:
    suggestions = suggest_adrs([_cp("Chose pytest for testing.")])
    assert len(suggestions) == 1
    assert suggestions[0].confidence == "low"


def test_two_keywords_high_confidence() -> None:
    suggestions = suggest_adrs(
        [_cp("Decidimos usar bcrypt instead of argon2 (trade-off de perf vs portabilidad).")]
    )
    assert len(suggestions) == 1
    assert suggestions[0].confidence == "high"


def test_title_truncated_to_80_chars() -> None:
    long_note = "Decidimos algo " + ("x" * 200)
    suggestions = suggest_adrs([_cp(long_note)])
    assert len(suggestions[0].title) <= 80
    assert suggestions[0].title.endswith("...")


def test_source_checkpoint_index_recorded() -> None:
    suggestions = suggest_adrs([_cp("nothing here"), _cp("Decidimos algo")])
    assert len(suggestions) == 1
    assert suggestions[0].source_checkpoint_index == 1
