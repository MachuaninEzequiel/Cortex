import asyncio
import collections
import concurrent.futures
import json
import logging
import os
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
from cortex.mcp.schemas import build_tool_definitions
from cortex.mcp.tools.documenter import DocumenterToolsMixin
from cortex.mcp.tools.search import SearchToolsMixin
from cortex.mcp.tools.sessions import SessionToolsMixin
from cortex.mcp.tools.workspace import WorkspaceToolsMixin
from cortex.workspace.layout import WorkspaceLayout

# Configure logging for MCP tool call tracking
logger = logging.getLogger(__name__)


class CortexMCPServer(
    SearchToolsMixin,
    DocumenterToolsMixin,
    SessionToolsMixin,
    WorkspaceToolsMixin,
):
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
        "cortex_search_vector": 60.0,  # primera invocacion carga ONNX (~10MB)
        "cortex_sync_vault": 120.0,  # indexacion masiva de disco
        "cortex_ping": 5.0,  # health check debe ser FAST FAIL
        # Spec creation legitimately spans: canonical write → semantic
        # index_file → session.open (git rev-parse + branch) → episodic
        # store (ONNX embed of the spec content). On cold ONNX or large
        # specs this can comfortably reach 30-45s; 60s is the budget
        # that survives a worst-case run without sacrificing the safety
        # of a finite timeout. See the May 2026 ``realestate`` incident.
        "cortex_create_spec": 60.0,
        # Documenter briefing runs the spec's verification_hooks as part of
        # the reconstruction (npm build, type-check, integration tests, etc.).
        # Each hook has its own ``timeout_seconds`` budget; on cold caches a
        # single ``npm ci && npm run build`` can take 60-90s by itself.
        # 180s is the budget that survives a typical spec with 3-4 hooks
        # without forcing the documenter to fall back to a manual
        # reconstruction. See the 2026-05-22 AppFutbol incident.
        "cortex_documenter_briefing": 180.0,
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

    # Ventana temporal para que un error pese en ``status`` de ``cortex_ping``.
    # Pasada esta ventana sin nuevos errores el server vuelve a reportar
    # ``ok`` (auto-recovery). Sin esto, un timeout aislado paralizaba al
    # documenter para siempre por el gate ``status != "ok" → abort``.
    # 300s (5 min) cubre re-intentos humanos razonables sin perpetuar un
    # estado sticky. ``_error_history`` sigue conservando los últimos 10
    # errores para audit, pero solo los recientes mueven el ``status``.
    # Ver docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/.
    _ERROR_RECENT_WINDOW_SECONDS: float = 300.0

    # Phase 09.A+: minimum seconds between ``cortex_emit_proposal`` and a
    # follow-up ``cortex_create_spec`` with proposal_confirmed=True. The
    # gap proxies "the user took a turn"; any tighter and the LLM could
    # fake the confirmation in the same turn. 2s is comfortably above
    # round-trip MCP latency yet well below human reaction time on the
    # acceptance message.
    _PROPOSAL_MIN_GAP_SECONDS: float = 2.0

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._layout = WorkspaceLayout.discover(project_root)

        # Capa 1: Sistema de tracking de herramientas llamadas para logging y validación
        self._tool_call_history: list[dict[str, Any]] = []
        self._called_tools: set[str] = set()

        # Phase 09.A+: timestamp of the most recent ``cortex_emit_proposal``
        # call. Used by ``_create_spec_text`` to enforce that a ``required``
        # proposal_mode + proposal_confirmed=True combo only succeeds when a
        # user turn has plausibly elapsed since the proposal was emitted.
        # See _PROPOSAL_MIN_GAP_SECONDS for the heuristic threshold.
        self._last_proposal_emitted_at: datetime | None = None

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
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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

    def _log_tool_call(
        self, tool_name: str, arguments: dict[str, Any], result: str | None = None
    ) -> None:
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
            "result": result if result else "pending",
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
            return build_tool_definitions()

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
                    loop.run_in_executor(self._executor, self._dispatch_tool_sync, name, arguments),
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

    # Tabla de ruteo nombre -> ruta de atributos. Congelada por
    # tests/unit/mcp/test_golden_contract.py (test_cada_nombre_llega_a_su_handler).
    # Sustituye al if-chain original (~35 ramas); el orden no es significativo.
    #
    # NOTA (Fase 5 plan multi-IDE & MCP hardening, 2026-05-15):
    # Los tools cortex_delegate_task / cortex_delegate_batch /
    # cortex_get_task_result fueron eliminados; la delegación a subagentes
    # es responsabilidad nativa del IDE.
    _TOOL_ROUTES: dict[str, tuple[str, ...]] = {
        "cortex_ping": ("_ping_text",),
        "cortex_search": ("_search_text_dispatch",),
        "cortex_search_vector": ("_search_vector_text",),
        "cortex_context": ("_context_text",),
        "cortex_sync_ticket": ("_build_sync_ticket_context",),
        "cortex_create_spec": ("_create_spec_text",),
        "cortex_emit_proposal": ("_emit_proposal_text",),
        "cortex_save_session": ("_save_session_text",),
        "cortex_validate_handoff": ("_validate_handoff_text",),
        "cortex_verify_session_claims": ("_verify_session_claims_text",),
        "cortex_import_hu": ("_import_hu_text",),
        "cortex_get_hu": ("_get_hu_text",),
        "cortex_autopilot_start": ("_autopilot_tools", "start"),
        "cortex_autopilot_preflight": ("_autopilot_tools", "preflight"),
        "cortex_autopilot_checkpoint": ("_autopilot_tools", "checkpoint"),
        "cortex_autopilot_finish": ("_autopilot_tools", "finish"),
        "cortex_autopilot_status": ("_autopilot_tools", "status"),
        "cortex_session_open": ("_session_open_text",),
        "cortex_session_checkpoint": ("_session_checkpoint_text",),
        "cortex_session_close": ("_session_close_text",),
        "cortex_session_status": ("_session_status_text",),
        "cortex_session_list": ("_session_list_text",),
        "cortex_finish_session": ("_finish_session_text",),
        "cortex_documenter_briefing": ("_documenter_briefing_text",),
        "cortex_close_session": ("_close_session_text",),
        "cortex_review_checkpoint": ("_session_review_checkpoint_text",),
        "write_design_note_canonical": ("_write_design_note_text",),
        "cortex_write_doc": ("_write_doc_text",),
        "cortex_self_review_note": ("_self_review_note_text",),
        "cortex_session_task_list": ("_session_task_list_text",),
        "cortex_session_task_update": ("_session_task_update_text",),
    }

    def _dispatch_tool_sync(self, name: str, arguments: dict[str, Any]) -> str:
        """Sync dispatcher de tool calls (tabla de rutas).

        Vive en un thread del executor (no bloquea el event loop). Cada ruta
        invoca el handler específico y retorna el texto a devolver al cliente.

        Errores propagan al caller (``handle_call_tool``), que los captura
        y los formatea como ``TextContent`` con marca de error.
        """
        # Ruta especial histórica: handler inline contra memory.sync_vault().
        if name == "cortex_sync_vault":
            count = self.memory.sync_vault()
            result_text = f"Vault synced - {count} documents indexed."
            self._log_tool_call(name, arguments, result_text)
            return result_text

        route = self._TOOL_ROUTES.get(name)
        if route is None:
            error_msg = f"Herramienta desconocida: {name}"
            self._log_tool_call(name, arguments, error_msg)
            return error_msg

        handler: Any = self
        for attr in route:
            handler = getattr(handler, attr)

        # Governance guard de create_spec: el mensaje canónico vive en
        # ``_create_spec_text`` (``_GOVERNANCE_VIOLATION_MESSAGE``); NO
        # duplicar acá. Lo prueba tests/unit/test_mcp_server.py.
        result_text = handler(arguments)
        self._log_tool_call(name, arguments, result_text)
        return result_text

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
        self._error_history.append(
            {
                "tool": tool_name,
                "timestamp": datetime.now().isoformat(),
                "error": sanitized,
            }
        )

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

        # Compute "recent errors" by filtering the rolling history against
        # ``_ERROR_RECENT_WINDOW_SECONDS``. ``_error_history`` keeps the last
        # 10 errors regardless of age (audit trail); ``status`` and
        # ``last_error_seen`` only reflect what happened recently. Without
        # this filter a single timeout latched the server in ``degraded``
        # forever — see AppFutbol Fase 3 incident.
        recent_errors: list[dict[str, Any]] = []
        for entry in self._error_history:
            try:
                entry_ts = datetime.fromisoformat(entry["timestamp"])
            except (KeyError, ValueError):
                continue
            age = (now - entry_ts).total_seconds()
            if age <= self._ERROR_RECENT_WINDOW_SECONDS:
                recent_errors.append(entry)

        # Determinar status
        if uptime < self._STARTUP_GRACE_SECONDS:
            status = "starting"
        elif recent_errors:
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

        last_error = recent_errors[-1] if recent_errors else None

        payload = {
            "status": status,
            "version": self.SERVER_VERSION,
            "uptime_seconds": round(uptime, 3),
            "indices_loaded": indices_loaded,
            "models_loaded": models_loaded,
            "last_error_seen": last_error,
            "recent_errors_count": len(recent_errors),
            "error_window_seconds": self._ERROR_RECENT_WINDOW_SECONDS,
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
