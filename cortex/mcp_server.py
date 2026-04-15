import sys
import logging
from typing import List, Optional
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Warning: 'mcp' package not found. Run 'pip install mcp'", file=sys.stderr)
    sys.exit(1)

from cortex.core import AgentMemory

# Redirect any stdout logs or print statements from other libraries to stderr
# because stdout is used by the MCP protocol to communicate with the host IDE.
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

mcp = FastMCP("CortexMemory")
memory = AgentMemory()

@mcp.tool()
def cortex_search(query: str, top_k: int = 5) -> str:
    """
    Search the Cortex hybrid memory for a specific query.
    Returns results from episodic memory (past PRs/chats) and semantic memory (Markdown docs).
    """
    try:
        logging.info(f"Executing cortex_search for query: {query}")
        result = memory.retrieve(query, top_k=top_k)
        return result.to_prompt()
    except Exception as e:
        return f"Error executing cortex_search: {e}"

@mcp.tool()
def cortex_context(files: List[str], pr_title: Optional[str] = None) -> str:
    """
    Get rich context from Cortex enriched with semantic concepts and past memory.
    Use this proactively before modifying files to understand past architectural decisions.
    """
    try:
        logging.info(f"Executing cortex_context for files: {files}")
        context = memory.enrich(changed_files=files, pr_title=pr_title)
        return context.to_prompt()
    except Exception as e:
        return f"Error executing cortex_context: {e}"

@mcp.tool()
def cortex_sync_vault() -> str:
    """
    Force a semantic index sync with the current state of the local obsidian vault.
    Run this after pulling new changes, or if you created new documentation.
    """
    try:
        logging.info("Executing cortex_sync_vault")
        docs_indexed = memory.sync_vault()
        return f"Vault successfully synced. {docs_indexed} documents indexed."
    except Exception as e:
        return f"Error syncing vault: {e}"

def start_mcp():
    """Starts the FastMCP server blocking stdin/stdout."""
    logging.info("Starting Cortex MCP Server...")
    mcp.run()

if __name__ == "__main__":
    start_mcp()
