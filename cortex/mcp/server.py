import asyncio
import os
import re
import shutil
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
        self._task_results: dict[str, dict[str, str]] = {}
        
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
                            "query": {"type": "string", "description": "Consulta de contexto."},
                            "changed_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Archivos modificados para enriquecer el contexto.",
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Palabras clave opcionales para complementar la consulta.",
                            },
                            "pr_title": {
                                "type": "string",
                                "description": "Titulo opcional del PR o tarea actual.",
                            },
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="cortex_sync_ticket",
                    description="Paso obligatorio de cortex-sync. Inyecta el pedido actual del usuario junto con contexto historico similar recuperado por ONNX/hybrid retrieval para preparar una spec.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_request": {
                                "type": "string",
                                "description": "Pedido textual actual del usuario en la terminal.",
                            },
                            "changed_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Archivos ya identificados para el ticket actual.",
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Palabras clave opcionales para reforzar la recuperacion.",
                            },
                            "title_hint": {
                                "type": "string",
                                "description": "Titulo corto opcional para orientar la spec.",
                            },
                            "top_k": {
                                "type": "integer",
                                "default": 5,
                            },
                        },
                        "required": ["user_request"]
                    }
                ),
                types.Tool(
                    name="cortex_delegate_task",
                    description="Delegar una tarea a un subagente de Cortex (SDDwork flow).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent": {"type": "string", "description": "Nombre del subagente (ej. cortex-code-explorer)."},
                            "task": {"type": "string", "description": "La tarea a realizar."},
                            "timeout_seconds": {
                                "type": "integer",
                                "default": 120,
                                "description": "Timeout opcional para subagentes lentos.",
                            },
                        },
                        "required": ["agent", "task"]
                    }
                ),
                types.Tool(
                    name="cortex_delegate_batch",
                    description="Lanzar una ronda de subagentes y devolver sus resultados consolidados. Usala desde cortex-SDDwork para orquestar explorer/planner/implementer/reviewer/tester/documenter.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "agent": {"type": "string"},
                                        "task": {"type": "string"},
                                    },
                                    "required": ["agent", "task"],
                                },
                                "description": "Lista de tareas a delegar en paralelo para una misma ronda.",
                            },
                            "timeout_seconds": {
                                "type": "integer",
                                "default": 120,
                                "description": "Timeout opcional aplicado a cada subagente de la ronda.",
                            },
                        },
                        "required": ["tasks"]
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
                    ctx = self._enrich_context(arguments)
                    return [types.TextContent(type="text", text=ctx.to_prompt_format())]

                elif name == "cortex_sync_ticket":
                    sync_context = self._build_sync_ticket_context(arguments)
                    return [types.TextContent(type="text", text=sync_context)]

                elif name == "cortex_delegate_task":
                    agent = arguments.get("agent", "")
                    task = arguments.get("task", "")
                    timeout_seconds = arguments.get("timeout_seconds")
                    result = await self._delegate_task(agent, task, timeout_seconds=timeout_seconds)
                    return [types.TextContent(type="text", text=result)]

                elif name == "cortex_delegate_batch":
                    tasks = arguments.get("tasks", [])
                    timeout_seconds = arguments.get("timeout_seconds")
                    result = await self._delegate_batch(tasks, timeout_seconds=timeout_seconds)
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
                    agent = str(arguments.get("agent", "")).strip()
                    if not agent:
                        return [types.TextContent(type="text", text="Error: el nombre del subagente es obligatorio.")]
                    return [types.TextContent(type="text", text=self._get_task_result(agent))]

                return [types.TextContent(type="text", text=f"Herramienta desconocida: {name}")]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error ejecutando {name}: {str(e)}")]

    @staticmethod
    def _extract_query_keywords(query: str) -> list[str]:
        """Build lightweight keywords from a free-form context query."""
        words = re.findall(r"\b[a-zA-Z][\w./-]{2,}\b", query.lower())
        return list(dict.fromkeys(words))[:10]

    def _enrich_context(self, arguments: dict[str, Any]) -> EnrichedContext:
        """Convert MCP arguments into a useful context enrichment request."""
        query = str(arguments.get("query", "")).strip()
        changed_files = self._normalize_string_list(arguments.get("changed_files", []))
        keywords = self._normalize_string_list(arguments.get("keywords", []))

        if not keywords and query:
            keywords = self._extract_query_keywords(query)

        pr_title = str(arguments.get("pr_title", "")).strip() or query or None

        return self.memory.enrich(
            changed_files=changed_files,
            keywords=keywords,
            pr_title=pr_title,
        )

    @staticmethod
    def _normalize_string_list(values: Any) -> list[str]:
        return [
            str(value).strip()
            for value in values or []
            if str(value).strip()
        ]

    def _extract_candidate_files(self, query: str) -> list[str]:
        project_root = self.project_root.resolve()
        candidates: list[str] = []

        for raw_path in re.findall(r"\b[\w./\\-]+\.[A-Za-z0-9]+\b", query):
            normalized = raw_path.strip().replace("\\", "/")
            path = Path(normalized)
            if path.is_absolute():
                continue

            candidate = (project_root / path).resolve()
            try:
                candidate.relative_to(project_root)
            except ValueError:
                continue

            if candidate.is_file():
                candidates.append(normalized)

        return list(dict.fromkeys(candidates))

    def _build_sync_ticket_context(self, arguments: dict[str, Any]) -> str:
        user_request = str(arguments.get("user_request", "")).strip()
        if not user_request:
            raise ValueError("user_request es obligatorio para cortex_sync_ticket.")

        changed_files = self._normalize_string_list(arguments.get("changed_files", []))
        if not changed_files:
            changed_files = self._extract_candidate_files(user_request)

        keywords = self._normalize_string_list(arguments.get("keywords", []))
        if not keywords:
            keywords = self._extract_query_keywords(user_request)

        title_hint = str(arguments.get("title_hint", "")).strip() or user_request
        top_k = int(arguments.get("top_k", 5) or 5)

        related = self.memory.retrieve(user_request, top_k=top_k)
        enriched = self.memory.enrich(
            changed_files=changed_files,
            keywords=keywords,
            pr_title=title_hint,
            top_k=top_k,
        )

        changed_files_text = ", ".join(changed_files) if changed_files else "(sin archivos inferidos)"
        keywords_text = ", ".join(keywords) if keywords else "(sin keywords)"

        sections = [
            "## Ticket actual",
            user_request,
            "",
            "## Scope detectado",
            changed_files_text,
            "",
            "## Keywords",
            keywords_text,
            "",
            "## Contexto historico similar (Vault + memoria episodica)",
            related.to_prompt(),
            "",
            "## Contexto enriquecido del proyecto",
            enriched.to_prompt_format(),
        ]
        return "\n".join(sections)

    def _resolve_delegate_timeout(self, agent_name: str, timeout_seconds: Any) -> int:
        if timeout_seconds is not None:
            try:
                return max(30, int(timeout_seconds))
            except (TypeError, ValueError):
                return 120

        defaults = {
            "cortex-code-implementer": 300,
            "cortex-code-tester": 300,
            "cortex-documenter": 180,
        }
        return defaults.get(agent_name, 120)

    async def _delegate_task(self, agent_name: str, task: str, timeout_seconds: Any = None) -> str:
        agent_name = agent_name.strip()
        task = task.strip()
        if not agent_name:
            return "Error: el nombre del subagente es obligatorio."
        if not task:
            return "Error: la tarea a delegar no puede estar vacia."

        subagent_path = self.project_root / ".cortex" / "subagents" / f"{agent_name}.md"
        if not subagent_path.exists():
            subagent_path = Path.home() / ".config" / "opencode" / "subagents" / f"{agent_name}.md"
            if not subagent_path.exists():
                message = f"Error: Subagente '{agent_name}' no encontrado."
                self._store_task_result(agent_name, "error", message, task)
                return message

        opencode = shutil.which("opencode")
        if not opencode:
            message = "Error: no se encontro el ejecutable 'opencode' en PATH."
            self._store_task_result(agent_name, "error", message, task)
            return message

        try:
            cmd = [opencode, "run", "--agent", agent_name, "--message", task]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            effective_timeout = self._resolve_delegate_timeout(agent_name, timeout_seconds)
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=effective_timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                message = f"Error: el subagente '{agent_name}' excedio el timeout de {effective_timeout}s."
                self._store_task_result(agent_name, "timeout", message, task)
                return message

            stdout_text = stdout.decode("utf-8", errors="replace").strip()
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            if process.returncode != 0:
                message = stderr_text or f"Error critico en subagente {agent_name}."
                self._store_task_result(agent_name, "error", message, task)
                return message

            message = stdout_text or f"Subagente '{agent_name}' finalizo sin salida textual."
            self._store_task_result(agent_name, "success", message, task)
            return message
        except Exception as e:
            message = f"Error al invocar subagente via CLI: {str(e)}"
            self._store_task_result(agent_name, "error", message, task)
            return message

    async def _delegate_batch(self, tasks: list[dict[str, Any]], timeout_seconds: Any = None) -> str:
        if not isinstance(tasks, list) or not tasks:
            return "Error: tasks debe contener al menos una delegacion."

        normalized_tasks: list[tuple[str, str]] = []
        for index, item in enumerate(tasks, start=1):
            if not isinstance(item, dict):
                return f"Error: la tarea #{index} no es un objeto valido."

            agent = str(item.get("agent", "")).strip()
            task = str(item.get("task", "")).strip()
            if not agent or not task:
                return f"Error: la tarea #{index} debe incluir agent y task."
            normalized_tasks.append((agent, task))

        results = await asyncio.gather(
            *[
                self._delegate_task(agent, task, timeout_seconds=timeout_seconds)
                for agent, task in normalized_tasks
            ]
        )

        lines = ["Ronda de subagentes completada."]
        has_failures = False
        for (agent, task), message in zip(normalized_tasks, results, strict=False):
            stored = self._task_results.get(agent, {})
            status = stored.get("status", "unknown")
            if status != "success":
                has_failures = True

            lines.extend(
                [
                    "",
                    f"Subagente: {agent}",
                    f"Estado: {status}",
                    f"Tarea: {task}",
                    "Resultado:",
                    message,
                ]
            )

        if has_failures:
            lines.extend(
                [
                    "",
                    "Resultado global: revisa los subagentes con error o timeout antes de avanzar a la siguiente ronda.",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "Resultado global: todos los subagentes de la ronda finalizaron correctamente.",
                ]
            )

        return "\n".join(lines)

    def _store_task_result(self, agent_name: str, status: str, message: str, task: str) -> None:
        self._task_results[agent_name] = {
            "status": status,
            "message": message,
            "task": task,
        }

    def _get_task_result(self, agent_name: str) -> str:
        result = self._task_results.get(agent_name)
        if not result:
            return f"No hay resultados guardados para el subagente '{agent_name}'."
        return (
            f"Subagente: {agent_name}\n"
            f"Estado: {result['status']}\n"
            f"Tarea: {result['task']}\n"
            f"Resultado:\n{result['message']}"
        )

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
