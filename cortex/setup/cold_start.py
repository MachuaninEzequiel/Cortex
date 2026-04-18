"""
cortex.setup.cold_start
-------------------------
Cold Start bootstrap for Cortex memory system.

Provides 3-layer fallback when no memories exist:
  Layer 1: Pre-seed from existing vault documentation
  Layer 2: Git history mining (extract decisions from commits)
  Layer 3: README fallback (project intro from README.md)

This ensures agents always have context, even on first use.
"""

from __future__ import annotations

import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Layer 1: Pre-seed from vault
# ---------------------------------------------------------------------------

def layer1_preseed_vault(
    vault_path: str | Path,
    memory_store: Any,
) -> list[str]:
    """
    Layer 1: Pre-seed memories from existing vault documentation.
    
    Scans the vault for existing markdown files and harvests
    metadata (titles, tags, links) to create initial memories.

    Args:
        vault_path: Path to the markdown vault directory.
        memory_store: EpisodicMemoryStore instance.

    Returns:
        List of memory IDs created.
    """
    import json
    from pathlib import Path
    
    vault = Path(vault_path)
    if not vault.exists():
        logger.debug("Vault does not exist, skipping Layer 1")
        return []
    
    memory_ids: list[str] = []
    
    # Find all markdown files
    md_files = list(vault.rglob("*.md"))
    if not md_files:
        logger.debug("No markdown files in vault, skipping Layer 1")
        return []
    
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            
            # Extract title from first heading or filename
            title = _extract_title(content, md_file.stem)
            
            # Extract tags from frontmatter
            tags = _extract_tags(content, md_file)
            
            # Extract links (for relationship mapping)
            links = _extract_links(content)
            
            # Create memory entry
            memory_content = (
                f"Vault doc: {title}\n"
                f"File: {md_file.relative_to(vault)}\n"
                f"Tags: {', '.join(tags) if tags else 'none'}\n"
                f"Links to: {', '.join(links) if links else 'none'}\n"
                f"\n{content[:500]}..."
            )
            
            entry = memory_store.add(
                content=memory_content,
                memory_type="vault_doc",
                tags=["vault"] + tags,
                files=[str(md_file.relative_to(vault))],
            )
            memory_ids.append(entry.id)
            logger.debug(f"Pre-seeded: {md_file.name}")
            
        except Exception as e:
            logger.debug(f"Failed to pre-seed {md_file}: {e}")
    
    return memory_ids


def _extract_title(content: str, fallback: str) -> str:
    """Extract title from markdown content."""
    # Look for first # heading
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return fallback


def _extract_tags(content: str, md_file: Path) -> list[str]:
    """Extract tags from YAML frontmatter."""
    import re
    
    # Check for frontmatter tags
    tag_pattern = re.compile(r"tags:\s*\[([^\]]+)\]", re.MULTILINE)
    match = tag_pattern.search(content)
    if match:
        tags_str = match.group(1)
        return [t.strip().strip("'\"") for t in tags_str.split(",")]
    
    # Also infer from filename
    filename_tags = []
    name_parts = md_file.stem.lower().replace("-", " ").replace("_", " ").split()
    for part in name_parts:
        if part not in ["readme", "doc", "index", "notes"]:
            filename_tags.append(part)
    
    return filename_tags[:5]


def _extract_links(content: str) -> list[str]:
    """Extract wiki-links from markdown."""
    wiki_link_pattern = re.compile(r"\[\[([^\]|]+)", re.MULTILINE)
    return wiki_link_pattern.findall(content)


# ---------------------------------------------------------------------------
# Layer 2: Git history mining
# ---------------------------------------------------------------------------

