from __future__ import annotations

import logging
import sys
from typing import List, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - dependency issue, handled at runtime
    print("Warning: 'mcp' package not found. Run 'pip install mcp'", file=sys.stderr)
    sys.exit(1)

from cortex.core import AgentMemory

# Stdout is reserved for the MCP protocol.
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

mcp = FastMCP("CortexMemory")
_memory: AgentMemory | None = None


def _get_memory() -> AgentMemory:
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory


@mcp.tool()
def cortex_search(query: str, top_k: int = 5) -> str:
    """
    Search the Cortex hybrid memory for a specific query.
    """
    try:
        logging.info("Executing cortex_search for query: %s", query)
        result = _get_memory().retrieve(query, top_k=top_k)
        return result.to_prompt()
    except Exception as exc:
        return f"Error executing cortex_search: {exc}"


@mcp.tool()
def cortex_context(files: List[str], pr_title: Optional[str] = None) -> str:
    """
    Get enriched Cortex context for the current implementation scope.
    """
    try:
        logging.info("Executing cortex_context for files: %s", files)
        context = _get_memory().enrich(changed_files=list(files), pr_title=pr_title)
        return context.to_prompt_format()
    except Exception as exc:
        return f"Error executing cortex_context: {exc}"


@mcp.tool()
def cortex_save_session(
    title: str,
    spec_summary: str,
    changes_made: Optional[List[str]] = None,
    files_touched: Optional[List[str]] = None,
    key_decisions: Optional[List[str]] = None,
    next_steps: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Persist a Cortex session note and index it back into the vault/memory system.
    """
    try:
        logging.info("Executing cortex_save_session for title: %s", title)
        path = _get_memory().save_session_note(
            title=title,
            spec_summary=spec_summary,
            changes_made=list(changes_made or []),
            files_touched=list(files_touched or []),
            key_decisions=list(key_decisions or []),
            next_steps=list(next_steps or []),
            tags=list(tags or []),
            sync_vault=True,
        )
        return f"Session persisted in Cortex: {path}"
    except Exception as exc:
        return f"Error executing cortex_save_session: {exc}"


@mcp.tool()
def cortex_create_spec(
    title: str,
    goal: str,
    requirements: Optional[List[str]] = None,
    files_in_scope: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    acceptance_criteria: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Persist an implementation specification into the Cortex vault.
    """
    try:
        logging.info("Executing cortex_create_spec for title: %s", title)
        path = _get_memory().create_spec_note(
            title=title,
            goal=goal,
            requirements=list(requirements or []),
            files_in_scope=list(files_in_scope or []),
            constraints=list(constraints or []),
            acceptance_criteria=list(acceptance_criteria or []),
            tags=list(tags or []),
            sync_vault=True,
        )
        return f"Specification persisted in Cortex: {path}"
    except Exception as exc:
        return f"Error executing cortex_create_spec: {exc}"


@mcp.tool()
def cortex_sync_vault() -> str:
    """
    Force a semantic index sync with the current state of the local vault.
    """
    try:
        logging.info("Executing cortex_sync_vault")
        docs_indexed = _get_memory().sync_vault()
        return f"Vault successfully synced. {docs_indexed} documents indexed."
    except Exception as exc:
        return f"Error syncing vault: {exc}"


def start_mcp() -> None:
    """Start the FastMCP server on stdin/stdout."""
    logging.info("Starting Cortex MCP Server...")
    mcp.run()


if __name__ == "__main__":
    start_mcp()
