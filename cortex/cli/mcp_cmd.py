"""``cortex mcp-server`` — servidor MCP sobre stdio.

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer


def register(app) -> None:
    """Registra ``mcp-server`` y el alias oculto ``mcp-serve``."""

    @app.command(name="mcp-server")
    def mcp_server(
        project_root: str = typer.Option(None, "--project-root", help="Ruta absoluta al directorio del proyecto Cortex (donde está config.yaml)."),
        stdio: bool = typer.Option(True, "--stdio", help="Use stdio transport (required for IDE integration)."),
    ) -> None:
        """Start the Cortex v2.1 MCP Server (stdio transport).
    
        Para integración con IDEs (Cursor, VSCode, Claude Desktop), usa --project-root
        para especificar la ruta del proyecto Cortex cuando el cwd del IDE no coincide
        con el directorio del proyecto.
        """
    
        # Determinar el directorio raíz del proyecto
        root = Path(project_root) if project_root else Path.cwd()
    
        # Redirección temporal de stdout a stderr para proteger el handshake JSON-RPC
        old_stdout = sys.stdout
        sys.stdout = sys.stderr
    
        try:
            from cortex.mcp.server import CortexMCPServer
            server = CortexMCPServer(project_root=root)
        finally:
            sys.stdout = old_stdout
        
        asyncio.run(server.run())

    @app.command(name="mcp-serve", hidden=True)
    def mcp_serve_legacy() -> None:
        """Legacy alias for mcp-server."""
        mcp_server()
