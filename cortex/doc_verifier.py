"""
cortex.doc_verifier
-------------------
Detects whether a PR includes agent-generated documentation in the vault.

Works in two modes:
- **Local**: uses ``git diff`` against a base branch to find new/modified vault files.
- **CI**: receives a list of changed files from the PR payload and checks which ones
  live inside the vault directory.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DocVerificationResult:
    """Result of verifying whether a PR contains agent-generated docs."""

    has_agent_docs: bool = False
    vault_files: list[str] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    valid_files: list[str] = field(default_factory=list)
    invalid_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_vault_files(self) -> int:
        return len(self.vault_files)

    @property
    def total_changes(self) -> int:
        return len(self.new_files) + len(self.modified_files) + len(self.deleted_files)

    def to_dict(self) -> dict:
        return {
            "has_agent_docs": self.has_agent_docs,
            "vault_files": self.vault_files,
            "new_files": self.new_files,
            "modified_files": self.modified_files,
            "deleted_files": self.deleted_files,
            "valid_files": self.valid_files,
            "invalid_files": self.invalid_files,
            "errors": self.errors,
            "total_vault_files": self.total_vault_files,
            "total_changes": self.total_changes,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class DocVerifier:
    """
    Verifies whether a PR contains agent-generated documentation.

    Parameters
    ----------
    vault_path : str | Path
        Path to the vault directory (relative to repo root or absolute).
    root : str | Path | None
        Repository root. Defaults to current working directory.
    """

    def __init__(self, vault_path: str | Path, root: str | Path | None = None):
        self.vault_path = Path(vault_path)
        self.root = Path(root) if root else Path.cwd()
        # If vault_path is absolute, use its parent as root
        if self.vault_path.is_absolute():
            self.root = self.vault_path.parent

    def verify_from_diff(
        self,
        base_branch: str = "main",
        changed_files: list[str] | None = None,
    ) -> DocVerificationResult:
        """
        Verify docs using git diff or an explicit file list.

        Parameters
        ----------
        base_branch : str
            Branch to diff against (used when *changed_files* is None).
        changed_files : list[str] | None
            Explicit list of changed file paths. When provided, git diff
            is skipped and this list is used directly.
        """
        result = DocVerificationResult()

        # Discover vault-relative paths
        vault_rel = self._get_vault_relative()
        if vault_rel is None:
            result.errors.append(
                f"Vault directory not found: {self.vault_path}"
            )
            return result

        # Determine changed files
        if changed_files is not None:
            files = changed_files
        else:
            try:
                files = self._git_diff_files(base_branch)
            except subprocess.CalledProcessError as exc:
                result.errors.append(f"git diff failed: {exc.stderr}")
                return result

        # Classify files
        for fpath in files:
            if fpath.startswith(vault_rel + "/") or fpath == vault_rel:
                continue  # the vault directory itself isn't a doc

            if fpath.startswith(vault_rel):
                rel_to_vault = fpath[len(vault_rel) + 1:]
                if rel_to_vault.endswith(".md"):
                    result.vault_files.append(rel_to_vault)

        # For new/modified detection we need status info
        if changed_files is None:
            try:
                new, modified, deleted = self._git_diff_status(base_branch)
            except subprocess.CalledProcessError as exc:
                result.errors.append(f"git status failed: {exc.stderr}")
                new, modified, deleted = [], [], []
        else:
            # Without git status, treat all as modified
            new, modified, deleted = [], changed_files, []

        for fpath in new:
            if fpath.startswith(vault_rel + "/") and fpath.endswith(".md"):
                result.new_files.append(fpath[len(vault_rel) + 1:])

        for fpath in modified:
            if fpath.startswith(vault_rel + "/") and fpath.endswith(".md"):
                result.modified_files.append(fpath[len(vault_rel) + 1:])

        for fpath in deleted:
            if fpath.startswith(vault_rel + "/") and fpath.endswith(".md"):
                result.deleted_files.append(fpath[len(vault_rel) + 1:])

        result.has_agent_docs = bool(result.new_files) or bool(result.modified_files)
        return result

    def verify_from_list(
        self, changed_files: list[str]
    ) -> DocVerificationResult:
        """Convenience wrapper for CI usage with an explicit file list."""
        return self.verify_from_diff(changed_files=changed_files)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_vault_relative(self) -> str | None:
        """Return the vault path relative to repo root, or None."""
        try:
            return str(self.vault_path.relative_to(self.root))
        except ValueError:
            return None

    def _git_diff_files(self, base_branch: str) -> list[str]:
        """Return list of files changed vs *base_branch*."""
        out = subprocess.check_output(
            ["git", "diff", "--name-only", base_branch, "--"],
            cwd=self.root,
            text=True,
        )
        return [f for f in out.strip().splitlines() if f]

    def _git_diff_status(
        self, base_branch: str
    ) -> tuple[list[str], list[str], list[str]]:
        """Return (new, modified, deleted) file lists vs *base_branch*."""
        out = subprocess.check_output(
            ["git", "diff", "--name-status", base_branch, "--"],
            cwd=self.root,
            text=True,
        )
        new: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []
        for line in out.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            status, filepath = parts[0], parts[1]
            if status == "A":
                new.append(filepath)
            elif status in ("M", "R", "C"):
                modified.append(filepath)
            elif status == "D":
                deleted.append(filepath)
        return new, modified, deleted
