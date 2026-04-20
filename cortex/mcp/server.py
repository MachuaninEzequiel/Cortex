import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
import mcp.server.stdio
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from cortex.core import AgentMemory
from cortex.models import EnrichedContext

# Configure logging for MCP tool call tracking
logger = logging.getLogger(__name__)

class CortexMCPServer:
    """
    Cortex v3.0 Engine Server.
    Provides tools for search, context, and memory.
    
    This is the Cortex Engine - a passive MCP server that exposes memory and
    semantic search capabilities. Delegation is now handled by IDE-native tools
    (Task, runSubagent, etc.) configured via profile injection.
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
        # Capa 1: Sistema de tracking de herramientas llamadas para logging y validación
        self._tool_call_history: list[dict[str, Any]] = []
        self._called_tools: set[str] = set()
        
        # Configurar logging para archivo
        log_dir = project_root / ".cortex" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"mcp_calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stderr)
            ]
        )
        
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
        
        logger.info(f"Cortex MCP Server inicializado. Log file: {log_file}")

    def _log_tool_call(self, tool_name: str, arguments: dict[str, Any], result: str | None = None) -> None:
        """
        Capa 1: Logging genérico de todas las llamadas a herramientas.
        Registra timestamp, herramienta, argumentos y resultado para auditoría completa.
        """
        timestamp = datetime.now().isoformat()
        
        # Registrar en el set de herramientas llamadas
        self._called_tools.add(tool_name)
        
        # Crear entrada de historial
        log_entry = {
            "timestamp": timestamp,
            "tool": tool_name,
            "arguments": arguments,
            "result": result if result else "pending"
        }
        self._tool_call_history.append(log_entry)
        
        # Log al archivo y stderr
        logger.info(f"TOOL_CALL: {tool_name} | args: {arguments}")
        
        if result:
            logger.info(f"TOOL_RESULT: {tool_name} | {result[:200]}...")  # Primeros 200 chars

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
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            if not arguments: arguments = {}

            # Capa 1: Logging genérico al inicio de cada llamada
            self._log_tool_call(name, arguments)

            try:
                result_text = None
                
                if name == "cortex_search":
                    query = arguments.get("query", "")
                    limit = arguments.get("limit", 5)
                    results = self.memory.search(query, top_k=limit)
                    result_text = str(results.to_prompt())
                    self._log_tool_call(name, arguments, result_text)
                    return [types.TextContent(type="text", text=result_text)]

                elif name == "cortex_context":
                    ctx = self._enrich_context(arguments)
                    result_text = ctx.to_prompt_format()
                    self._log_tool_call(name, arguments, result_text)
                    return [types.TextContent(type="text", text=result_text)]

                elif name == "cortex_sync_ticket":
                    sync_context = self._build_sync_ticket_context(arguments)
                    result_text = sync_context
                    self._log_tool_call(name, arguments, result_text)
                    return [types.TextContent(type="text", text=result_text)]


                elif name == "cortex_create_spec":
                    # Capa 1: Validación técnica - rechazar si cortex_sync_ticket no fue llamado
                    if "cortex_sync_ticket" not in self._called_tools:
                        error_msg = (
                            "❌ **VIOLACIÓN DE GOBERNANZA**: cortex_create_spec fue llamado sin "
                            "ejecutar primero cortex_sync_ticket.\n\n"
                            "Según las reglas de Cortex v2.0, cortex-sync DEBE llamar a "
                            "cortex_sync_ticket como PRIMER paso para inyectar contexto histórico "
                            "vía ONNX/hybrid retrieval antes de crear cualquier spec.\n\n"
                            "Por favor, corrige el flujo:\n"
                            "1. Llama a cortex_sync_ticket con el pedido del usuario\n"
                            "2. Luego llama a cortex_create_spec\n\n"
                            f"Herramientas llamadas en esta sesión: {', '.join(sorted(self._called_tools))}"
                        )
                        logger.error(f"GOVERNANCE_VIOLATION: cortex_create_spec called without cortex_sync_ticket. Tools called: {self._called_tools}")
                        return [types.TextContent(type="text", text=error_msg)]
                    
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
                    result_text = f"Specification saved -> {path}"
                    self._log_tool_call(name, arguments, result_text)
                    return [types.TextContent(type="text", text=result_text)]

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
                    result_text = f"Session note saved -> {path}"
                    self._log_tool_call(name, arguments, result_text)
                    return [types.TextContent(type="text", text=result_text)]

                elif name == "cortex_sync_vault":
                    count = self.memory.sync_vault()
                    result_text = f"Vault synced - {count} documents indexed."
                    self._log_tool_call(name, arguments, result_text)
                    return [types.TextContent(type="text", text=result_text)]


                error_msg = f"Herramienta desconocida: {name}"
                self._log_tool_call(name, arguments, error_msg)
                return [types.TextContent(type="text", text=error_msg)]
            except Exception as e:
                error_msg = f"Error ejecutando {name}: {str(e)}"
                self._log_tool_call(name, arguments, error_msg)
                logger.exception(f"Exception in tool call: {name}")
                return [types.TextContent(type="text", text=error_msg)]

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