def layer2_git_history(
    project_root: str | Path,
    memory_store: Any,
    max_commits: int = 50,
) -> list[str]:
    """
    Layer 2: Mine git history for architectural decisions and patterns.
    
    Analyzes recent commits to extract:
    - Commit messages (as decision/context log)
    - Modified files (for co-occurrence)
    - Authors and timestamps (for patterns)

    Args:
        project_root: Root directory of the project.
        memory_store: EpisodicMemoryStore instance.
        max_commits: Maximum commits to analyze.

    Returns:
        List of memory IDs created.
    """
    from pathlib import Path
    
    project = Path(project_root)
    memory_ids: list[str] = []
    
    # Get recent commits
    commits = _get_git_commits(project, max_commits)
    if not commits:
        logger.debug("No git history found, skipping Layer 2")
        return []
    
    # Analyze commits in chunks (create memories per day/week)
    commit_chunks = _chunk_commits_by_time(commits)
    
    for chunk in commit_chunks:
        if len(chunk) < 2:
            continue
            
        # Extract info from chunk
        dates = []
        files_touched = set()
        messages = []
        
        for commit in chunk:
            dates.append(commit.get("date", ""))
            files_touched.update(commit.get("files", []))
            msg = commit.get("message", "")
            if msg:
                messages.append(msg[:100])
        
        if not messages:
            continue
        
        # Classify the chunk
        chunk_type = _classify_commit_chunk(chunk)
        
        # Create memory content
        file_list = list(files_touched)[:20]
        content = (
            f"Git session: {len(chunk)} commits\n"
            f"Type: {chunk_type}\n"
            f"Files: {', '.join(file_list)}\n"
            f"Changes:\n" + "\n".join(f"  - {m}" for m in messages[:5])
        )
        
        entry = memory_store.add(
            content=content,
            memory_type=chunk_type,
            tags=["git_history", chunk_type],
            files=file_list,
        )
        memory_ids.append(entry.id)
        logger.debug(f"Mined git session: {len(chunk)} commits as {chunk_type}")
    
    # Also extract individual architectural decisions
    for commit in commits[:20]:
        msg = commit.get("message", "")
        if _is_architectural_decision(msg):
            entry = memory_store.add(
                content=f"Decision: {msg}\nFile: {commit.get('files', [])}\n",
                memory_type="decision",
                tags=["adr", "decision", "git"],
                files=commit.get("files", [])[:10],
            )
            memory_ids.append(entry.id)
    
    return memory_ids


def _get_git_commits(project: Path, max_count: int) -> list[dict]:
    """Get commits from git log."""
    commits: list[dict] = []
    
    try:
        result = subprocess.run(
            ["git", "log", f"-{max_count * 2}", "--format=%H|%an|%ai|%s", "--name-only"],
            cwd=project,
            capture_output=True,
            text=True,
            timeout=15,
        )
        
        current_commit = None
        files = []
        
        for line in result.stdout.split("\n"):
            line = line.rstrip()
            if not line:
                continue
            
            if "|" in line and current_commit is None:
                # New commit
                parts = line.split("|")
                if len(parts) >= 4:
                    current_commit = {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                        "files": [],
                    }
            elif current_commit is not None and not line.startswith("commit"):
                # File path
                if line and not line.startswith("Author:"):
                    current_commit["files"].append(line)
            elif line.startswith("commit "):
                # New commit starting, save previous
                if current_commit and current_commit.get("files"):
                    commits.append(current_commit)
                current_commit = None
                files = []
        
        # Add last commit
        if current_commit and current_commit.get("files"):
            commits.append(current_commit)
            
    except Exception as e:
        logger.debug(f"Git log failed: {e}")
    
    return commits


def _chunk_commits_by_time(commits: list[dict]) -> list[list[dict]]:
    """Group commits by time proximity (same day = same chunk)."""
    if not commits:
        return []
    
    chunks: list[list[dict]] = []
    current_chunk: list[dict] = []
    current_date = ""
    
    for commit in commits:
        date = commit.get("date", "")[:10]  # Just YYYY-MM-DD
        if date != current_date and current_chunk:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = []
        current_chunk.append(commit)
        current_date = date
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def _classify_commit_chunk(commits: list[dict]) -> str:
    """Classify the type of work in a commit chunk."""
    all_messages = " ".join(c.get("message", "").lower() for c in commits)
    
    if any(word in all_messages for word in ["fix", "bug", "error", "hotfix"]):
        return "bugfix"
    elif any(word in all_messages for word in ["feat", "add", "new", "implement"]):
        return "feature"
    elif any(word in all_messages for word in ["refactor", "cleanup", "simplify"]):
        return "refactor"
    elif any(word in all_messages for word in ["test", "spec"]):
        return "test"
    elif any(word in all_messages for word in ["docs", "doc", "readme"]):
        return "documentation"
    else:
        return "chore"


def _is_architectural_decision(message: str) -> bool:
    """Check if a commit message indicates an architectural decision."""
    decision_keywords = [
        "refactor", "architecture", "design", "decision", "adr",
        "migrate", "upgrade", "breaking", "api change",
        "introduce", "remove", "deprecate",
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in decision_keywords)


# ---------------------------------------------------------------------------
# Layer 3: README fallback
# ---------------------------------------------------------------------------

