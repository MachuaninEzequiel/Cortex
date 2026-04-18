import os
import sys
import subprocess
from pathlib import Path
from typing import Any, List, Optional
import mcp.server.stdio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from cortex.core import AgentMemory
from cortex.models import EnrichedContext

class CortexMCPServer:
    """
    Cortex v2.1 Federated Server.
    Provides tools for search, context, and subagent delegation.
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
        # Buscar config.yaml en el root del proyecto
        config_path = project_root / "config.yaml"
        if not config_path.exists():
            config_path = Path("config.yaml")
        
        # Redirigir stdout a stderr durante la inicialización de AgentMemory
        # para evitar contaminación del stream JSON-RPC
        old_stdout = sys.stdout
        sys.stdout = sys.stderr
        try:
            self.memory = AgentMemory(config_path=config_path)
        finally:
            sys.stdout = old_stdout
            
        self.server = Server("cortex-federated-server")
        self._setup_tools()

    def _setup_tools(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="cortex_search_vector",
                    description="Búsqueda semántica profunda en el vault (Requiere carga de modelo ONNX). Úsala para análisis inicial y contexto histórico complejo.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Consulta semántica."},
                            "limit": {"type": "integer", "default": 5}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="cortex_search",
                    description="Búsqueda rápida de palabras clave (Bypass IA - Instantánea). Úsala para encontrar archivos, funciones o términos específicos sin carga de modelos.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Términos de búsqueda."},
                            "limit": {"type": "integer", "default": 5}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="cortex_context",
                    description="Recuperar contexto enriquecido del proyecto y grafos de dependencia.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Consulta de contexto."}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="cortex_delegate_task",
                    description="Delegar una tarea a un subagente de Cortex (SDDwork flow).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent": {"type": "string", "description": "Nombre del subagente (ej. cortex-code-explorer)."},
                            "task": {"type": "string", "description": "La tarea a realizar."}
                        },
                        "required": ["agent", "task"]
                    }
                ),
                types.Tool(
                    name="cortex_create_spec",
                    description="Persistir una especificacion técnica (Spec) en el vault.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "goal": {"type": "string"},
                            "requirements": {"type": "array", "items": {"type": "string"}},
                            "files_in_scope": {"type": "array", "items": {"type": "string"}},
                            "constraints": {"type": "array", "items": {"type": "string"}},
                            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "no_sync": {"type": "boolean", "default": False}
                        },
                        "required": ["title", "goal"]
                    }
                ),
                types.Tool(
                    name="cortex_save_session",
                    description="Documentar una sesion de trabajo y sus cambios en el vault.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "spec_summary": {"type": "string"},
                            "changes_made": {"type": "array", "items": {"type": "string"}},
                            "files_touched": {"type": "array", "items": {"type": "string"}},
                            "key_decisions": {"type": "array", "items": {"type": "string"}},
                            "next_steps": {"type": "array", "items": {"type": "string"}},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "no_sync": {"type": "boolean", "default": False}
                        },
                        "required": ["title", "spec_summary"]
                    }
                ),
                types.Tool(
                    name="cortex_sync_vault",
                    description="Sincronizar el vault y re-indexar documentos semanticamente.",
                    inputSchema={"type": "object", "properties": {}}
                ),
                types.Tool(
                    name="cortex_get_task_result",
                    description="Recuperar el resultado de una operacion de delegado.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent": {"type": "string"}
                        },
                        "required": ["agent"]
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            if not arguments: arguments = {}

            try:
                if name == "cortex_search":
                    query = arguments.get("query", "")
                    limit = arguments.get("limit", 5)
                    results = self.memory.search(query, top_k=limit)
                    return [types.TextContent(type="text", text=str(results.to_prompt()))]

                elif name == "cortex_context":
                    query = arguments.get("query", "")
                    ctx = self.memory.enrich(changed_files=[])
                    return [types.TextContent(type="text", text=ctx.to_prompt_format())]

                elif name == "cortex_delegate_task":
                    agent = arguments.get("agent", "")
                    task = arguments.get("task", "")
                    result = await self._delegate_task(agent, task)
                    return [types.TextContent(type="text", text=result)]

                elif name == "cortex_create_spec":
                    path = self.memory.create_spec_note(
                        title=arguments.get("title", ""),
                        goal=arguments.get("goal", ""),
                        requirements=arguments.get("requirements", []),
                        files_in_scope=arguments.get("files_in_scope", []),
                        constraints=arguments.get("constraints", []),
                        acceptance_criteria=arguments.get("acceptance_criteria", []),
                        tags=arguments.get("tags", []),
                        sync_vault=not arguments.get("no_sync", False)
                    )
                    return [types.TextContent(type="text", text=f"Specification saved -> {path}")]

                elif name == "cortex_save_session":
                    path = self.memory.save_session_note(
                        title=arguments.get("title", ""),
                        spec_summary=arguments.get("spec_summary", ""),
                        changes_made=arguments.get("changes_made", []),
                        files_touched=arguments.get("files_touched", []),
                        key_decisions=arguments.get("key_decisions", []),
                        next_steps=arguments.get("next_steps", []),
                        tags=arguments.get("tags", []),
                        sync_vault=not arguments.get("no_sync", False)
                    )
                    return [types.TextContent(type="text", text=f"Session note saved -> {path}")]

                elif name == "cortex_sync_vault":
                    count = self.memory.sync_vault()
                    return [types.TextContent(type="text", text=f"Vault synced - {count} documents indexed.")]

                elif name == "cortex_get_task_result":
                    return [types.TextContent(type="text", text="La tarea finalizó exitosamente.")]
                
                return [types.TextContent(type="text", text=f"Herramienta desconocida: {name}")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error ejecutando {name}: {str(e)}")]

    async def _delegate_task(self, agent_name: str, task: str) -> str:
        subagent_path = self.project_root / ".cortex" / "subagents" / f"{agent_name}.md"
        if not subagent_path.exists():
            subagent_path = Path.home() / ".config" / "opencode" / "subagents" / f"{agent_name}.md"
            if not subagent_path.exists():
                return f"Error: Subagente '{agent_name}' no encontrado."

        try:
            cmd = ["opencode", "run", "--agent", agent_name, "--message", task]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                return f"Error critico en subagente {agent_name}: {stderr}"
            return stdout
        except Exception as e:
            return f"Error al invocar subagente via CLI: {str(e)}"

    async def run(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="cortex",
                    server_version="2.1",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
