"""Tests for :class:`cortex.ci.validator.CiValidator`."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cortex.ci.result import ValidationInput
from cortex.ci.validator import (
    EXIT_BLOCKED,
    EXIT_PASS,
    EXIT_WARN,
    CiValidator,
)
from cortex.session import SessionStatus
from cortex.session.service import SessionService
from cortex.session.storage import SessionStorage
from cortex.session.verification import VerificationRunner

PY = sys.executable


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@x.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=repo, check=True)
    (repo / "src").mkdir()
    (repo / "src" / "x.py").write_text("def x(): return 1\n", encoding="utf-8")

    vault = repo / "vault"
    (vault / "specs").mkdir(parents=True)
    spec_path = vault / "specs" / "2026-05-17_demo.md"
    spec_path.write_text(
        textwrap.dedent(
            """\
            ---
            title: demo
            doc_type: spec
            goal: keep x working
            files_in_scope:
              - src/x.py
            verification_hooks:
              - {name: smoke, command: %s -c "exit(0)", required: true, success_criteria: "exit 0", timeout_seconds: 30}
            ---
            """
        )
        % PY,
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


@pytest.fixture
def service(repo: Path, tmp_path: Path) -> SessionService:
    return SessionService(SessionStorage(tmp_path / "sessions"), repo_root=repo)


@pytest.fixture
def validator(service: SessionService, repo: Path) -> CiValidator:
    return CiValidator(
        session_service=service,
        verification_runner=VerificationRunner(repo_root=repo),
        repo_root=repo,
    )


def _diff(touched: list[str]) -> str:
    chunks: list[str] = []
    for path in touched:
        chunks.append(f"--- a/{path}\n+++ b/{path}\n@@ -1 +1,2 @@\n x\n+new\n")
    return "\n".join(chunks)


def _payload(diff_text: str, repo: Path, **overrides: object) -> ValidationInput:
    base = ValidationInput(
        diff_text=diff_text,
        repo_root=repo,
    )
    if overrides:
        return ValidationInput(
            diff_text=diff_text,
            repo_root=repo,
            base_commit=str(overrides.get("base_commit") or "") or None,
            head_commit=str(overrides.get("head_commit") or "") or None,
            base_branch=str(overrides.get("base_branch") or "") or None,
            head_branch=str(overrides.get("head_branch") or "") or None,
            pr_number=overrides.get("pr_number"),  # type: ignore[arg-type]
            pr_author=str(overrides.get("pr_author") or "") or None,
            explicit_session_id=str(overrides.get("explicit_session_id") or "")
            or None,
        )
    return base


class TestValidatorMatching:
    def test_explicit_match(
        self, validator: CiValidator, service: SessionService, repo: Path
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        result = validator.validate(
            _payload(_diff(["src/x.py"]), repo, explicit_session_id=rec.session_id)
        )
        assert result.session_match == "explicit"
        assert result.matched_session is not None

    def test_no_match_yields_blocked(self, validator: CiValidator, repo: Path) -> None:
        result = validator.validate(_payload(_diff(["src/x.py"]), repo))
        assert result.session_match == "none"
        assert result.exit_code == EXIT_BLOCKED
        assert any("No Cortex Session" in b for b in result.blockers)


class TestScopeChecks:
    def test_in_scope_pass(
        self, validator: CiValidator, service: SessionService, repo: Path
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        result = validator.validate(
            _payload(_diff(["src/x.py"]), repo, explicit_session_id=rec.session_id)
        )
        assert result.exit_code == EXIT_PASS
        assert result.scope_drift == []

    def test_out_of_scope_yields_warning(
        self, validator: CiValidator, service: SessionService, repo: Path
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        result = validator.validate(
            _payload(
                _diff(["src/x.py", "src/unexpected.py"]),
                repo,
                explicit_session_id=rec.session_id,
            )
        )
        assert any(f.reason == "out_of_scope" for f in result.scope_drift)
        assert result.exit_code == EXIT_WARN

    def test_unimplemented_yields_block(
        self, validator: CiValidator, service: SessionService, repo: Path
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        # Diff touches nothing in scope; required hook still passes,
        # but the unimplemented file in scope blocks.
        result = validator.validate(
            _payload(_diff(["src/other.py"]), repo, explicit_session_id=rec.session_id)
        )
        assert any(f.reason == "unimplemented" for f in result.scope_drift)
        assert result.exit_code == EXIT_BLOCKED


class TestHookSeverity:
    def test_required_hook_failure_blocks(
        self,
        validator: CiValidator,
        service: SessionService,
        repo: Path,
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        # Rewrite the spec to a failing required hook.
        spec_path = repo / "vault" / "specs" / "2026-05-17_demo.md"
        spec_path.write_text(
            spec_path.read_text(encoding="utf-8").replace("exit(0)", "exit(1)"),
            encoding="utf-8",
        )
        result = validator.validate(
            _payload(_diff(["src/x.py"]), repo, explicit_session_id=rec.session_id)
        )
        assert result.exit_code == EXIT_BLOCKED
        assert any("required hook" in b for b in result.blockers)


class TestLifecycleStatusEffects:
    def test_handoff_session_warns(
        self,
        validator: CiValidator,
        service: SessionService,
        repo: Path,
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        service.close(
            rec.session_id,
            status=SessionStatus.HANDOFF,
            documenter_decision=SessionStatus.HANDOFF,
        )
        result = validator.validate(
            _payload(_diff(["src/x.py"]), repo, explicit_session_id=rec.session_id)
        )
        # HANDOFF triggers a warning; if no blockers it lands at WARN.
        assert result.exit_code in (EXIT_WARN, EXIT_BLOCKED)
        assert any("HANDOFF" in w for w in result.warnings)


class TestSerialization:
    def test_json_dict_stable_keys(
        self,
        validator: CiValidator,
        service: SessionService,
        repo: Path,
    ) -> None:
        rec = service.open(
            spec_id="2026-05-17_demo",
            spec_path=Path("vault/specs/2026-05-17_demo.md"),
        )
        result = validator.validate(
            _payload(_diff(["src/x.py"]), repo, explicit_session_id=rec.session_id)
        )
        payload = result.to_json_dict()
        for key in (
            "status",
            "exit_code",
            "session_match",
            "session_id",
            "files_in_diff",
            "scope_drift",
            "verification_results",
            "blockers",
            "warnings",
            "summary_text",
        ):
            assert key in payload
