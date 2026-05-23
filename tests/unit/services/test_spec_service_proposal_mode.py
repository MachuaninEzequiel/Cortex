"""Tests for the Phase 09.A ``proposal_mode`` gate on :class:`SpecService`.

The gate has three values:

* ``optional`` (default) — ``SpecService.create`` always proceeds.
  ``cortex-sync`` may have emitted a proposal but no confirmation is
  required from the caller.
* ``required`` — the caller MUST set ``proposal_confirmed=True``. Any
  other value raises :class:`ValueError`.
* ``skip`` — the gate is bypassed entirely (legacy / Fast track).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.services.spec_service import SpecService


class _DummySemantic:
    def __init__(self) -> None:
        self.indexed: list[str] = []

    def index_file(self, rel_path: str) -> bool:
        self.indexed.append(rel_path)
        return True

    def sync(self) -> int:
        return 0


class _DummyEpisodic:
    def __init__(self) -> None:
        self.added: list[dict[str, object]] = []

    def add(self, **kwargs: object) -> object:
        self.added.append(kwargs)
        return object()


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "specs").mkdir(parents=True)
    return v


def _service(vault: Path) -> SpecService:
    return SpecService(
        vault_path=vault,
        semantic=_DummySemantic(),  # type: ignore[arg-type]
        episodic=_DummyEpisodic(),  # type: ignore[arg-type]
    )


class TestProposalModeOptional:
    def test_default_is_optional(self, vault: Path) -> None:
        """No flag passed → behaves like the legacy unguarded create."""
        svc = _service(vault)
        result = svc.create(title="demo", goal="anything")
        assert result.path.is_file()

    def test_optional_does_not_require_confirmation(self, vault: Path) -> None:
        svc = _service(vault)
        result = svc.create(
            title="demo-opt",
            goal="anything",
            proposal_mode="optional",
            proposal_confirmed=False,
        )
        assert result.path.is_file()


class TestProposalModeRequired:
    def test_required_without_confirmation_raises(self, vault: Path) -> None:
        svc = _service(vault)
        with pytest.raises(ValueError, match="proposal was not confirmed"):
            svc.create(
                title="demo-req",
                goal="anything",
                proposal_mode="required",
                proposal_confirmed=False,
            )

    def test_required_with_confirmation_succeeds(self, vault: Path) -> None:
        svc = _service(vault)
        result = svc.create(
            title="demo-req-ok",
            goal="anything",
            proposal_mode="required",
            proposal_confirmed=True,
        )
        assert result.path.is_file()


class TestProposalModeSkip:
    def test_skip_bypasses_check_even_without_confirmation(self, vault: Path) -> None:
        svc = _service(vault)
        result = svc.create(
            title="demo-skip",
            goal="anything",
            proposal_mode="skip",
            proposal_confirmed=False,
        )
        assert result.path.is_file()


class TestProposalModeValidation:
    def test_unknown_mode_raises(self, vault: Path) -> None:
        svc = _service(vault)
        with pytest.raises(ValueError, match="proposal_mode must be one of"):
            svc.create(
                title="demo-bad",
                goal="anything",
                proposal_mode="invalid-mode",
            )
