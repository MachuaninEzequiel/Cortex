from __future__ import annotations

from pathlib import Path

TRACKED_VAULT_DIRS = (
    "vault/specs/",
    "vault/decisions/",
    "vault/runbooks/",
    "vault/hu/",
    "vault/incidents/",
)
OPTIONAL_VAULT_DIRS = (
    "vault/sessions/",
)
LOCAL_ONLY_PATTERNS = (
    ".memory/",
    "*.chroma/",
)
RECOMMENDED_GITIGNORE_PATTERNS = (
    ".memory/",
    "*.chroma/",
    "vault/sessions/",
)


def recommended_gitignore_snippet() -> str:
    return "\n".join(
        [
            "# Cortex local state",
            ".memory/",
            "*.chroma/",
            "",
            "# Cortex vault policy",
            "# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents",
            "# Ignore session churn by default unless your team explicitly audits sessions in Git",
            "vault/sessions/",
        ]
    )


def gitignore_contains(root: Path, pattern: str) -> bool:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return False
    normalized = pattern.strip()
    for line in gitignore.read_text(encoding="utf-8").splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if candidate == normalized:
            return True
    return False
