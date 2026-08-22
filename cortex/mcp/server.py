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
from cortex.mcp.vault_adapter import PathVault
from cortex.models import EnrichedContext
from cortex.security.paths import PathSecurityError, resolve_safe
from cortex.session.models import CheckpointSource
from cortex.workspace.layout import WorkspaceLayout

# Single source of truth for the checkpoint ``source`` enum exposed to clients.
# Derived from :class:`CheckpointSource` so adding a new value in the canonical
# enum (e.g. ``cortex-code-designer`` in Pluggable Middle Phase 09.B) flows
# automatically into the JSON schema of ``cortex_session_checkpoint`` and into
# the runtime validator ``_VALID_CHECKPOINT_SOURCES``.
_CHECKPOINT_SOURCE_VALUES: tuple[str, ...] = tuple(s.value for s in CheckpointSource)

# Configure logging for MCP tool call tracking
logger = logging.getLogger(__name__)


def _serialize_reconstruction(out: Any) -> dict[str, Any]:
    """Serialize a :class:`ReconstructionOutput` to JSON-safe dict.

    Used by ``cortex_documenter_briefing``. Kept at module scope so it
    can be unit-tested without spinning up the full server. Paths are
    rendered as POSIX strings; ``LoadedSpec`` is reduced to the fields
    the skill needs for editorial decisions.
    """
    # ``VerificationHookResult`` (frozen, extra="forbid") doesn't carry the
    # ``required`` flag — that lives on the spec's ``VerificationHook``. We
    # derive it by name lookup so the briefing payload stays self-contained.
    # Default ``True`` on miss is conservative: an unmatched result is treated
    # as required so a failure isn't silently downgraded.
    _hook_required_by_name = {h.name: h.required for h in out.spec.verification_hooks}
    return {
        "session_id": out.session_id,
        "spec": {
            "path": out.spec.path.as_posix(),
            "title": out.spec.title,
            "goal": out.spec.goal,
            "files_in_scope": [p.as_posix() for p in out.spec.files_in_scope],
            "constraints": list(out.spec.constraints),
            "acceptance_criteria": list(out.spec.acceptance_criteria),
            "verification_hooks": [
                {
                    "name": h.name,
                    "command": h.command,
                    "required": h.required,
                    "success_criteria": h.success_criteria,
                    "timeout_seconds": h.timeout_seconds,
                }
                for h in out.spec.verification_hooks
            ],
        },
        "diff_text": out.diff_text,
        "diff_entries": [
            {"action": e.action, "path": e.path.as_posix()} for e in out.diff_entries
        ],
        "files_touched": [p.as_posix() for p in out.files_touched],
        "files_verified_by_git": [p.as_posix() for p in out.files_verified_by_git],
        "files_declared_only": [p.as_posix() for p in out.files_declared_only],
        "in_scope_files": [p.as_posix() for p in out.in_scope_files],
        "out_of_scope_files": [p.as_posix() for p in out.out_of_scope_files],
        "unimplemented_files": [p.as_posix() for p in out.unimplemented_files],
        "verification_results": [
            {
                "name": r.name,
                "command": r.command,
                "passed": r.passed,
                "exit_code": r.exit_code,
                "output": r.output,
                "duration_ms": r.duration_ms,
                "run_at": r.run_at.isoformat(),
                "required": _hook_required_by_name.get(r.name, True),
            }
            for r in out.verification_results
        ],
        "contradictions": [
            {
                "prior_record": c.prior_record,
                "current_claim": c.current_claim,
                "evidence": c.evidence,
                "severity": c.severity,
            }
            for c in out.contradictions
        ],
        "suggested_status": out.suggested_status.value,
        "suggested_adrs": [
            {
                "title": a.title,
                "rationale": a.rationale,
                "source_checkpoint_index": a.source_checkpoint_index,
                "evidence": a.evidence,
                "confidence": a.confidence,
            }
            for a in out.suggested_adrs
        ],
        "raw_checkpoints": [
            {
                "timestamp": cp.timestamp.isoformat(),
                "source": cp.source.value,
                "verified_claims": list(cp.verified_claims),
                "unverified_claims": list(cp.unverified_claims),
                "artifacts_touched": list(cp.artifacts_touched),
                "note": cp.note,
            }
            for cp in out.raw_checkpoints
        ],
        "end_commit": out.end_commit,
        "gitless": out.gitless,
    }


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
                            "limit": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
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
                            },
                        },
                        "required": ["query"],
                    },
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
                            "task_type": {
                                "type": ["string", "null"],
                                "description": (
                                    "Detected task type (question-only | docs-only | "
                                    "fast-code | deep-code | security | ambiguous | "
                                    "noop). When supplied, the server sizes the "
                                    "retrieval envelope via "
                                    "cortex.context_enricher.budget_resolver. "
                                    "Unknown values fall back to fast-code defaults."
                                ),
                                "default": None,
                            },
                            "complexity": {
                                "type": ["string", "null"],
                                "description": (
                                    "Reserved for Phase 09 complexity tuning. "
                                    "Currently accepted but unused."
                                ),
                                "default": None,
                            },
                        },
                        "required": ["query"],
                    },
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
                                # Tolerant input: accept either a JSON array of
                                # strings or a single comma-separated string.
                                # LLM clients sometimes serialize lists as CSV;
                                # the server splits and trims internally.
                                "oneOf": [
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "string"},
                                ],
                                "description": (
                                    "Archivos ya identificados para el ticket actual. "
                                    "Acepta array de strings o un string CSV (\"a.py,b.py\")."
                                ),
                            },
                            "keywords": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "string"},
                                ],
                                "description": (
                                    "Palabras clave opcionales para reforzar la recuperacion. "
                                    "Acepta array de strings o un string CSV (\"fase,roadmap\")."
                                ),
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
                        "required": ["user_request"],
                    },
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
                            "verification_hooks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "command": {"type": "string"},
                                        "required": {"type": "boolean", "default": True},
                                        "success_criteria": {
                                            "type": "string",
                                            "default": "exit code 0",
                                        },
                                        "timeout_seconds": {
                                            "type": "integer",
                                            "default": 300,
                                        },
                                    },
                                    "required": ["name", "command"],
                                },
                                "description": (
                                    "Executable commands that prove the work is "
                                    "done (Pluggable Middle, Phase 01). Optional "
                                    "for legacy compatibility; new specs should "
                                    "declare at least one."
                                ),
                            },
                            "no_sync": {"type": "boolean", "default": False},
                            "proposal_mode": {
                                "type": "string",
                                "enum": ["optional", "required", "skip"],
                                "default": "optional",
                                "description": (
                                    "Phase 09.A: gate on the cortex-sync proposal "
                                    "step. 'required' rejects the call unless "
                                    "proposal_confirmed is True."
                                ),
                            },
                            "proposal_confirmed": {
                                "type": "boolean",
                                "default": False,
                                "description": (
                                    "Phase 09.A: signal that the cortex-sync "
                                    "proposal has been acknowledged by the user."
                                ),
                            },
                        },
                        "required": ["title", "goal"],
                    },
                ),
                types.Tool(
                    name="cortex_emit_proposal",
                    description=(
                        "Phase 09.A+: emit a structured proposal as a Markdown "
                        "card visible to the user. After calling this tool, the "
                        "agent MUST end its turn — do NOT chain "
                        "cortex_create_spec in the same response. The server "
                        "enforces a minimum gap between emit_proposal and a "
                        "follow-up create_spec with proposal_confirmed=true, "
                        "rejecting fake same-turn confirmations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": (
                                    "Executive summary in 2-3 lines describing "
                                    "what is being proposed."
                                ),
                            },
                            "alternatives": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 5,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {
                                            "type": "string",
                                            "description": (
                                                "Short token (A, B, C, ...) the "
                                                "user can reference."
                                            ),
                                        },
                                        "description": {"type": "string"},
                                        "rejected_reason": {
                                            "type": "string",
                                            "default": "",
                                            "description": (
                                                "Empty for the recommended "
                                                "alternative; non-empty "
                                                "explanation for the rest."
                                            ),
                                        },
                                    },
                                    "required": ["id", "description"],
                                },
                            },
                            "recommendation_id": {
                                "type": "string",
                                "description": (
                                    "Id of the alternative the agent recommends. "
                                    "Must match an entry in 'alternatives'."
                                ),
                            },
                            "risks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                                "description": (
                                    "Optional list of risks/assumptions the "
                                    "user is implicitly accepting."
                                ),
                            },
                        },
                        "required": ["summary", "alternatives", "recommendation_id"],
                    },
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
                        "required": ["title", "spec_summary"],
                    },
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
                            "external_id": {
                                "type": "string",
                                "description": "Clave del item externo, por ejemplo PROJ-123.",
                            },
                            "provider": {"type": "string", "default": "jira"},
                            "no_remember": {"type": "boolean", "default": False},
                        },
                        "required": ["external_id"],
                    },
                ),
                types.Tool(
                    name="cortex_get_hu",
                    description="Obtener la nota local ya importada de una HU o work item.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "string",
                                "description": "ID local o externo, por ejemplo PROJ-123.",
                            },
                        },
                        "required": ["item_id"],
                    },
                ),
                types.Tool(
                    name="cortex_sync_vault",
                    description="Sincronizar el vault y re-indexar documentos semanticamente.",
                    inputSchema={"type": "object", "properties": {}},
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
                    },
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
                    },
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
                    },
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
                    },
                ),
                types.Tool(
                    name="cortex_autopilot_status",
                    description="Get the current Autopilot status.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                        },
                    },
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
                #
                # ── Pluggable Middle — Session primitive (Fase 00 / T0.7) ──
                types.Tool(
                    name="cortex_session_open",
                    description=(
                        "Open a new Session anchored on a spec. Normally invoked "
                        "automatically by cortex_create_spec; exposed here for "
                        "testing and for callers that manage Sessions manually. "
                        "Returns JSON with session_id, opened_at, start_commit, start_branch."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "spec_id": {
                                "type": "string",
                                "description": "Stem of the spec file (YYYY-MM-DD_<slug>).",
                            },
                            "spec_path": {
                                "type": "string",
                                "description": "Path to the persisted spec file.",
                            },
                            "spec_summary": {"type": "string", "default": ""},
                        },
                        "required": ["spec_id", "spec_path"],
                    },
                ),
                types.Tool(
                    name="cortex_session_checkpoint",
                    description=(
                        "Append a checkpoint to an OPEN Session. Used by the middle "
                        "(SDDwork, code-explorer, code-implementer) and by IDE hooks "
                        "to enrich the Session with verified/unverified claims, "
                        "artifacts touched and a short context note."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "source": {
                                "type": "string",
                                "enum": list(_CHECKPOINT_SOURCE_VALUES),
                            },
                            "verified_claims": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "unverified_claims": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "artifacts_touched": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "note": {"type": "string", "default": ""},
                        },
                        "required": ["session_id", "source"],
                    },
                ),
                types.Tool(
                    name="cortex_session_close",
                    description=(
                        "Close an OPEN Session into a terminal status. Captures HEAD "
                        "as end_commit and infers the mode (managed / observed / byo) "
                        "from the existing checkpoints. Returns JSON with session_id, "
                        "closed_at, end_commit, mode_inferred."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["closed", "handoff", "abandoned"],
                            },
                            "documenter_decision": {
                                "type": "string",
                                "enum": ["closed", "handoff", "abandoned"],
                            },
                            "session_note_path": {"type": ["string", "null"], "default": None},
                            "adrs_created": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                        },
                        "required": ["session_id", "status", "documenter_decision"],
                    },
                ),
                types.Tool(
                    name="cortex_session_status",
                    description=(
                        "Return the full SessionRecord for a session_id (or the "
                        "active session if session_id is omitted)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": ["string", "null"], "default": None},
                        },
                    },
                ),
                types.Tool(
                    name="cortex_finish_session",
                    description=(
                        "Close a Session: reconstruct context from the spec + diff "
                        "+ checkpoints, run the verification hooks declared in the "
                        "spec, persist the session note (and any ADR candidates), "
                        "and mark the underlying Session as CLOSED / HANDOFF / "
                        "ABANDONED. Returns JSON with session_note_path, "
                        "adrs_created, final_status, summary_text."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": ["string", "null"],
                                "description": "Session id to finish (default: active session).",
                                "default": None,
                            },
                            "intent": {
                                "type": "string",
                                "enum": ["auto", "handoff", "abandon"],
                                "default": "auto",
                                "description": (
                                    "Override the auto-suggested status. "
                                    "'auto' uses the reconstructor's verdict; "
                                    "'handoff' / 'abandon' force the closure."
                                ),
                            },
                            "reason": {
                                "type": ["string", "null"],
                                "default": None,
                                "description": "Required when intent != 'auto'.",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="cortex_documenter_briefing",
                    description=(
                        "Phase 09.A+ / May 2026 — READ-ONLY reconstruction "
                        "of a Session for the /cortex-documenter skill. "
                        "Runs the 8-step Reconstructor (sin persistir nada "
                        "ni cerrar la sesion). Returns ReconstructionOutput "
                        "JSON: spec, diff_text, diff_entries, "
                        "files_verified_by_git, files_declared_only, "
                        "files_touched (union), in_scope / out_of_scope / "
                        "unimplemented, verification_results, contradictions, "
                        "suggested_status, suggested_adrs, raw_checkpoints, "
                        "end_commit, gitless.\n\n"
                        "By default ``run_hooks=false`` — verification hooks "
                        "(``npm ci && build``, integration tests, etc.) NO se "
                        "ejecutan dentro del briefing porque pueden tardar "
                        "minutos y reventar el timeout del MCP. SDDwork "
                        "tipicamente ya los corrio antes de cerrar; si "
                        "necesitas verificarlos otra vez, pasá ``run_hooks=true`` "
                        "explicitamente y considera subir el timeout client-side."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": ["string", "null"],
                                "description": "Session id (default: active session).",
                                "default": None,
                            },
                            "run_hooks": {
                                "type": "boolean",
                                "default": False,
                                "description": (
                                    "If true, execute the spec's "
                                    "verification_hooks during the "
                                    "reconstruction. Default false to keep "
                                    "the briefing fast and avoid MCP timeouts "
                                    "on heavy hooks (npm build, tests, etc.)."
                                ),
                            },
                        },
                    },
                ),
                types.Tool(
                    name="cortex_close_session",
                    description=(
                        "Phase 09.A+ / May 2026 — close an OPEN Session "
                        "without re-running the reconstructor. Intended "
                        "as the FINAL step of the /cortex-documenter skill "
                        "after it has called cortex_documenter_briefing "
                        "and persisted the session note + ADRs (via the "
                        "write_*_note_canonical tools). Records final "
                        "status, an optional note_path, and any ADR paths "
                        "the skill created. Returns JSON with the closed "
                        "SessionRecord summary."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": ["string", "null"],
                                "description": "Session id (default: active session).",
                                "default": None,
                            },
                            "status": {
                                "type": "string",
                                "enum": ["closed", "handoff", "abandoned"],
                                "description": (
                                    "Terminal status the documenter decided. "
                                    "Use 'handoff' when the work is incomplete "
                                    "or verification hooks failed; 'abandoned' "
                                    "when the work was discarded; 'closed' "
                                    "otherwise."
                                ),
                            },
                            "session_note_path": {
                                "type": ["string", "null"],
                                "description": (
                                    "Optional absolute path to the persisted "
                                    "session note (returned by "
                                    "write_session_note_canonical)."
                                ),
                                "default": None,
                            },
                            "adrs_created": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                                "description": (
                                    "Paths of ADR notes the skill created "
                                    "during this close (if any)."
                                ),
                            },
                        },
                        "required": ["status"],
                    },
                ),
                types.Tool(
                    name="cortex_session_list",
                    description=(
                        "List Sessions, optionally filtered by status. Returns a "
                        "JSON array of summarized SessionRecord objects (without "
                        "full checkpoint arrays — use cortex_session_status for that)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": ["string", "null"],
                                "enum": ["open", "closed", "handoff", "abandoned", None],
                                "default": None,
                            },
                        },
                    },
                ),
                types.Tool(
                    name="cortex_self_review_note",
                    description=(
                        "Phase 09.A+ / May 2026 — pure inspection of a "
                        "draft note body written by the /cortex-documenter "
                        "skill. Scans for placeholder tokens (TBD, TODO, "
                        "FIXME, ???, ...), hollow success claims (\"tests "
                        "pass\" without a corresponding verification hook "
                        "result), and other low-signal smells. Returns "
                        "JSON {warnings: [str], passed: bool}. INFORMATIONAL "
                        "only — never blocks persistence. The skill decides "
                        "whether to revise and re-call, or accept the "
                        "warnings and proceed."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "string",
                                "description": (
                                    "The Markdown body the skill drafted. "
                                    "Scanned case-insensitively."
                                ),
                            },
                            "verification_hooks_passed": {
                                "type": "boolean",
                                "default": False,
                                "description": (
                                    "Whether at least one verification "
                                    "hook in the spec actually passed. "
                                    "Drives the hollow-claim detector — "
                                    "claiming \"tests pass\" is hollow if "
                                    "no hook reported success."
                                ),
                            },
                        },
                        "required": ["body"],
                    },
                ),
                types.Tool(
                    name="cortex_write_doc",
                    description=(
                        "Phase 09.A+ / May 2026 — generic canonical writer "
                        "dispatched by ``doc_type``. Used by the "
                        "``/cortex-documenter`` skill to persist any of the "
                        "11 supported doc types under their canonical vault "
                        "folder. The ``payload`` shape varies per doc_type; "
                        "minimum required fields per type:\n\n"
                        "• ``session``     → title, spec_summary, session_id\n"
                        "• ``handoff``     → title, parent_session_id\n"
                        "• ``adr``         → title, context, decision\n"
                        "• ``decision``    → title, context, decision\n"
                        "• ``incident``    → title, short_description, severity\n"
                        "• ``postmortem``  → title, incident_path, incident_number, root_cause\n"
                        "• ``runbook``     → title, runbook_kind, procedure\n"
                        "• ``architecture``→ title, summary\n"
                        "• ``changelog``   → title, version\n"
                        "• ``glossary``    → title, term, definition\n"
                        "• ``hu``          → title, external_id, source\n\n"
                        "Every payload accepts the common fields ``tags`` "
                        "(list[str]), ``links`` (list[str]), ``status`` (str). "
                        "Returns JSON {path, doc_type}.\n\n"
                        "NOTE: ``spec`` and ``design`` doc types are NOT "
                        "exposed here — use ``cortex_create_spec`` and "
                        "``write_design_note_canonical`` respectively."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_type": {
                                "type": "string",
                                "enum": [
                                    "session",
                                    "handoff",
                                    "adr",
                                    "decision",
                                    "incident",
                                    "postmortem",
                                    "runbook",
                                    "architecture",
                                    "changelog",
                                    "glossary",
                                    "hu",
                                ],
                            },
                            "payload": {
                                "type": "object",
                                "description": (
                                    "Fields for the chosen doc_type. See "
                                    "the description above for the minimum "
                                    "required fields per type."
                                ),
                            },
                            "vault_scope": {
                                "type": "string",
                                "enum": ["local", "enterprise"],
                                "default": "local",
                            },
                            "overwrite": {
                                "type": "boolean",
                                "default": False,
                            },
                        },
                        "required": ["doc_type", "payload"],
                    },
                ),
                types.Tool(
                    name="write_design_note_canonical",
                    description=(
                        "Persist a design document under vault/designs/ "
                        "(Pluggable Middle Phase 09.B). Used by "
                        "cortex-code-designer between explorer and "
                        "implementer in Deep Track. Returns the absolute "
                        "path of the persisted note."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "session_id": {"type": "string"},
                            "spec_path": {"type": "string"},
                            "architecture_decision": {"type": "string"},
                            "data_model_changes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "api_contracts": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "test_plan": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "risks": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "status": {
                                "type": "string",
                                "enum": ["draft", "approved", "superseded"],
                                "default": "draft",
                            },
                        },
                        "required": ["title", "session_id", "spec_path"],
                    },
                ),
                types.Tool(
                    name="cortex_session_task_list",
                    description=(
                        "List the granular tasks attached to a Session "
                        "(Pluggable Middle Phase 09.C). Optionally filter "
                        "by status. Returns a JSON array of Task objects "
                        "in declaration order."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": ["string", "null"],
                                "description": "Session id (default: active).",
                                "default": None,
                            },
                            "status": {
                                "type": ["string", "null"],
                                "enum": [
                                    "pending",
                                    "in-progress",
                                    "done",
                                    "skipped",
                                    "blocked",
                                    None,
                                ],
                                "default": None,
                            },
                        },
                    },
                ),
                types.Tool(
                    name="cortex_session_task_update",
                    description=(
                        "Mutate one task's status (Pluggable Middle Phase 09.C). "
                        "If the task doesn't exist yet, it is created on the "
                        "fly when ``description`` is supplied — that is how "
                        "SDDwork emits a task decomposition in one pass. "
                        "Setting ``status='done'`` stamps ``completed_at`` "
                        "automatically. Returns JSON with task_id and new status."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": ["string", "null"],
                                "description": "Session id (default: active).",
                                "default": None,
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task id matching the pattern 'T\\\\d+(\\\\.\\\\d+)*'.",
                            },
                            "status": {
                                "type": "string",
                                "enum": [
                                    "pending",
                                    "in-progress",
                                    "done",
                                    "skipped",
                                    "blocked",
                                ],
                            },
                            "description": {
                                "type": "string",
                                "description": (
                                    "Required when the task does not exist "
                                    "yet (auto-creates a new task with the "
                                    "given description + initial status)."
                                ),
                                "default": "",
                            },
                            "files_in_scope": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": [],
                            },
                            "note": {"type": "string", "default": ""},
                            "checkpoint_index": {
                                "type": ["integer", "null"],
                                "default": None,
                            },
                        },
                        "required": ["task_id", "status"],
                    },
                ),
                types.Tool(
                    name="cortex_review_checkpoint",
                    description=(
                        "Run the two-stage quality review on a checkpoint of an "
                        "OPEN Session. Stage 1 verifies spec compliance "
                        "(artifacts in scope; checkpoint reports progress); "
                        "stage 2 verifies quality (no placeholder tokens in "
                        "note; non-trivial test/build claims). Returns JSON "
                        "with accepted, stage_1_passed, stage_2_passed, "
                        "reason, action (one of accept|redelegate|warn)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": ["string", "null"],
                                "description": "Session id (default: active).",
                                "default": None,
                            },
                            "checkpoint_index": {
                                "type": "integer",
                                "description": (
                                    "Index into session.checkpoints. Negative "
                                    "indexing is supported (default: -1, most "
                                    "recent)."
                                ),
                                "default": -1,
                            },
                        },
                    },
                ),
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

        if name == "cortex_emit_proposal":
            result_text = self._emit_proposal_text(arguments)
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

        # ── Pluggable Middle: Session primitive (Fase 00 / T0.7) ──
        if name == "cortex_session_open":
            result_text = self._session_open_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_session_checkpoint":
            result_text = self._session_checkpoint_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_session_close":
            result_text = self._session_close_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_session_status":
            result_text = self._session_status_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_session_list":
            result_text = self._session_list_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_finish_session":
            result_text = self._finish_session_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_documenter_briefing":
            result_text = self._documenter_briefing_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_close_session":
            result_text = self._close_session_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_review_checkpoint":
            result_text = self._session_review_checkpoint_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "write_design_note_canonical":
            result_text = self._write_design_note_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_write_doc":
            result_text = self._write_doc_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_self_review_note":
            result_text = self._self_review_note_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_session_task_list":
            result_text = self._session_task_list_text(arguments)
            self._log_tool_call(name, arguments, result_text)
            return result_text

        if name == "cortex_session_task_update":
            result_text = self._session_task_update_text(arguments)
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
        """Convert MCP arguments into a useful context enrichment request.

        Phase 08 / T8.4: when the caller (typically SDDwork) passes a
        ``task_type``, the retrieval envelope is sized by
        :func:`cortex.context_enricher.budget_resolver.resolve_budget_profile`.
        Calls without ``task_type`` use the historical default and stay
        backward-compatible.
        """
        from cortex.context_enricher.budget_resolver import resolve_budget_profile

        query = str(arguments.get("query", "")).strip()
        changed_files = self._normalize_string_list(arguments.get("changed_files", []))
        keywords = self._normalize_string_list(arguments.get("keywords", []))

        if not keywords and query:
            keywords = self._extract_query_keywords(query)

        pr_title = str(arguments.get("pr_title", "")).strip() or query or None

        raw_task_type = arguments.get("task_type")
        task_type = (
            str(raw_task_type).strip()
            if raw_task_type not in (None, "")
            else None
        )
        raw_complexity = arguments.get("complexity")
        complexity = (
            str(raw_complexity).strip()
            if raw_complexity not in (None, "")
            else None
        )

        top_k: int | None
        if task_type is not None:
            profile = resolve_budget_profile(task_type, complexity)
            top_k = profile["top_k"]
        else:
            top_k = None

        return self.memory.enrich(
            changed_files=changed_files,
            keywords=keywords,
            pr_title=pr_title,
            top_k=top_k,
        )

    @staticmethod
    def _normalize_string_list(values: Any) -> list[str]:
        """Coerce ``values`` to a clean ``list[str]``.

        Tolerates two shapes commonly produced by LLM clients:

        - ``list``/``tuple`` of strings → strip + drop empties.
        - Single ``str`` → split on commas (CSV), strip + drop empties.

        Any other type collapses to an empty list. See
        ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.
        """
        if values is None:
            return []
        if isinstance(values, str):
            return [token.strip() for token in values.split(",") if token.strip()]
        if isinstance(values, (list, tuple)):
            return [str(v).strip() for v in values if str(v).strip()]
        return []

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

        changed_files_text = (
            ", ".join(changed_files) if changed_files else "(sin archivos inferidos)"
        )
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

        proposal_mode = str(arguments.get("proposal_mode", "optional"))
        proposal_confirmed = bool(arguments.get("proposal_confirmed", False))

        if proposal_mode == "required" and proposal_confirmed:
            gap_error = self._validate_proposal_gap()
            if gap_error is not None:
                logger.error("PROPOSAL_GAP_VIOLATION: %s", gap_error)
                return f"❌ {gap_error}"

        from cortex.documentation.errors import DuplicateDocumentError

        try:
            result = self.memory.create_spec_note(
                title=arguments.get("title", ""),
                goal=arguments.get("goal", ""),
                requirements=arguments.get("requirements", []),
                files_in_scope=arguments.get("files_in_scope", []),
                constraints=arguments.get("constraints", []),
                acceptance_criteria=arguments.get("acceptance_criteria", []),
                tags=arguments.get("tags", []),
                verification_hooks=arguments.get("verification_hooks", []),
                sync_vault=not arguments.get("no_sync", False),
                proposal_mode=proposal_mode,
                proposal_confirmed=proposal_confirmed,
            )
        except ValueError as exc:
            return f"❌ {exc}"
        except DuplicateDocumentError as exc:
            # Expected branch: a spec already exists at the target path with
            # *different* content. Idempotent same-content retries don't reach
            # this — they succeed silently in ``writers._write_note``. Return
            # an actionable message without polluting ``_error_history`` /
            # marking the server as degraded; this is user-recoverable, not a
            # server fault. See
            # ``docs/incidents/2026-05-22_appfutbol-mcp-duplicate-loop/``.
            return (
                f"ℹ️  Spec ya existe con contenido distinto.\n\n{exc}\n\n"
                f"Opciones:\n"
                f"  • Cambiá el título para generar un slug distinto.\n"
                f"  • O abrí sesión sobre la spec existente con cortex_session_open."
            )
        # Tolerate test doubles that still return a bare Path (see
        # ``tests/unit/test_mcp_server.py``). Real callers always return
        # ``SpecCreationResult``.
        if hasattr(result, "path"):
            path = result.path
            session = result.session
        else:
            path = result
            session = None
        message = f"Specification saved -> {path}"
        if session is not None and session.is_gitless:
            message += (
                "\n\n⚠️  No git repository detected. Session opened in degraded mode:\n"
                "   • cortex finish-session will skip git diff reconstruction\n"
                "   • documenter will rely exclusively on checkpoints\n"
                "   • To enable full session capabilities later, run:\n"
                "       git init && git add -A && git commit -m \"initial\""
            )
        return message

    def _validate_proposal_gap(self) -> str | None:
        """Return an error string if the proposal/spec gap is invalid.

        Enforces Phase 09.A+ ``required`` mode: a follow-up
        ``cortex_create_spec`` with ``proposal_confirmed=True`` must come
        from a different conversational turn than the originating
        ``cortex_emit_proposal``. The gap heuristic catches an LLM that
        chains both calls in the same response without a real user reply.

        Returns:
            ``None`` if the gap is fine; otherwise a human-readable error.
        """
        emitted_at = self._last_proposal_emitted_at
        if emitted_at is None:
            return (
                "proposal_mode='required' requires a prior cortex_emit_proposal "
                "call. Emit the proposal first, end your turn, and only after "
                "the user replies should you call cortex_create_spec with "
                "proposal_confirmed=True."
            )
        delta = (datetime.now() - emitted_at).total_seconds()
        if delta < self._PROPOSAL_MIN_GAP_SECONDS:
            return (
                f"proposal emitted {delta:.2f}s ago — too recent to count as "
                f"user-confirmed. The user has not had time to respond yet. "
                f"End your turn after cortex_emit_proposal and wait for an "
                f"explicit reply before calling cortex_create_spec. "
                f"(minimum gap: {self._PROPOSAL_MIN_GAP_SECONDS}s)"
            )
        return None

    def _emit_proposal_text(self, arguments: dict[str, Any]) -> str:
        """Render a structured proposal card and record its timestamp.

        Validates the payload against :class:`cortex.session.proposal.Proposal`,
        which guarantees recommendation/alternative consistency. Stamps
        ``_last_proposal_emitted_at`` so a subsequent
        ``cortex_create_spec`` with ``proposal_mode='required'`` can verify
        a user turn has elapsed.
        """
        from pydantic import ValidationError

        from cortex.session.proposal import Proposal, format_proposal_card

        payload = {
            "summary": arguments.get("summary", ""),
            "alternatives": arguments.get("alternatives", []),
            "recommendation_id": arguments.get("recommendation_id", ""),
            "risks": list(arguments.get("risks", []) or []),
        }
        try:
            proposal = Proposal.model_validate(payload)
        except ValidationError as exc:
            return f"❌ cortex_emit_proposal payload invalid: {exc}"

        self._last_proposal_emitted_at = datetime.now()
        card = format_proposal_card(proposal)
        return card

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
    # Pluggable Middle — Session primitive (Fase 00 / T0.7)
    # ------------------------------------------------------------------

    _VALID_CHECKPOINT_SOURCES: tuple[str, ...] = _CHECKPOINT_SOURCE_VALUES
    _VALID_CLOSE_STATUSES: tuple[str, ...] = ("closed", "handoff", "abandoned")

    def _session_open_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_open``."""
        spec_id = str(arguments.get("spec_id", "")).strip()
        spec_path = str(arguments.get("spec_path", "")).strip()
        if not spec_id or not spec_path:
            return "❌ spec_id and spec_path are required for cortex_session_open."

        record = self.memory.open_session(
            spec_id=spec_id,
            spec_path=spec_path,
            spec_summary=str(arguments.get("spec_summary", "")),
        )
        payload = {
            "session_id": record.session_id,
            "opened_at": record.opened_at.isoformat(),
            "start_commit": record.start_commit,
            "start_branch": record.start_branch,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_checkpoint_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_checkpoint``."""
        session_id = str(arguments.get("session_id", "")).strip()
        source = str(arguments.get("source", "")).strip()
        if not session_id or not source:
            return "❌ session_id and source are required for cortex_session_checkpoint."
        if source not in self._VALID_CHECKPOINT_SOURCES:
            return (
                f"❌ Invalid source {source!r}. Must be one of: "
                f"{', '.join(self._VALID_CHECKPOINT_SOURCES)}"
            )

        record = self.memory.checkpoint_session(
            session_id,
            source=source,
            verified_claims=list(arguments.get("verified_claims", []) or []),
            unverified_claims=list(arguments.get("unverified_claims", []) or []),
            artifacts_touched=list(arguments.get("artifacts_touched", []) or []),
            note=str(arguments.get("note", "")),
        )
        last = record.checkpoints[-1] if record.checkpoints else None
        payload = {
            "session_id": record.session_id,
            "checkpoint_count": len(record.checkpoints),
            "last_checkpoint_at": last.timestamp.isoformat() if last else None,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_close_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_close``."""
        session_id = str(arguments.get("session_id", "")).strip()
        status = str(arguments.get("status", "")).strip()
        documenter_decision = str(arguments.get("documenter_decision", "")).strip()
        if not session_id or not status or not documenter_decision:
            return (
                "❌ session_id, status and documenter_decision are required "
                "for cortex_session_close."
            )
        if status not in self._VALID_CLOSE_STATUSES:
            return (
                f"❌ Invalid status {status!r}. Must be one of: "
                f"{', '.join(self._VALID_CLOSE_STATUSES)}"
            )
        if documenter_decision not in self._VALID_CLOSE_STATUSES:
            return (
                f"❌ Invalid documenter_decision {documenter_decision!r}. "
                f"Must be one of: {', '.join(self._VALID_CLOSE_STATUSES)}"
            )

        session_note_path = arguments.get("session_note_path")
        adrs = list(arguments.get("adrs_created", []) or [])
        record = self.memory.close_session(
            session_id,
            status=status,
            documenter_decision=documenter_decision,
            session_note_path=session_note_path,
            adrs_created=adrs,
        )
        payload = {
            "session_id": record.session_id,
            "closed_at": record.closed_at.isoformat() if record.closed_at else None,
            "end_commit": record.end_commit,
            "mode_inferred": record.mode.value,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_status_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_status``."""
        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
        else:
            record = self.memory.get_session(str(raw_id).strip())
        return json.dumps(record.model_dump(mode="json"), ensure_ascii=False)

    def _session_task_list_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_task_list`` (Phase 09.C)."""
        from cortex.session import TaskStatus

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
            session_id = record.session_id
        else:
            session_id = str(raw_id).strip()

        raw_status = arguments.get("status")
        filter_status: TaskStatus | None = None
        if raw_status not in (None, ""):
            try:
                filter_status = TaskStatus(str(raw_status))
            except ValueError:
                return (
                    f"❌ Invalid status {raw_status!r}. Must be one of: "
                    f"{', '.join(s.value for s in TaskStatus)}"
                )

        tasks = self.memory.list_session_tasks(session_id, status=filter_status)
        return json.dumps(
            [t.model_dump(mode="json") for t in tasks],
            ensure_ascii=False,
        )

    def _session_task_update_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_task_update`` (Phase 09.C).

        Doubles as ``create-or-update``: if the task id does not exist
        yet and ``description`` is supplied, a fresh task is appended.
        """
        from cortex.session import Task, TaskStatus

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
            session_id = record.session_id
        else:
            session_id = str(raw_id).strip()

        task_id = str(arguments.get("task_id", "")).strip()
        raw_status = str(arguments.get("status", "")).strip()
        if not task_id or not raw_status:
            return "❌ task_id and status are required."
        try:
            new_status = TaskStatus(raw_status)
        except ValueError:
            return (
                f"❌ Invalid status {raw_status!r}. Must be one of: "
                f"{', '.join(s.value for s in TaskStatus)}"
            )

        note = str(arguments.get("note", ""))
        ckp_idx = arguments.get("checkpoint_index")
        checkpoint_index: int | None
        if ckp_idx is None or ckp_idx == "":
            checkpoint_index = None
        else:
            try:
                checkpoint_index = int(ckp_idx)
            except (TypeError, ValueError):
                return "❌ checkpoint_index must be an integer."

        # Auto-create the task if it doesn't exist yet and description was passed.
        existing = self.memory.list_session_tasks(session_id)
        if not any(t.id == task_id for t in existing):
            description = str(arguments.get("description", "")).strip()
            if not description:
                return (
                    f"❌ Task {task_id!r} does not exist; pass `description` "
                    "to create it on the fly."
                )
            files = list(arguments.get("files_in_scope", []) or [])
            try:
                self.memory.add_session_task(
                    session_id,
                    Task(
                        id=task_id,
                        description=description,
                        files_in_scope=files,
                        status=TaskStatus.PENDING,
                    ),
                )
            except (ValueError, Exception) as exc:  # noqa: BLE001
                return f"❌ {exc}"

        try:
            self.memory.update_session_task(
                session_id,
                task_id,
                new_status,
                note=note,
                checkpoint_index=checkpoint_index,
            )
        except (ValueError, Exception) as exc:  # noqa: BLE001
            return f"❌ {exc}"
        return json.dumps(
            {"session_id": session_id, "task_id": task_id, "status": new_status.value},
            ensure_ascii=False,
        )

    def _write_design_note_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``write_design_note_canonical`` (Phase 09.B).

        Persists a design document under ``vault/designs/`` using the
        canonical writer. The vault path is resolved via the active
        :class:`WorkspaceLayout`; failures (invalid spec_path, missing
        required field) come back as ``❌ <message>`` for the LLM.
        """
        from cortex.documentation import write_design_note_canonical
        from cortex.documentation.data import DesignDocData
        from cortex.documentation.errors import SchemaValidationError
        from cortex.documentation.writers import VaultLike

        title = str(arguments.get("title", "")).strip()
        session_id = str(arguments.get("session_id", "")).strip()
        spec_path = str(arguments.get("spec_path", "")).strip()
        if not session_id:
            return "❌ session_id is required for write_design_note_canonical."
        if not spec_path:
            return "❌ spec_path is required for write_design_note_canonical."

        data = DesignDocData(
            title=title or f"Design for {session_id}",
            tags=list(arguments.get("tags", []) or []),
            status=str(arguments.get("status", "draft")),
            session_id=session_id,
            spec_path=spec_path,
            architecture_decision=str(arguments.get("architecture_decision", "")),
            data_model_changes=list(arguments.get("data_model_changes", []) or []),
            api_contracts=list(arguments.get("api_contracts", []) or []),
            test_plan=list(arguments.get("test_plan", []) or []),
            risks=list(arguments.get("risks", []) or []),
        )

        # Reuse the same vault discovery the spec / session writers use.
        layout = self._get_layout()
        vault_root = layout.vault_path
        vault_root.mkdir(parents=True, exist_ok=True)

        vault: VaultLike = PathVault(vault_root)
        try:
            path = write_design_note_canonical(data, vault=vault)
        except SchemaValidationError as exc:
            return f"❌ {exc}"
        return json.dumps({"path": str(path)}, ensure_ascii=False)

    _DOC_TYPE_DISPATCH: dict[str, tuple[str, str]] = {
        # doc_type → (DataClass name, writer name) — resolved at runtime
        # against ``cortex.documentation.data`` and ``cortex.documentation``
        # so the table stays compact and self-documenting.
        "session": ("SessionData", "write_session_note_canonical"),
        "handoff": ("HandoffData", "write_handoff_note"),
        "adr": ("ADRData", "write_adr_note"),
        "decision": ("DecisionData", "write_decision_note"),
        "incident": ("IncidentData", "write_incident_note"),
        "postmortem": ("PostmortemData", "write_postmortem_note"),
        "runbook": ("RunbookData", "write_runbook_note"),
        "architecture": ("ArchitectureData", "write_architecture_note"),
        "changelog": ("ChangelogData", "write_changelog_note"),
        "glossary": ("GlossaryEntryData", "write_glossary_entry"),
        "hu": ("HUData", "write_hu_note"),
    }

    def _write_doc_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_write_doc`` (Phase 09.A+ / May 2026).

        Dispatch the payload to the appropriate canonical writer based
        on ``doc_type``. The skill calls this for each note it wants to
        persist (one session + zero or more ADRs / decisions / runbooks
        / etc.). Returns JSON ``{path, doc_type}`` on success or
        ``❌ <message>`` on validation failure.

        ``spec`` and ``design`` are not routed here on purpose — those
        have their own governance flows (``cortex_create_spec`` and
        ``write_design_note_canonical``).
        """
        from cortex.documentation import data as data_module
        from cortex.documentation import (
            write_adr_note,
            write_architecture_note,
            write_changelog_note,
            write_decision_note,
            write_glossary_entry,
            write_handoff_note,
            write_hu_note,
            write_incident_note,
            write_postmortem_note,
            write_runbook_note,
            write_session_note_canonical,
        )
        from cortex.documentation.errors import SchemaValidationError
        from cortex.documentation.writers import VaultLike

        doc_type = str(arguments.get("doc_type", "")).strip()
        if doc_type not in self._DOC_TYPE_DISPATCH:
            return (
                f"❌ Unknown doc_type {doc_type!r}. Must be one of: "
                f"{', '.join(sorted(self._DOC_TYPE_DISPATCH))}."
            )

        payload = arguments.get("payload") or {}
        if not isinstance(payload, dict):
            return "❌ 'payload' must be an object."

        # Fail-fast validation of the minimum-required-fields contract
        # documented in the tool description. Without this, the failure
        # happens deeper in ``write_*_canonical`` via ``SchemaValidationError``
        # with a less actionable message. The list below mirrors the bullets
        # in the tool description; keep them in sync.
        _REQUIRED_BY_DOC_TYPE: dict[str, tuple[str, ...]] = {
            "session": ("title", "spec_summary", "session_id"),
            "handoff": ("title", "parent_session_id"),
            "adr": ("title", "context", "decision"),
            "decision": ("title", "context", "decision"),
            "incident": ("title", "short_description", "severity"),
            "postmortem": ("title", "incident_path", "incident_number", "root_cause"),
            "runbook": ("title", "runbook_kind", "procedure"),
            "architecture": ("title", "summary"),
            "changelog": ("title", "version"),
            "glossary": ("title", "term", "definition"),
            "hu": ("title", "external_id", "source"),
        }
        required_fields = _REQUIRED_BY_DOC_TYPE.get(doc_type, ())
        missing = [f for f in required_fields if not payload.get(f)]
        if missing:
            return (
                f"❌ payload for doc_type={doc_type!r} is missing required "
                f"field(s): {', '.join(missing)}. See the tool description "
                f"for the full per-type contract."
            )

        vault_scope = str(arguments.get("vault_scope", "local"))
        overwrite = bool(arguments.get("overwrite", False))

        data_class_name, writer_name = self._DOC_TYPE_DISPATCH[doc_type]
        data_class = getattr(data_module, data_class_name)
        writer_map = {
            "write_session_note_canonical": write_session_note_canonical,
            "write_handoff_note": write_handoff_note,
            "write_adr_note": write_adr_note,
            "write_decision_note": write_decision_note,
            "write_incident_note": write_incident_note,
            "write_postmortem_note": write_postmortem_note,
            "write_runbook_note": write_runbook_note,
            "write_architecture_note": write_architecture_note,
            "write_changelog_note": write_changelog_note,
            "write_glossary_entry": write_glossary_entry,
            "write_hu_note": write_hu_note,
        }
        writer = writer_map[writer_name]

        # Reuse the same vault discovery as other writers.
        layout = self._get_layout()
        vault_root = layout.vault_path
        vault_root.mkdir(parents=True, exist_ok=True)

        vault: VaultLike = PathVault(vault_root)

        # Build the dataclass from the payload, dropping unknown fields
        # so an over-eager LLM that includes extras doesn't crash the call.
        valid_fields = {f.name for f in data_class.__dataclass_fields__.values()}
        clean_payload = {k: v for k, v in payload.items() if k in valid_fields}
        try:
            data = data_class(**clean_payload)
            path = writer(data, vault=vault, vault_scope=vault_scope, overwrite=overwrite)
        except SchemaValidationError as exc:
            return f"❌ {exc}"
        except TypeError as exc:
            return f"❌ Invalid payload for doc_type={doc_type!r}: {exc}"
        return json.dumps(
            {"path": str(path), "doc_type": doc_type}, ensure_ascii=False
        )

    _PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
        {"tbd", "todo", "fixme", "xxx", "???", "fill me", "[pendiente]"}
    )
    _SUCCESS_CLAIM_PATTERNS: frozenset[str] = frozenset(
        {
            "tests pass",
            "test passed",
            "tests passed",
            "build exitoso",
            "build successful",
            "linter clean",
            "lint passed",
            "checks pass",
            "ci passed",
        }
    )

    def _self_review_note_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_self_review_note`` (Phase 09.A+ / May 2026).

        Pure inspection. Surfaces placeholder tokens and hollow success
        claims so the skill can revise its draft before persisting.
        Never blocks — the skill chooses what to do with the warnings.
        """
        body = str(arguments.get("body", ""))
        hooks_passed = bool(arguments.get("verification_hooks_passed", False))

        warnings: list[str] = []
        body_lower = body.lower()
        for token in self._PLACEHOLDER_TOKENS:
            if token in body_lower:
                warnings.append(f"Placeholder token detected: {token!r}")

        if not hooks_passed:
            for pattern in self._SUCCESS_CLAIM_PATTERNS:
                if pattern in body_lower:
                    warnings.append(
                        f"Hollow claim {pattern!r} — no verification hook "
                        "actually passed; either remove the claim or run "
                        "the test/build that proves it."
                    )

        return json.dumps(
            {"warnings": warnings, "passed": not warnings}, ensure_ascii=False
        )

    def _session_review_checkpoint_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_review_checkpoint`` (Phase 08 / T8.2).

        Runs :func:`cortex.session.quality_gates.review_checkpoint` over
        the resolved checkpoint of the resolved session and returns the
        verdict as JSON. Pure inspection — never mutates the session.
        """
        from cortex.documenter.spec_loader import load_spec
        from cortex.session.quality_gates import review_checkpoint

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            record = self.memory.get_active_session()
            if record is None:
                return "❌ No active session. Pass session_id or open one first."
        else:
            record = self.memory.get_session(str(raw_id).strip())

        if not record.checkpoints:
            return "❌ Session has no checkpoints to review."

        try:
            idx = int(arguments.get("checkpoint_index", -1))
        except (TypeError, ValueError):
            return "❌ checkpoint_index must be an integer."
        try:
            checkpoint = record.checkpoints[idx]
        except IndexError:
            return (
                f"❌ checkpoint_index {idx} out of range "
                f"(session has {len(record.checkpoints)} checkpoint(s))."
            )

        spec_path = record.spec_path
        if not spec_path.is_absolute():
            spec_path = (self.project_root / spec_path).resolve()
        spec = load_spec(spec_path)

        verdict = review_checkpoint(checkpoint, spec)
        payload = {
            "accepted": verdict.accepted,
            "stage_1_passed": verdict.stage_1_passed,
            "stage_2_passed": verdict.stage_2_passed,
            "reason": verdict.reason,
            "action": verdict.action,
        }
        return json.dumps(payload, ensure_ascii=False)

    _VALID_FINISH_INTENTS: tuple[str, ...] = ("auto", "handoff", "abandon")

    def _finish_session_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_finish_session`` (Phase 01 / T1.7).

        The Phase 04 ``--interactive`` mode of the documenter (``cortex
        finish-session --interactive``) is **CLI only**; an MCP request
        runs the auto pipeline because the protocol is non-interactive
        by design (text in, text out — no terminal to prompt against).
        Pass ``interactive: true`` to receive a clear error directing
        the caller to the CLI.
        """
        if arguments.get("interactive"):
            return (
                "❌ The interactive documenter mode is CLI-only. Run "
                "`cortex finish-session --interactive` instead, or omit "
                "`interactive` from this tool call."
            )
        from cortex.documenter import (
            DocumenterPersister,
            FinishOverrides,
            ReconstructionInput,
            Reconstructor,
        )
        from cortex.session import SessionStatus
        from cortex.session.verification import VerificationRunner

        raw_id = arguments.get("session_id")
        intent = str(arguments.get("intent") or "auto").strip()
        reason = str(arguments.get("reason") or "").strip()

        if intent not in self._VALID_FINISH_INTENTS:
            return (
                f"❌ Invalid intent {intent!r}. Must be one of: "
                f"{', '.join(self._VALID_FINISH_INTENTS)}"
            )
        if intent != "auto" and not reason:
            return f"❌ 'reason' is required when intent is {intent!r}."

        # Resolve session id: explicit arg or active.
        if raw_id is None or not str(raw_id).strip():
            active = self.memory.get_active_session()
            if active is None:
                return "❌ No active session. Pass session_id explicitly."
            session_id = active.session_id
        else:
            session_id = str(raw_id).strip()

        record = self.memory.get_session(session_id)
        if record.status is not SessionStatus.OPEN:
            return (
                f"❌ Session {session_id!r} is already in status "
                f"{record.status.value!r}; nothing to finish."
            )

        reconstructor = Reconstructor(
            session_service=self.memory._session_service,
            verification_runner=VerificationRunner(repo_root=self.memory.repo_root),
            repo_root=self.memory.repo_root,
        )
        out = reconstructor.reconstruct(ReconstructionInput(session_id=session_id))

        forced_status: SessionStatus | None = None
        if intent == "abandon":
            forced_status = SessionStatus.ABANDONED
        elif intent == "handoff":
            forced_status = SessionStatus.HANDOFF

        persister = DocumenterPersister(
            note_service=self.memory._note_service,
            session_service=self.memory._session_service,
            vault_path=self.memory._vault_path_resolved,
        )
        result = persister.finalize(
            out,
            overrides=FinishOverrides(forced_status=forced_status),
        )

        payload = {
            "session_id": result.session_id,
            "final_status": result.final_status.value,
            "session_note_path": (
                str(result.session_note_path) if result.session_note_path else None
            ),
            "adrs_created": [str(p) for p in result.adrs_created],
            "summary_text": result.summary,
            "already_closed": result.already_closed,
        }
        return json.dumps(payload, ensure_ascii=False)

    def _documenter_briefing_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_documenter_briefing`` (Phase 09.A+ / May 2026).

        Read-only reconstruction. Mirrors :meth:`_finish_session_text`
        up to the moment of persistence, then returns the full
        :class:`ReconstructionOutput` serialized as JSON instead of
        running the persister and closing the session.

        Consumed by the ``/cortex-documenter`` skill to obtain the
        context (spec, diff, checkpoints, hooks, scope drift, ADR
        candidates) it needs to write a session note with editorial
        criterion. The skill calls ``cortex_close_session`` after it
        has written the notes via the ``write_*_note_canonical`` tools.
        """
        from cortex.documenter import ReconstructionInput, Reconstructor
        from cortex.session.verification import VerificationRunner

        raw_id = arguments.get("session_id")
        if raw_id is None or not str(raw_id).strip():
            active = self.memory.get_active_session()
            if active is None:
                return "❌ No active session. Pass session_id explicitly."
            session_id = active.session_id
        else:
            session_id = str(raw_id).strip()

        run_hooks = bool(arguments.get("run_hooks", False))

        reconstructor = Reconstructor(
            session_service=self.memory._session_service,
            verification_runner=VerificationRunner(repo_root=self.memory.repo_root),
            repo_root=self.memory.repo_root,
        )
        out = reconstructor.reconstruct(
            ReconstructionInput(session_id=session_id, run_hooks=run_hooks)
        )
        return json.dumps(_serialize_reconstruction(out), ensure_ascii=False)

    def _close_session_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_close_session`` (Phase 09.A+ / May 2026).

        Close an OPEN session into a terminal state declared by the
        skill, recording the optional note path + any ADR paths the
        skill created. Does **not** invoke the reconstructor; the
        skill already has all the context (it called
        ``cortex_documenter_briefing`` first).
        """
        from cortex.session import SessionStatus

        raw_id = arguments.get("session_id")
        raw_status = arguments.get("status")
        note_path_arg = arguments.get("session_note_path")
        adrs_arg = arguments.get("adrs_created", []) or []

        if raw_status is None or not str(raw_status).strip():
            return "❌ 'status' is required (one of: closed, handoff, abandoned)."
        try:
            status = SessionStatus(str(raw_status).strip())
        except ValueError:
            return (
                f"❌ Invalid status {raw_status!r}. Must be one of: "
                "closed, handoff, abandoned."
            )
        if status not in {
            SessionStatus.CLOSED,
            SessionStatus.HANDOFF,
            SessionStatus.ABANDONED,
        }:
            return (
                f"❌ Status {status.value!r} is not terminal — cortex_close_session "
                "only accepts closed / handoff / abandoned."
            )

        if raw_id is None or not str(raw_id).strip():
            active = self.memory.get_active_session()
            if active is None:
                return "❌ No active session. Pass session_id explicitly."
            session_id = active.session_id
        else:
            session_id = str(raw_id).strip()

        from pathlib import Path

        note_path = Path(str(note_path_arg)) if note_path_arg else None
        adrs = [Path(str(p)) for p in adrs_arg if str(p).strip()]

        try:
            record = self.memory._session_service.close(
                session_id,
                status=status,
                documenter_decision=status,
                session_note_path=note_path,
                adrs_created=adrs,
            )
        except Exception as exc:
            return f"❌ Failed to close session {session_id!r}: {exc}"

        payload = {
            "session_id": record.session_id,
            "final_status": record.status.value,
            "mode": record.mode.value,
            "closed_at": record.closed_at.isoformat() if record.closed_at else None,
            "end_commit": record.end_commit,
            "session_note_path": (
                str(record.session_note_path) if record.session_note_path else None
            ),
            "adrs_created": [str(p) for p in record.adrs_created],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _session_list_text(self, arguments: dict[str, Any]) -> str:
        """Tool: ``cortex_session_list``."""
        raw_status = arguments.get("status")
        status = str(raw_status).strip() if raw_status else None
        records = self.memory.list_sessions(status)
        payload = [
            {
                "session_id": r.session_id,
                "status": r.status.value,
                "mode": r.mode.value,
                "opened_at": r.opened_at.isoformat(),
                "closed_at": r.closed_at.isoformat() if r.closed_at else None,
                "checkpoint_count": len(r.checkpoints),
                "spec_summary": r.spec_summary,
            }
            for r in records
        ]
        return json.dumps(payload, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Tripartita Refinada — Handoff & Verification helpers (Plan 02)
    # ------------------------------------------------------------------

    def _validate_handoff_text(self, arguments: dict[str, Any]) -> str:
        """Validate a YAML handoff against the AgentHandoff schema.

        Deprecated since Pluggable Middle Phase 02: the canonical contract
        between Cortex agents is now ``cortex_session_checkpoint``. This
        tool remains available for the documenter's Legacy YAML mode
        (single-agent IDEs like Codex that cannot emit checkpoints
        inline). It will be removed in Phase 04 if no Legacy YAML
        consumer remains.
        """
        from pydantic import ValidationError

        from cortex.handoff import AgentHandoff

        logger.warning(
            "cortex_validate_handoff is deprecated since Phase 02 (Pluggable "
            "Middle). Use cortex_session_checkpoint for inter-agent state. "
            "This tool stays available only for the documenter's Legacy "
            "YAML mode."
        )
        yaml_text = str(arguments.get("handoff_yaml", "") or "")
        expected_agent = arguments.get("expected_agent")
        if not yaml_text.strip():
            return "❌ handoff_yaml is required and must not be empty."
        try:
            handoff = AgentHandoff.from_yaml(yaml_text)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
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
            lines.append(f"  📚 CONTEXT.md terms: {', '.join(handoff.suggested_context_terms)}")
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
                t.lower() for t in claim.replace("_", " ").replace("/", " ").split() if len(t) > 3
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