def layer3_readme_fallback(
    project_root: str | Path,
    memory_store: Any,
) -> list[str]:
    """
    Layer 3: Use README.md as fallback context.
    
    If no vault and no git history, use the project's README.md
    to create initial context.

    Args:
        project_root: Root directory of the project.
        memory_store: EpisodicMemoryStore instance.

    Returns:
        List of memory IDs created.
    """
    from pathlib import Path
    
    project = Path(project_root)
    memory_ids: list[str] = []
    
    # Look for README files
    readme_candidates = ["README.md", "README.txt", "README.rst", "readme.md"]
    readme_path = None
    
    for candidate in readme_candidates:
        path = project / candidate
        if path.exists():
            readme_path = path
            break
    
    if not readme_path:
        logger.debug("No README found, skipping Layer 3")
        return []
    
    try:
        content = readme_path.read_text(encoding="utf-8")
        
        # Extract key sections
        sections = _parse_readme_sections(content)
        
        # Create memory
        memory_content = (
            f"Project: {sections.get('title', readme_path.stem)}\n"
            f"Description: {sections.get('description', '')[:300]}\n"
            f"Installation: {sections.get('installation', '')[:200]}\n"
            f"Usage: {sections.get('usage', '')[:200]}\n"
            f"\n--- Full README ---\n"
            f"{content[:800]}..."
        )
        
        tags = ["readme", "project_intro"]
        if sections.get("tech_stack"):
            tags.extend(sections["tech_stack"])
        
        entry = memory_store.add(
            content=memory_content,
            memory_type="project_intro",
            tags=tags,
            files=[str(readme_path.relative_to(project))],
        )
        memory_ids.append(entry.id)
        logger.debug(f"Loaded README: {readme_path.name}")
        
    except Exception as e:
        logger.debug(f"Failed to parse README: {e}")
    
    return memory_ids


def _parse_readme_sections(content: str) -> dict[str, str]:
    """Parse README into sections."""
    import re
    
    sections: dict[str, str] = {}
    
    # Title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        sections["title"] = title_match.group(1).strip()
    
    # Description (first paragraph after title)
    desc_match = re.search(r"^#.+\n\n(.+?)(?:\n\n##|\Z)", content, re.DOTALL | re.MULTILINE)
    if desc_match:
        sections["description"] = desc_match.group(1).strip()[:500]
    
    # Installation
    install_match = re.search(r"^##\s+Installation\s*\n\n(.+?)(?:\n\n##|\Z)", content, re.DOTALL | re.MULTILINE)
    if install_match:
        sections["installation"] = install_match.group(1).strip()[:300]
    
    # Usage
    usage_match = re.search(r"^##\s+Usage\s*\n\n(.+?)(?:\n\n##|\Z)", content, re.DOTALL | re.MULTILINE)
    if usage_match:
        sections["usage"] = usage_match.group(1).strip()[:300]
    
    # Tech stack (look for badges or known tech names)
    tech_patterns = [
        "python", "javascript", "typescript", "go", "rust", "java",
        "react", "vue", "angular", "next", "svelte",
        "node", "fastapi", "django", "flask", "express",
        "postgresql", "mysql", "mongodb", "redis", "docker",
    ]
    content_lower = content.lower()
    tech_stack = [t for t in tech_patterns if t in content_lower]
    if tech_stack:
        sections["tech_stack"] = tech_stack
    
    return sections


# ---------------------------------------------------------------------------
# Orchestrator: Run all layers
# ---------------------------------------------------------------------------

def run_cold_start(
    project_root: str | Path,
    memory_store: Any,
    vault_path: str | Path | None = None,
    git_depth: int = 50,
) -> dict:
    """
    Run all Cold Start layers as complementary context sources.
    
    Returns:
        Dict with results from each layer.
    """
    from pathlib import Path
    import subprocess
    
    project = Path(project_root)
    vault = Path(vault_path) if vault_path else project / "vault"
    
    results: dict = {
        "layer1_preseed": [],
        "layer2_git_history": [],
        "layer3_readme": [],
        "total": 0,
        "success": False,
        "warnings": []
    }
    
    # Si ya hay memoria, no hacemos nada
    if memory_store.count() > 0:
        results["success"] = True
        return results
    
    # Capa 1: Vault (Siempre se intenta)
    if vault.exists():
        results["layer1_preseed"] = layer1_preseed_vault(vault, memory_store)
    
    # Capa 2: Git History (Resiliente)
    try:
        is_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=project, capture_output=True, text=True
        ).returncode == 0
        
        if is_git:
            results["layer2_git_history"] = layer2_git_history(project, memory_store, max_commits=git_depth)
            if not results["layer2_git_history"]:
                 results["warnings"].append("Git repo detectado pero no se pudieron extraer commits.")
        else:
            results["warnings"].append("No se detecto repositorio Git. Saltando Capa 2.")
    except Exception:
        results["warnings"].append("Error al intentar acceder a Git. Saltando Capa 2.")
    
    # Capa 3: README (Siempre se intenta)
    results["layer3_readme"] = layer3_readme_fallback(project, memory_store)
    
    results["total"] = (
        len(results["layer1_preseed"]) 
        + len(results["layer2_git_history"]) 
        + len(results["layer3_readme"])
    )
    results["success"] = results["total"] > 0
    
    return results
