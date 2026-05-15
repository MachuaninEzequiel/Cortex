import asyncio
import collections
import concurrent.futures
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from cortex.autopilot.mcp_tools import AutopilotMCPTools
from cortex.autopilot.service import AutopilotService
from cortex.core import AgentMemory
from cortex.models import EnrichedContext
from cortex.security.paths import PathSecurityError, resolve_safe
from cortex.workspace.layout import WorkspaceLayout

# Configure logging for MCP tool call tracking
logger = logging.getLogger(__name__)

class CortexMCPServer:
    """
    Cortex v3.0 Engine Server.
    Provides tools for search, context, and memory.

    This is the Cortex Engine - a passive MCP server that exposes memory and
    semantic search capabilities. Delegation is now handled by IDE-native tools
    (Task, runSubagent, etc.) configured via profile injection.

    Fase 1 — Capa 1 del plan multi-IDE & MCP hardening:
    Cada tool call corre en un ``ThreadPoolExecutor`` con timeout enforced.
    Sin este aislamiento, una llamada bloqueante (subprocess colgado, carga
    de modelo, IO masivo) bloqueaba el event loop async — exactamente el
    incidente del 2026-05-15.
    """

    # Timeout en segundos por tool. Default 30s; ajustar solo para tools
    # que sabemos que son legitimamente mas lentas (ej. carga del modelo
    # ONNX la primera vez).
    _TOOL_TIMEOUT_DEFAULT: float = 30.0
    _TOOL_TIMEOUTS: dict[str, float] = {
        "cortex_search_vector": 60.0,   # primera invocacion carga ONNX (~10MB)
        "cortex_sync_vault": 120.0,     # indexacion masiva de disco
        "cortex_ping": 5.0,             # health check debe ser FAST FAIL
    }

    # Server version expuesta por ``cortex_ping`` y por InitializationOptions.
    # Bump manual cuando el contrato del MCP cambie de forma incompatible.
    SERVER_VERSION: str = "2.2"

    # Threshold: el server se considera "starting" durante los primeros N
    # segundos post-init. Despues del threshold, status pasa a "ok" o
    # "degraded" segun haya o no errores recientes.
    _STARTUP_GRACE_SECONDS: float = 2.0

    # Tope de caracteres del mensaje de error guardado en last_error_seen.
    # Suficiente para diagnosticar sin riesgo de incluir un traceback completo
    # con paths sensibles.
    _ERROR_MESSAGE_MAX_CHARS: int = 200

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._layout = WorkspaceLayout.discover(project_root)

        # Capa 1: Sistema de tracking de herramientas llamadas para logging y validación
        self._tool_call_history: list[dict[str, Any]] = []
        self._called_tools: set[str] = set()

        # Fase 2: tracking para cortex_ping.
        # ``_startup_time`` permite calcular uptime; ``_error_history`` mantiene
        # los ultimos 10 errores capturados por el dispatcher (timeouts o
        # exceptions). El client puede consultar ``cortex_ping`` para detectar
        # estado degradado antes de gastar tiempo en operaciones costosas.
        self._startup_time: datetime = datetime.now()
        self._error_history: collections.deque[dict[str, Any]] = collections.deque(maxlen=10)
        
        # Configurar logging para archivo.
        #
        # En modo stdio (el unico transport del MCP server actualmente), escribir
        # logs a sys.stderr es un bug latente: si el cliente MCP no drena el pipe
        # stderr rapidamente, el siguiente ``logger.info`` se bloquea por
        # contrapresion del pipe — y bloquea el handler async del server entero.
        # Esto causo el incidente del 2026-05-15 (subagente colgado 14 minutos +
        # MCP desconectandose mid-operacion).
        #
        # Por defecto solo escribimos a archivo. Escape hatch para debugging:
        # ``CORTEX_MCP_LOG_TO_STDERR=1`` reactiva el StreamHandler en stderr.
        log_dir = self._layout.logs_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"mcp_calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        handlers: list[logging.Handler] = [logging.FileHandler(log_file)]
        if os.environ.get("CORTEX_MCP_LOG_TO_STDERR") == "1":
            handlers.append(logging.StreamHandler(sys.stderr))

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
        )
        
        # Buscar config usando WorkspaceLayout
        config_path = self._layout.config_path
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
        
        # Autopilot tools (Phase 5)
        self._autopilot_service = AutopilotService.from_project_root(project_root)
        self._autopilot_tools = AutopilotMCPTools(self._autopilot_service)
        
        # Executor para aislar tool calls bloqueantes del event loop async.
        # max_workers=4 por default; configurable via CORTEX_MCP_MAX_WORKERS.
        max_workers = int(os.environ.get("CORTEX_MCP_MAX_WORKERS", "4") or "4")
        self._executor: concurrent.futures.ThreadPoolExecutor = (
            concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, max_workers),
                thread_name_prefix="cortex-mcp-",
            )
        )

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
        
        # Log al FileHandler configurado en __init__ (Capa 2: stderr solo
        # bajo CORTEX_MCP_LOG_TO_STDERR=1 para evitar bloqueo del pipe stdio).
        logger.info(f"TOOL_CALL: {tool_name} | args: {arguments}")
        
        if result:
            logger.info(f"TOOL_RESULT: {tool_name} | {result[:200]}...")  # Primeros 200 chars

    def _setup_tools(self):
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            return [
                types.Tool(
                    name="cortex_ping",
                    description=(
                        "Health check rapido del MCP server. Devuelve JSON con "
                        "{status, version, uptime_seconds, indices_loaded, "
                        "models_loaded, last_error_seen}. Latencia objetivo <50ms. "
                        "Pensado para que los agentes verifiquen disponibilidad "
                        "ANTES de gastar tiempo y contexto en operaciones costosas. "
                        "Si status != 'ok', abortar la operacion con error claro al usuario; "
                        "NO degradar features, NO hacer fallback manual."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
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
                    description=(
                        "Búsqueda rápida de palabras clave (Bypass IA - Instantánea). "
                        "Úsala para encontrar archivos, funciones o términos específicos sin carga de modelos. "
                        "Acepta filtros estructurales opcionales (doc_type, scope, status, tags, max_age_days, "
                        "strict): si alguno es informado, el resultado se construye con ContextEnricher en lugar "
                        "del RRF crudo (mismo backend que `cortex docs search`)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Términos de búsqueda."},
                            "limit": {"type": "integer", "default": 5},
                            "doc_type": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filtrar por DocType slug (adr, runbook, ...).",
                            },
                            "exclude_doc_type": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Excluir DocTypes.",
                            },
                            "status": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filtrar por frontmatter status (accepted, draft, ...).",
                            },
                            "tag": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Items deben contener TODOS los tags.",
                            },
                            "tag_any": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Items deben contener al menos uno de estos tags.",
                            },
                            "scope": {
                                "type": "string",
                                "enum": ["local", "enterprise", "all"],
                                "default": "local",
                            },
                            "max_age_days": {
                                "type": "integer",
                                "description": "Descartar items más antiguos que N días.",
                            },
                            "project_id": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filtro multi-tenant por origin_project_id.",
                            },
                            "strict": {
                                "type": "boolean",
                                "default": False,
                                "description": "Descartar items sin doc_type cuando doc_type filtra.",
                            }
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
                            "no_sync": {"type": "boolean", "default": False},
                            "handoff": {
                                "type": "boolean",
                                "default": False,
                                "description": "Marca la sesion como handoff cross-session (Tripartita Refinada).",
                            },
                            "blockers": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Bloqueos abiertos que el siguiente agente debe resolver.",
                            },
                            "verified_state": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Hechos verificados contra el diff o tests reales.",
                            },
                            "unverified_claims": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Afirmaciones sin verificar que el siguiente agente debe re-chequear.",
                            },
                            "suggested_skills": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Skills/subagents recomendados para retomar el trabajo.",
                            },
                        },
                        "required": ["title", "spec_summary"]
                    }
                ),
                # ----------------------------------------------------------
                # Tripartita Refinada — Handoff & Verification tools
                # Plan 02 §1-§2. MCP-only (sin contraparte CLI por diseno).
                # ----------------------------------------------------------
                types.Tool(
                    name="cortex_validate_handoff",
                    description=(
                        "Validate a structured agent handoff (YAML). Use this between "
                        "subagents to enforce the cortex.handoff.AgentHandoff schema. "
                        "Returns OK with normalized fields or an error message detailing "
                        "the schema violations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "handoff_yaml": {
                                "type": "string",
                                "description": "YAML text matching AgentHandoff schema.",
                            },
                            "expected_agent": {
                                "type": "string",
                                "description": "(Optional) Assert the handoff's agent field matches this value.",
                            },
                        },
                        "required": ["handoff_yaml"],
                    },
                ),
                types.Tool(
                    name="cortex_verify_session_claims",
                    description=(
                        "Verify session claims against the actual git diff. Returns a "
                        "structured breakdown of verified / asserted / contradicted "
                        "claims that the documenter can use to fill the confidence field."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "claims": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of claims to verify.",
                            },
                            "base_branch": {
                                "type": "string",
                                "description": "Branch to diff against (default: main).",
                            },
                            "files_to_check": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional file allowlist to scope verification.",
                            },
                        },
                        "required": ["claims"],
                    },
                ),
                types.Tool(
                    name="cortex_import_hu",
                    description="Importar una historia o work item externo en modo read-only.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "external_id": {"type": "string", "description": "Clave del item externo, por ejemplo PROJ-123."},
                            "provider": {"type": "string", "default": "jira"},
                            "no_remember": {"type": "boolean", "default": False},
                        },
                        "required": ["external_id"]
                    }
                ),
                types.Tool(
                    name="cortex_get_hu",
                    description="Obtener la nota local ya importada de una HU o work item.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string", "description": "ID local o externo, por ejemplo PROJ-123."},
                        },
                        "required": ["item_id"]
                    }
                ),
                types.Tool(
                    name="cortex_sync_vault",
                    description="Sincronizar el vault y re-indexar documentos semanticamente.",
                    inputSchema={"type": "object", "properties": {}}
                ),
                types.Tool(
                    name="cortex_autopilot_start",
                    description="Start a new Autopilot session.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_root": {"type": "string"},
                            "workspace_root": {"type": "string"},
                            "mode": {"type": "string", "default": "assist"},
                            "user_request": {"type": "string"},
                            "title_hint": {"type": "string"},
                        },
                        "required": ["project_root", "workspace_root"],
                    }
                ),
                types.Tool(
                    name="cortex_autopilot_preflight",
                    description="Run Autopilot preflight detection for a session.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "user_request": {"type": "string"},
                            "changed_files": {"type": "array", "items": {"type": "string"}},
                            "git_diff_stat": {"type": "string"},
                        },
                        "required": ["session_id"],
                    }
                ),
                types.Tool(
                    name="cortex_autopilot_checkpoint",
                    description="Record an Autopilot checkpoint.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "summary": {"type": "string"},
                            "files_at_checkpoint": {"type": "array", "items": {"type": "string"}},
                            "verified": {"type": "boolean", "default": False},
                        },
                        "required": ["session_id", "summary"],
                    }
                ),
                types.Tool(
                    name="cortex_autopilot_finish",
                    description="Finish an Autopilot session and optionally persist a draft.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "auto": {"type": "boolean", "default": False},
                        },
                        "required": ["session_id"],
                    }
                ),
                types.Tool(
                    name="cortex_autopilot_status",
                    description="Get the current Autopilot status.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                        },
                    }
                ),
                # NOTA (Fase 5 plan multi-IDE & MCP hardening, 2026-05-15):
                # Los tools experimentales `cortex_delegate_task`,
                # `cortex_delegate_batch` y `cortex_get_task_result` fueron
                # ELIMINADOS. Razon: estaban hardcoded a `opencode run` via
                # subprocess y devolvian no-op silencioso en cualquier otro
                # IDE — el bug exacto del incidente del 2026-05-15.
                #
                # La delegacion a subagentes ahora es responsabilidad NATIVA
                # del IDE (Task tool en Claude Code, mode: subagent en
                # opencode, secuencial single-agent en codex). Ver
                # `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md`
                # seccion 1 para detalles por IDE.
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
            if not arguments:
                arguments = {}

            # Capa 1: Logging generico al inicio de cada llamada
            self._log_tool_call(name, arguments)

            # Capa 1 (defensive): cada tool call corre en un thread del executor
            # con timeout enforced. Si el handler bloquea (subprocess colgado,
            # carga ONNX, IO masivo), el event loop async sigue libre — el
            # cliente recibe error de timeout en lugar de un servidor muerto.
            timeout = self._TOOL_TIMEOUTS.get(name, self._TOOL_TIMEOUT_DEFAULT)
            # ``get_running_loop`` en lugar de ``get_event_loop``: este ultimo
            # esta deprecated en Python 3.10+ cuando se llama desde dentro
            # de una corutina. Como ``handle_call_tool`` ES una corutina
            # (decorada con async), siempre hay un loop corriendo y
            # ``get_running_loop`` es la API correcta.
            loop = asyncio.get_running_loop()
            try:
                result_text = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor, self._dispatch_tool_sync, name, arguments
                    ),
                    timeout=timeout,
                )
            except TimeoutError:
                result_text = (
                    f"❌ Tool '{name}' excedio el timeout ({timeout}s). "
                    "El handler quedo bloqueado — el server continua operando."
                )
                self._register_error(name, f"timeout after {timeout}s")
                self._log_tool_call(name, arguments, result_text)
            except Exception as e:
                result_text = f"Error ejecutando {name}: {str(e)}"
                self._register_error(name, str(e))
                self._log_tool_call(name, arguments, result_text)
                logger.exception(f"Exception in tool call: {name}")
            return [types.TextContent(type="text", text=result_text)]

    def _dispatch_tool_sync(self, name: str, arguments: dict[str, Any]) -> str:
        """Sync dispatcher de tool calls.

        Vive en un thread del executor (no bloquea el event loop). Cada branch
        invoca el handler especifico y retorna el texto a devolver al cliente.

        Errores propagan al caller (``handle_call_tool``), que los captura
        y los formatea como ``TextContent`` con marca de error.
        """
        if name == "cortex_ping":
            result_text = self._ping_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_search":
            result_text = self._search_text_dispatch(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_search_vector":
            result_text = self._search_vector_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_context":
            result_text = self._context_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_sync_ticket":
            result_text = self._build_sync_ticket_context(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_create_spec":
            # Governance guard + spec creation estan centralizados en
            # ``_create_spec_text``. NO duplicar el guard aqui: el
            # mensaje canonico vive en ``_GOVERNANCE_VIOLATION_MESSAGE``
            # y el flujo lo prueba ``tests/unit/test_mcp_server.py``.
            result_text = self._create_spec_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_save_session":
            result_text = self._save_session_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_validate_handoff":
            result_text = self._validate_handoff_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_verify_session_claims":
            result_text = self._verify_session_claims_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_import_hu":
            result_text = self._import_hu_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_get_hu":
            result_text = self._get_hu_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_sync_vault":
            count = self.memory.sync_vault()
            result_text = f"Vault synced - {count} documents indexed."
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_autopilot_start":
            result_text = self._autopilot_tools.start(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_autopilot_preflight":
            result_text = self._autopilot_tools.preflight(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_autopilot_checkpoint":
            result_text = self._autopilot_tools.checkpoint(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_autopilot_finish":
            result_text = self._autopilot_tools.finish(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_autopilot_status":
            result_text = self._autopilot_tools.status(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        # Tools cortex_delegate_task / cortex_delegate_batch /
        # cortex_get_task_result eliminados en Fase 5 del plan multi-IDE
        # & MCP hardening (2026-05-15). La delegacion a subagentes ahora
        # es responsabilidad nativa del IDE — ver
        # `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md` seccion 5.

        error_msg = f"Herramienta desconocida: {name}"
        self._log_tool_call(name, arguments, error_msg)
        return error_msg

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
            try:
                candidate = resolve_safe(project_root, normalized)
            except PathSecurityError:
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

    def _search_text(self, query: str, limit: int = 5) -> str:
        results = self.memory.retrieve(query, top_k=limit)
        return str(results.to_prompt())

    def _search_vector_text(self, arguments: dict[str, Any]) -> str:
        """Handler para ``cortex_search_vector``: forces the semantic/vector path.

        Difiere de ``cortex_search`` en que NUNCA cae al modo ContextEnricher
        estructural — siempre invoca el path retrieval con ``use_embeddings=True``.
        Pensado para casos donde el caller quiere busqueda semantica pura
        aunque el costo de cargar el modelo ONNX sea mayor.
        """
        query = str(arguments.get("query", "") or "")
        limit = int(arguments.get("limit", 5) or 5)
        results = self.memory.retrieve(query, top_k=limit, use_embeddings=True)
        return str(results.to_prompt())

    _STRUCTURAL_KEYS = (
        "doc_type",
        "exclude_doc_type",
        "status",
        "tag",
        "tag_any",
        "max_age_days",
        "project_id",
        "strict",
    )

    def _search_text_dispatch(self, arguments: dict[str, Any]) -> str:
        """Route ``cortex_search`` to legacy RRF or structural enricher path."""
        query = arguments.get("query", "")
        limit = int(arguments.get("limit", 5) or 5)

        scope = arguments.get("scope", "local") or "local"
        structural = any(arguments.get(k) for k in self._STRUCTURAL_KEYS) or scope != "local"
        if not structural:
            return self._search_text(query, limit)

        from cortex.cli._search_filters import build_enrichment_filters_from_cli
        from cortex.context_enricher.config import ContextEnricherConfig
        from cortex.context_enricher.enricher import ContextEnricher
        from cortex.models import WorkContext

        try:
            filters = build_enrichment_filters_from_cli(
                doc_type=arguments.get("doc_type") or [],
                exclude_doc_type=arguments.get("exclude_doc_type") or [],
                status=arguments.get("status") or [],
                tag=arguments.get("tag") or [],
                tag_any=arguments.get("tag_any") or [],
                scope=scope,
                max_age_days=arguments.get("max_age_days"),
                project_id=arguments.get("project_id") or [],
                strict=bool(arguments.get("strict", False)),
            )
        except ValueError as exc:
            return f"cortex_search: invalid filter — {exc}"

        enricher = ContextEnricher(
            episodic=self.memory.episodic,
            semantic=self.memory.semantic,
            config=ContextEnricherConfig(),
        )
        work = WorkContext(
            source="manual",
            changed_files=[],
            keywords=str(query).split(),
            search_queries=[str(query)],
        )
        ctx = enricher.enrich(work, top_k=limit, filters=filters)
        return ctx.to_prompt_format()

    def _context_text(self, arguments: dict[str, Any]) -> str:
        return self._enrich_context(arguments).to_prompt_format()

    # Mensaje canónico de violación del guard de gobernanza.
    # Usado tanto desde ``handle_call_tool`` como desde ``_create_spec_text``
    # para que el contrato sea único, testeable y libre de mojibake.
    # NO duplicar la cadena en otra parte del archivo.
    _GOVERNANCE_VIOLATION_MESSAGE = (
        "❌ **VIOLACIÓN DE GOBERNANZA**: cortex_create_spec fue llamado sin "
        "ejecutar primero cortex_sync_ticket.\n\n"
        "Según las reglas de Cortex v2.0, cortex-sync DEBE llamar a "
        "cortex_sync_ticket como PRIMER paso para inyectar contexto histórico "
        "vía ONNX/hybrid retrieval antes de crear cualquier spec.\n\n"
        "Por favor, corrige el flujo:\n"
        "1. Llama a cortex_sync_ticket con el pedido del usuario\n"
        "2. Luego llama a cortex_create_spec"
    )

    def _create_spec_text(self, arguments: dict[str, Any]) -> str:
        called_tools: set[str] = getattr(self, "_called_tools", set())
        if "cortex_sync_ticket" not in called_tools:
            logger.error(
                "GOVERNANCE_VIOLATION: cortex_create_spec called without "
                "cortex_sync_ticket. Tools called: %s",
                called_tools,
            )
            return (
                f"{self._GOVERNANCE_VIOLATION_MESSAGE}\n\n"
                f"Herramientas llamadas en esta sesión: "
                f"{', '.join(sorted(called_tools))}"
            )

        path = self.memory.create_spec_note(
            title=arguments.get("title", ""),
            goal=arguments.get("goal", ""),
            requirements=arguments.get("requirements", []),
            files_in_scope=arguments.get("files_in_scope", []),
            constraints=arguments.get("constraints", []),
            acceptance_criteria=arguments.get("acceptance_criteria", []),
            tags=arguments.get("tags", []),
            sync_vault=not arguments.get("no_sync", False),
        )
        return f"Specification saved -> {path}"

    def _save_session_text(self, arguments: dict[str, Any]) -> str:
        path = self.memory.save_session_note(
            title=arguments.get("title", ""),
            spec_summary=arguments.get("spec_summary", ""),
            changes_made=arguments.get("changes_made", []),
            files_touched=arguments.get("files_touched", []),
            key_decisions=arguments.get("key_decisions", []),
            next_steps=arguments.get("next_steps", []),
            tags=arguments.get("tags", []),
            sync_vault=not arguments.get("no_sync", False),
            handoff=bool(arguments.get("handoff", False)),
            blockers=list(arguments.get("blockers", []) or []),
            verified_state=list(arguments.get("verified_state", []) or []),
            unverified_claims=list(arguments.get("unverified_claims", []) or []),
            suggested_skills=list(arguments.get("suggested_skills", []) or []),
        )
        return f"Session note saved -> {path}"

    # ------------------------------------------------------------------
    # Tripartita Refinada — Handoff & Verification helpers (Plan 02)
    # ------------------------------------------------------------------

    def _validate_handoff_text(self, arguments: dict[str, Any]) -> str:
        """Validate a YAML handoff against the AgentHandoff schema."""
        from pydantic import ValidationError

        from cortex.handoff import AgentHandoff

        yaml_text = str(arguments.get("handoff_yaml", "") or "")
        expected_agent = arguments.get("expected_agent")
        if not yaml_text.strip():
            return "❌ handoff_yaml is required and must not be empty."
        try:
            handoff = AgentHandoff.from_yaml(yaml_text)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            return f"❌ Handoff schema violation:\n  {details}"
        except Exception as exc:
            return f"❌ Failed to parse YAML: {exc}"

        if expected_agent and handoff.agent != expected_agent:
            return (
                f"❌ Agent mismatch: handoff says '{handoff.agent}' but "
                f"expected '{expected_agent}'."
            )

        lines = [
            f"✅ Handoff validated for {handoff.agent} (status: {handoff.status})",
            f"  verified_claims: {len(handoff.verified_claims)}",
            f"  unverified_claims: {len(handoff.unverified_claims)}",
            f"  artifacts: {len(handoff.artifacts_produced)}",
            f"  context_for_next: {len(handoff.context_for_next)}",
        ]
        if handoff.suggested_adr:
            reason = handoff.suggested_adr_reason or "(no reason given)"
            lines.append(f"  ⚠ suggested ADR: {reason}")
        if handoff.suggested_context_terms:
            lines.append(
                f"  📚 CONTEXT.md terms: {', '.join(handoff.suggested_context_terms)}"
            )
        return "\n".join(lines)

    def _verify_session_claims_text(self, arguments: dict[str, Any]) -> str:
        """Cross-check claims against the current git diff (heuristic)."""
        from cortex.mcp._subprocess import git_branch_exists, safe_run

        claims = [str(c).strip() for c in (arguments.get("claims") or []) if str(c).strip()]
        base = str(arguments.get("base_branch") or "main")
        if not claims:
            return "❌ claims list is required and must not be empty."

        # Pre-validacion barata: si la rama base no existe, fallar rapido (~100ms)
        # en lugar de esperar el timeout completo del diff. Esto evita el caso
        # donde el adopter pasa "main" pero su repo usa "master" — sin esto, el
        # handler queda bloqueado 10s antes de devolver un error.
        if not git_branch_exists(base, cwd=self.project_root, timeout=2.0):
            return (
                f"❌ Base branch '{base}' does not exist in this repo. "
                f"Pass a valid branch via `base_branch` argument."
            )

        diff_result = safe_run(
            ["git", "diff", "--unified=0", base, "--"],
            cwd=self.project_root,
            timeout=10.0,
        )
        if not diff_result.ok:
            return f"❌ git diff against '{base}' failed: {diff_result.error}"
        diff_text = diff_result.stdout

        diff_lower = diff_text.lower()
        verified: list[str] = []
        asserted: list[str] = []
        contradicted: list[str] = []  # reserved for future negation heuristic

        for claim in claims:
            tokens = [
                t.lower()
                for t in claim.replace("_", " ").replace("/", " ").split()
                if len(t) > 3
            ]
            hits = sum(1 for t in tokens if t in diff_lower)
            if hits >= 2:
                verified.append(claim)
            else:
                asserted.append(claim)

        lines = [
            f"Verification of {len(claims)} claims against branch {base}:",
            f"  ✅ verified: {len(verified)}",
            f"  ⚠ asserted: {len(asserted)}",
            f"  ❌ contradicted: {len(contradicted)}",
        ]
        if verified:
            lines.append("\nVerified:")
            lines.extend(f"  - {c}" for c in verified)
        if asserted:
            lines.append("\nAsserted (no diff evidence):")
            lines.extend(f"  - {c}" for c in asserted)
        return "\n".join(lines)

    def _import_hu_text(self, arguments: dict[str, Any]) -> str:
        path = self.memory.import_work_item(
            arguments.get("external_id", ""),
            provider=arguments.get("provider", "jira"),
            remember=not arguments.get("no_remember", False),
        )
        return f"Tracked item imported -> {path}"

    def _get_hu_text(self, arguments: dict[str, Any]) -> str:
        path = self.memory.get_work_item_note(arguments.get("item_id", ""))
        return f"Tracked item note -> {path}"

    def _sync_vault_text(self) -> str:
        count = self.memory.sync_vault()
        return f"Vault synced - {count} documents indexed."


    async def run(self):
        try:
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
        finally:
            # Liberar workers del executor al terminar (cancel_futures evita
            # esperar tareas zombie si el cliente cerro el pipe abruptamente).
            self.shutdown()

    def _register_error(self, tool_name: str, error_msg: str) -> None:
        """Append a sanitized error to the rolling ``_error_history``.

        Llamado por ``handle_call_tool`` cuando captura timeout o exception.
        El mensaje se trunca a ``_ERROR_MESSAGE_MAX_CHARS`` para que el
        tracking nunca acumule tracebacks completos (que pueden contener
        paths sensibles del filesystem del adopter).
        """
        sanitized = (error_msg or "").strip()
        if len(sanitized) > self._ERROR_MESSAGE_MAX_CHARS:
            sanitized = sanitized[: self._ERROR_MESSAGE_MAX_CHARS - 3] + "..."
        self._error_history.append({
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "error": sanitized,
        })

    def _ping_text(self, arguments: dict[str, Any]) -> str:
        """Build the JSON response for ``cortex_ping``.

        Latencia objetivo <50ms p99: este metodo NO hace IO, NO toca disco,
        NO invoca subprocesos. Solo lee estado in-memory.

        Estructura del JSON devuelto:

        - ``status``: ``"ok" | "degraded" | "starting"``.
          * ``starting`` durante los primeros ``_STARTUP_GRACE_SECONDS``.
          * ``degraded`` si hay errores en ``_error_history``.
          * ``ok`` en cualquier otro caso.
        - ``version``: ``SERVER_VERSION`` (string).
        - ``uptime_seconds``: float, segundos desde init.
        - ``indices_loaded``: bool, ``self.memory`` existe y esta usable.
        - ``models_loaded``: lista de nombres de modelos actualmente cargados
          (vacia hasta que algun caller dispare carga lazy).
        - ``last_error_seen``: el ultimo error registrado, o ``null``.

        El argumento ``arguments`` se acepta por uniformidad con el
        dispatcher pero se ignora.
        """
        del arguments  # ping no acepta inputs
        now = datetime.now()
        uptime = (now - self._startup_time).total_seconds()

        # Determinar status
        if uptime < self._STARTUP_GRACE_SECONDS:
            status = "starting"
        elif len(self._error_history) > 0:
            status = "degraded"
        else:
            status = "ok"

        # Modelos cargados (lazy singletons)
        models_loaded: list[str] = []
        try:
            from cortex.embedders.onnx import OnnxEmbedder
            if OnnxEmbedder._onnx_fn is not None:
                models_loaded.append("onnx-embeddings")
        except Exception:
            # Si el import falla por algun motivo, no rompemos el ping.
            pass

        # Indices loaded: proxy = self.memory existe y no es None
        indices_loaded = getattr(self, "memory", None) is not None

        last_error = self._error_history[-1] if self._error_history else None

        payload = {
            "status": status,
            "version": self.SERVER_VERSION,
            "uptime_seconds": round(uptime, 3),
            "indices_loaded": indices_loaded,
            "models_loaded": models_loaded,
            "last_error_seen": last_error,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def shutdown(self) -> None:
        """Liberar recursos del server (executor + handlers de logging).

        Idempotente: llamarlo dos veces no rompe nada. Invocado automaticamente
        por ``run()`` en su ``finally`` block, y exponible para tests o
        embebido en otros runtimes que necesiten control explicito del cleanup.
        """
        executor = getattr(self, "_executor", None)
        if executor is not None:
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                # Cleanup defensivo: nunca propagar al caller.
                logger.exception("Error shutting down MCP executor")
            self._executor = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Subagent delegation layer (used by cortex-SDDwork flow)
    # ------------------------------------------------------------------

    def _get_layout(self) -> WorkspaceLayout:
        """Return the workspace layout, discovering it lazily if needed."""
        if not hasattr(self, "_layout") or self._layout is None:
            self._layout = WorkspaceLayout.discover(self.project_root)
        return self._layout

    # NOTA (Fase 5 plan multi-IDE & MCP hardening, 2026-05-15):
    # Los metodos privados ``_store_task_result``, ``_get_task_result``,
    # ``_delegate_task`` y ``_delegate_batch`` fueron eliminados junto con
    # los tools MCP `cortex_delegate_task`/`cortex_delegate_batch`/
    # `cortex_get_task_result` que los usaban.
    #
    # La logica de invocar subagents via subprocess (`opencode run --agent`)
    # estaba hardcoded a opencode y devolvia no-op silencioso en cualquier
    # otro IDE — el bug exacto que detono el incidente del 2026-05-15.
    # La delegacion ahora es responsabilidad nativa del IDE, no del MCP
    # server. Ver `docs/multi-ide-mcp-hardening/MATRIZ-NATIVA-IDES.md`
    # seccion 5 para detalles por IDE.
