"""Tests for ``SpecService`` integration with verification hooks (T1.1)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pytest

from cortex.services.spec_service import SpecService
from cortex.session import VerificationHook


class _DummySemantic:
    def __init__(self) -> None:
        self.indexed: list[str] = []

    def index_file(self, rel_path: str) -> bool:
        self.indexed.append(rel_path)
        return True

    def sync(self) -> int:
        return 0


class _DummyEpisodic:
    def add(self, **kwargs: Any) -> object:
        return object()


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    v.mkdir()
    return v


@pytest.fixture
def service(vault: Path) -> SpecService:
    return SpecService(
        vault_path=vault,
        semantic=_DummySemantic(),  # type: ignore[arg-type]
        episodic=_DummyEpisodic(),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


class TestCreateWithHooks:
    def test_create_with_pydantic_hooks_persists_in_frontmatter(
        self, service: SpecService, vault: Path
    ) -> None:
        result = service.create(
            title="Auth JWT",
            goal="Implementar refresh tokens",
            verification_hooks=[
                VerificationHook(name="tests", command="pytest tests/auth/"),
                VerificationHook(
                    name="lint",
                    command="ruff check src/auth.py",
                    required=False,
                ),
            ],
        )
        text = result.path.read_text(encoding="utf-8")
        # Frontmatter contains the hooks (YAML mapping).
        assert "verification_hooks" in text
        assert "pytest tests/auth/" in text
        assert "ruff check src/auth.py" in text
        # Body section also renders them.
        assert "## Verification Hooks" in text
        assert re.search(r"###\s+tests", text)
        assert "*(optional)*" in text  # required=False marker

    def test_create_accepts_dict_hooks(self, service: SpecService) -> None:
        result = service.create(
            title="Dict input",
            goal="...",
            verification_hooks=[
                {"name": "tests", "command": "pytest"},
            ],
        )
        assert result.path.is_file()


# ---------------------------------------------------------------------------
# Backward compatibility / soft warning
# ---------------------------------------------------------------------------


class TestLegacyCompat:
    def test_create_without_hooks_logs_warning(
        self, service: SpecService, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="cortex.services.spec_service"):
            service.create(title="Legacy", goal="no hooks")
        warnings = [r for r in caplog.records if "verification_hooks" in r.message]
        assert warnings, "expected a soft warning for missing verification_hooks"

    def test_template_renders_legacy_message_when_no_hooks(self, service: SpecService) -> None:
        result = service.create(title="Legacy", goal="...")
        body = result.path.read_text(encoding="utf-8")
        assert "## Verification Hooks" in body
        assert "legacy spec" in body


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_duplicate_hook_names_rejected(self, service: SpecService) -> None:
        with pytest.raises(ValueError, match="duplicate"):
            service.create(
                title="Dup",
                goal="...",
                verification_hooks=[
                    VerificationHook(name="tests", command="pytest"),
                    VerificationHook(name="tests", command="pytest -x"),
                ],
            )

    def test_invalid_hook_dict_raises_validation(self, service: SpecService) -> None:
        # Missing required field "command".
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            service.create(
                title="Bad",
                goal="...",
                verification_hooks=[{"name": "tests"}],
            )
