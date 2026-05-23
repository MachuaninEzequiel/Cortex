"""Tests for :mod:`cortex.documenter.spec_loader` (T1.4 helper)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from cortex.documenter.spec_loader import LoadedSpec, load_spec


def _write_spec(path: Path, frontmatter: str, body: str = "") -> None:
    text = f"---\n{frontmatter}---\n{body}"
    path.write_text(text, encoding="utf-8")


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    spec = load_spec(tmp_path / "absent.md")
    assert isinstance(spec, LoadedSpec)
    assert spec.title == ""
    assert spec.verification_hooks == []


def test_loads_title_and_goal(tmp_path: Path) -> None:
    p = tmp_path / "spec.md"
    _write_spec(
        p,
        "title: Auth JWT\ndoc_type: spec\ngoal: Implementar refresh tokens\n",
    )
    spec = load_spec(p)
    assert spec.title == "Auth JWT"
    assert spec.goal == "Implementar refresh tokens"


def test_loads_files_in_scope_and_acceptance(tmp_path: Path) -> None:
    p = tmp_path / "spec.md"
    _write_spec(
        p,
        "title: x\nfiles_in_scope:\n  - src/a.py\n  - src/b.py\n"
        "acceptance_criteria:\n  - a\n  - b\n",
    )
    spec = load_spec(p)
    assert spec.files_in_scope == [Path("src/a.py"), Path("src/b.py")]
    assert spec.acceptance_criteria == ["a", "b"]


def test_loads_verification_hooks(tmp_path: Path) -> None:
    p = tmp_path / "spec.md"
    _write_spec(
        p,
        "title: t\nverification_hooks:\n"
        "  - {name: tests, command: pytest, required: true, "
        "success_criteria: 'exit 0', timeout_seconds: 300}\n"
        "  - {name: lint, command: ruff check ., required: false, "
        "success_criteria: 'exit 0', timeout_seconds: 60}\n",
    )
    spec = load_spec(p)
    assert len(spec.verification_hooks) == 2
    assert spec.verification_hooks[0].name == "tests"
    assert spec.verification_hooks[1].required is False


def test_invalid_hook_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    p = tmp_path / "spec.md"
    _write_spec(
        p,
        "title: t\nverification_hooks:\n"
        "  - {name: ok, command: pytest}\n"
        "  - 'not-a-mapping'\n"
        "  - {name: bad}\n",  # missing command
    )
    with caplog.at_level(logging.WARNING, logger="cortex.documenter.spec_loader"):
        spec = load_spec(p)
    assert [h.name for h in spec.verification_hooks] == ["ok"]
    assert len(caplog.records) >= 2


def test_legacy_spec_without_hooks_loads_clean(tmp_path: Path) -> None:
    p = tmp_path / "spec.md"
    _write_spec(p, "title: legacy\ngoal: no hooks\n", body="## Goal\nlegacy body\n")
    spec = load_spec(p)
    assert spec.title == "legacy"
    assert spec.verification_hooks == []


def test_no_frontmatter_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "spec.md"
    p.write_text("# just a markdown file\n", encoding="utf-8")
    spec = load_spec(p)
    assert spec.title == ""


def test_load_hooks_accepts_pre_built_instances(tmp_path: Path) -> None:
    """The internal hook coercion accepts ready-made VerificationHook objects.

    Used when an in-process caller hands the loader pre-validated hooks
    instead of plain dicts.
    """
    from cortex.documenter.spec_loader import _load_hooks
    from cortex.session import VerificationHook

    raw = [VerificationHook(name="ready", command="pytest")]
    out = _load_hooks(raw)
    assert out == raw


def test_extract_section_handles_os_error(tmp_path: Path) -> None:
    """When the file can't be read mid-parse the fallback returns ''."""
    from cortex.documenter.spec_loader import _extract_section

    # A directory path is unreadable as text — exercises the OSError branch.
    nonexistent = tmp_path / "this" / "does" / "not" / "exist.md"
    assert _extract_section(nonexistent, "## Goal") == ""


def test_goal_falls_back_to_body_section(tmp_path: Path) -> None:
    p = tmp_path / "spec.md"
    # No ``goal`` in frontmatter, but a ## Goal section in the body.
    _write_spec(
        p,
        "title: body-fallback\n",
        body="## Goal\nfrom body\n\n## Requirements\nx\n",
    )
    spec = load_spec(p)
    assert spec.goal == "from body"
