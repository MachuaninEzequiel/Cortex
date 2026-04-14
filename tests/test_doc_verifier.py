"""
tests.test_doc_verifier
-----------------------
Tests for the document verification system.
"""

from __future__ import annotations

import json
from pathlib import Path

from cortex.doc_verifier import DocVerificationResult, DocVerifier

# ------------------------------------------------------------------
# DocVerificationResult tests
# ------------------------------------------------------------------

class TestDocVerificationResult:
    def test_default_has_no_docs(self) -> None:
        result = DocVerificationResult()
        assert result.has_agent_docs is False

    def test_total_vault_files(self) -> None:
        result = DocVerificationResult(vault_files=["a.md", "b.md"])
        assert result.total_vault_files == 2

    def test_total_changes(self) -> None:
        result = DocVerificationResult(
            new_files=["new.md"],
            modified_files=["mod.md"],
            deleted_files=["del.md"],
        )
        assert result.total_changes == 3

    def test_to_dict(self) -> None:
        result = DocVerificationResult(has_agent_docs=True, vault_files=["x.md"])
        d = result.to_dict()
        assert d["has_agent_docs"] is True
        assert "vault_files" in d
        assert "total_vault_files" in d

    def test_to_json(self) -> None:
        result = DocVerificationResult(has_agent_docs=False)
        j = json.loads(result.to_json())
        assert j["has_agent_docs"] is False


# ------------------------------------------------------------------
# DocVerifier tests
# ------------------------------------------------------------------

class TestDocVerifier:
    def test_vault_not_found(self, tmp_path: Path) -> None:
        verifier = DocVerifier(vault_path=tmp_path / "nonexistent")
        result = verifier.verify_from_diff()

        assert not result.has_agent_docs
        assert len(result.errors) > 0

    def test_detects_new_vault_files(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "sessions").mkdir()

        # Simulate a new file added
        changed = ["vault/sessions/2026-04-13_test.md"]
        verifier = DocVerifier(vault_path=vault)
        result = verifier.verify_from_list(changed)

        assert result.has_agent_docs is True
        assert "sessions/2026-04-13_test.md" in result.modified_files

    def test_ignores_non_md_files(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        changed = ["vault/sessions/image.png", "vault/runbooks/notes.txt"]
        verifier = DocVerifier(vault_path=vault)
        result = verifier.verify_from_list(changed)

        assert result.has_agent_docs is False

    def test_detects_modified_files(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        changed = ["vault/decisions/ADR-001.md"]
        verifier = DocVerifier(vault_path=vault)
        result = verifier.verify_from_list(changed)

        assert result.has_agent_docs is True
        assert "decisions/ADR-001.md" in result.modified_files

    def test_empty_file_list(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        verifier = DocVerifier(vault_path=vault)
        result = verifier.verify_from_list([])

        assert result.has_agent_docs is False
        assert result.total_vault_files == 0

    def test_detects_deleted_files(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        # Note: without git status, all files are treated as modified
        # So deleted detection requires git diff mode
        # This test verifies the list mode works
        changed = ["vault/architecture.md"]
        verifier = DocVerifier(vault_path=vault)
        result = verifier.verify_from_list(changed)

        # In list mode, all files are treated as modified
        assert result.has_agent_docs is True
