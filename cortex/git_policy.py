"""
cortex.git_policy
-----------------
Git policy helpers for Cortex projects.

Provides gitignore patterns and snippets that work for both
new-layout (``.cortex/`` workspace) and legacy-layout projects.

EPIC 6: Updated with new-layout-aware patterns.
"""

from __future__ import annotations

from pathlib import Path

from cortex.workspace.layout import WorkspaceLayout

# Patterns that should always be in .gitignore regardless of layout.
# In new layout, memory lives inside .cortex/memory/ which is already
# covered by the general .cortex/ gitignore rule (if users choose to
# ignore the whole .cortex directory). But Chroma artifacts should
# still be explicitly ignored.
RECOMMENDED_GITIGNORE_PATTERNS = (
    ".memory/",
    "*.chroma/",
    "vault/sessions/",
)

# New-layout-specific gitignore patterns. These are safe to add
# regardless of layout mode — the paths won't exist in legacy projects.
NEW_LAYOUT_GITIGNORE_PATTERNS = (
    ".cortex/memory/",
    ".cortex/vault/sessions/",
)

# Legacy-layout patterns.
LEGACY_GITIGNORE_PATTERNS = (
    ".memory/",
    "vault/sessions/",
)


def recommended_gitignore_snippet(
    *,
    layout: WorkspaceLayout | None = None,
    project_root: Path | None = None,
) -> str:
    """Generate a .gitignore snippet appropriate for the detected layout.

    If a ``WorkspaceLayout`` is provided, the snippet is tailored to
    the layout mode.  If neither ``layout`` nor ``project_root`` is
    given, a conservative snippet that covers both layouts is returned.

    Parameters
    ----------
    layout:
        A pre-resolved WorkspaceLayout.  Takes precedence over
        ``project_root``.
    project_root:
        Used to discover the layout if ``layout`` is not provided.
    """
    if layout is None and project_root is not None:
        layout = WorkspaceLayout.discover(project_root)

    if layout is not None and layout.is_new_layout:
        return "\n".join(
            [
                "# Cortex local state (new layout)",
                ".cortex/memory/",
                "*.chroma/",
                "",
                "# Cortex vault policy",
                "# Track: vault/specs, vault/decisions, vault/runbooks, vault/hu, vault/incidents",
                "# Ignore session churn by default unless your team explicitly audits sessions in Git",
                ".cortex/vault/sessions/",
            ]
        )

    # Legacy or unknown layout — return the conservative superset
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