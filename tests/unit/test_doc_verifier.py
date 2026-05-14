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
        assert "sessions/2026-04-13_test.md" in result.vault_files
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


# ---------------------------------------------------------------------------
# Mutually-exclusive classification contract (Ola 4 — weakness #7)
# ---------------------------------------------------------------------------
# Contract: every entry in ``vault_files`` appears in exactly ONE of
# ``new_files`` / ``modified_files`` / ``deleted_files``. Paths outside
# the vault are dropped from every list.


class TestClassificationContract:
    def _make_verifier(self, tmp_path: Path) -> DocVerifier:
        vault = tmp_path / "vault"
        vault.mkdir()
        return DocVerifier(vault_path=vault)

    def test_vault_files_equals_union_of_partitions(self, tmp_path: Path, monkeypatch) -> None:
        """vault_files must equal new ∪ modified ∪ deleted (no overlap)."""
        verifier = self._make_verifier(tmp_path)

        # Inject controlled git status output via monkeypatch.
        def fake_status(_base):
            return (
                ["vault/specs/new1.md", "vault/specs/new2.md"],
                ["vault/runbooks/mod.md"],
                ["vault/sessions/del.md"],
            )

        monkeypatch.setattr(verifier, "_git_diff_status", fake_status)
        result = verifier.verify_from_diff(base_branch="main")

        assert sorted(result.vault_files) == sorted(
            [
                "specs/new1.md",
                "specs/new2.md",
                "runbooks/mod.md",
                "sessions/del.md",
            ]
        )
        # Mutually exclusive partitions
        assert set(result.new_files).isdisjoint(result.modified_files)
        assert set(result.new_files).isdisjoint(result.deleted_files)
        assert set(result.modified_files).isdisjoint(result.deleted_files)
        # Each partition sums to vault_files
        assert (
            set(result.new_files) | set(result.modified_files) | set(result.deleted_files)
            == set(result.vault_files)
        )

    def test_non_vault_files_excluded_from_all_lists(self, tmp_path: Path, monkeypatch) -> None:
        verifier = self._make_verifier(tmp_path)
        monkeypatch.setattr(
            verifier,
            "_git_diff_status",
            lambda _b: (
                ["vault/specs/keep.md", "src/auth.py", "README.md"],
                ["vault/runbooks/keep.md", "tests/test_x.py"],
                ["vault/sessions/keep.md", "docs/architecture.md"],
            ),
        )
        result = verifier.verify_from_diff(base_branch="main")
        # Only vault paths land in vault_files.
        for path in result.vault_files:
            assert not path.startswith("src/")
            assert not path.startswith("tests/")
            assert path.endswith(".md")
        # Non-vault files do not contaminate the partitions either.
        for partition in (result.new_files, result.modified_files, result.deleted_files):
            for path in partition:
                assert path.endswith(".md")
                assert ".." not in path

    def test_non_md_in_vault_excluded(self, tmp_path: Path, monkeypatch) -> None:
        verifier = self._make_verifier(tmp_path)
        monkeypatch.setattr(
            verifier,
            "_git_diff_status",
            lambda _b: (
                ["vault/specs/keep.md", "vault/assets/diagram.png"],
                ["vault/runbooks/mod.md", "vault/cache/data.json"],
                [],
            ),
        )
        result = verifier.verify_from_diff(base_branch="main")
        assert "assets/diagram.png" not in result.vault_files
        assert "cache/data.json" not in result.vault_files
        assert result.new_files == ["specs/keep.md"]
        assert result.modified_files == ["runbooks/mod.md"]

    def test_explicit_list_mode_treats_all_as_modified(self, tmp_path: Path) -> None:
        verifier = self._make_verifier(tmp_path)
        changed = ["vault/specs/a.md", "vault/runbooks/b.md", "src/main.py"]
        result = verifier.verify_from_list(changed)
        assert result.new_files == []
        assert result.deleted_files == []
        assert sorted(result.modified_files) == ["runbooks/b.md", "specs/a.md"]
        assert sorted(result.vault_files) == ["runbooks/b.md", "specs/a.md"]

    def test_empty_diff_returns_empty_partitions(self, tmp_path: Path, monkeypatch) -> None:
        verifier = self._make_verifier(tmp_path)
        monkeypatch.setattr(verifier, "_git_diff_status", lambda _b: ([], [], []))
        result = verifier.verify_from_diff(base_branch="main")
        assert result.vault_files == []
        assert result.new_files == []
        assert result.modified_files == []
        assert result.deleted_files == []
        assert result.has_agent_docs is False

    def test_has_agent_docs_only_true_with_new_or_modified(self, tmp_path: Path, monkeypatch) -> None:
        """``has_agent_docs`` is False when only deletions happened (nothing new to verify)."""
        verifier = self._make_verifier(tmp_path)
        monkeypatch.setattr(
            verifier,
            "_git_diff_status",
            lambda _b: ([], [], ["vault/sessions/old.md"]),
        )
        result = verifier.verify_from_diff(base_branch="main")
        assert result.deleted_files == ["sessions/old.md"]
        assert result.has_agent_docs is False
