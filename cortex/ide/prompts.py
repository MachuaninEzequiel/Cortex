"""
cortex.ide.prompts
------------------
Centralized prompt generation for Cortex agent profiles.

Reads the actual skill files from the workspace layout (using
WorkspaceLayout to resolve paths) as the single source of truth.
Never hardcodes prompt content — always derives from the real files on disk.

EPIC 5: All path resolution now goes through WorkspaceLayout so that
new-layout projects (where skills/subagents live under
repo_root/.cortex/) and legacy projects both work correctly.
"""

from __future__ import annotations

from pathlib import Path

from cortex.workspace.layout import WorkspaceLayout


def split_markdown_frontmatter(content: str) -> tuple[str | None, str]:
    """Split optional YAML frontmatter from markdown content."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, content.strip()

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            frontmatter = "\n".join(lines[1:index]).strip()
            body = "\n".join(lines[index + 1 :]).strip()
            return frontmatter, body

    return None, content.strip()


def strip_markdown_frontmatter(content: str) -> str:
    """Return markdown content without the leading YAML frontmatter."""
    _, body = split_markdown_frontmatter(content)
    return body


def get_skill_prompt(project_root: Path, skill_name: str, *, workspace_layout: WorkspaceLayout | None = None) -> str:
    """Read a skill prompt from the workspace skills directory.

    Args:
        project_root: Path to the Cortex project repo root.
        skill_name: Name of the skill (e.g. 'cortex-sync', 'cortex-SDDwork').
        workspace_layout: Optional WorkspaceLayout for path resolution.

    Returns:
        The skill prompt content, or a minimal fallback if file doesn't exist.
    """
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    skill_path = layout.skills_dir / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"# {skill_name}\n\nSkill file not found. Run `cortex setup agent` to generate."


def get_subagent_prompt(project_root: Path, subagent_name: str, *, workspace_layout: WorkspaceLayout | None = None) -> str:
    """Read a subagent prompt from the workspace subagents directory.

    Args:
        project_root: Path to the Cortex project repo root.
        subagent_name: Name of the subagent (e.g. 'cortex-code-explorer').
        workspace_layout: Optional WorkspaceLayout for path resolution.

    Returns:
        The subagent prompt content, or a minimal fallback.
    """
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    subagent_path = layout.subagents_dir / f"{subagent_name}.md"
    if subagent_path.exists():
        return subagent_path.read_text(encoding="utf-8")
    return f"# {subagent_name}\n\nYou are {subagent_name}, a Cortex subagent."


def get_available_subagents(project_root: Path, *, workspace_layout: WorkspaceLayout | None = None) -> list[str]:
    """Discover which subagents actually exist on disk.

    Returns:
        List of subagent names (without .md extension).
    """
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    subagents_dir = layout.subagents_dir
    if not subagents_dir.exists():
        return []
    return sorted(p.stem for p in subagents_dir.glob("*.md"))


def build_all_prompts(project_root: Path, *, workspace_layout: WorkspaceLayout | None = None) -> dict[str, str]:
    """Build the full set of Cortex prompts for injection.

    Returns a dict with at least:
        - 'cortex-sync': The pre-flight analysis prompt
        - 'cortex-SDDwork': The implementation orchestrator prompt

    These are read directly from the workspace skills files.
    """
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    prompts: dict[str, str] = {}

    # Core skills (always injected)
    for skill_name in ("cortex-sync", "cortex-SDDwork"):
        prompts[skill_name] = get_skill_prompt(project_root, skill_name, workspace_layout=layout)

    return prompts


def build_cursor_prompts(project_root: Path, *, workspace_layout: WorkspaceLayout | None = None) -> dict[str, str]:
    """Build Cortex prompts specifically for Cursor IDE.

    Cursor only supports subagents, so we use a hybrid architecture:
        - 'cortex-sync': Pre-flight analysis (unchanged)
        - 'cortex-SDDwork-cursor': Hybrid orchestrator (explorer + implementer combined)
        - 'cortex-documenter': Documentation specialist (from subagents)

    Returns:
        Dict with the 3 Cursor-specific prompts.
    """
    layout = workspace_layout or WorkspaceLayout.discover(project_root)
    prompts: dict[str, str] = {}

    # Cortex-sync (unchanged)
    prompts["cortex-sync"] = get_skill_prompt(project_root, "cortex-sync", workspace_layout=layout)

    # Cortex-SDDwork-cursor (hybrid version for Cursor)
    prompts["cortex-SDDwork-cursor"] = get_skill_prompt(project_root, "cortex-SDDwork-cursor", workspace_layout=layout)

    # Cortex-documenter (from subagents directory)
    prompts["cortex-documenter"] = get_subagent_prompt(project_root, "cortex-documenter", workspace_layout=layout)

    return prompts
