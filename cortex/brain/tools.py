"""Herramientas del brain — read-only + safe-action, sobre servicios existentes.

Contrato (doc 06 §BRAIN v1):
- ``Tier.READ``: consulta pura, sin side-effects.
- ``Tier.SAFE_ACTION``: side-effect externo no destructivo whitelisteado
  (único permitido hoy: webgraph.serve).
- Las MUTACIONES no son herramientas: ``actions_propose`` devuelve el
  comando CLI exacto para que el usuario las ejecute ("propone, no ejecuta").
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from cortex.action_engine.context import ActionContext


class Tier(str, Enum):
    READ = "read"
    SAFE_ACTION = "safe_action"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    tier: Tier
    handler: Callable[..., str]
    args_hint: str = ""


def build_tools(ctx: ActionContext) -> dict[str, ToolSpec]:
    """Construye el registro de herramientas anclado al proyecto de *ctx*."""
    tools: dict[str, ToolSpec] = {}

    def tool(name: str, description: str, tier: Tier, args_hint: str = ""):
        def deco(fn: Callable[..., str]) -> None:
            tools[name] = ToolSpec(name=name, description=description, tier=tier,
                                   handler=fn, args_hint=args_hint)

        return deco

    # ── READ ───────────────────────────────────────────────────────────

    @tool("memory.search", "Búsqueda híbrida (RRF) en memoria episódica+semántica.",
          Tier.READ, "<query> [top_k]")
    def memory_search(query: str, top_k: int = 5) -> str:
        result = ctx.mem.retrieve(query, top_k=top_k)
        if not result.unified_hits:
            return "Sin resultados en este repo para esa consulta."
        lineas = ["Resultados (RRF híbrido):"]
        for i, hit in enumerate(result.unified_hits, 1):
            lineas.append(
                f"  {i}. [{hit.source}] {hit.display_title} "
                f"({hit.display_path}) score={hit.score:.4f}"
            )
        return "\n".join(lineas)

    @tool("docs.related", "Documentos del vault relacionados con un tema "
          "(embeddings OPT-IN: precise=e5-large ~2GB RAM / fast=MiniLM liviano).",
          Tier.READ, "<tema> [precise|fast]")
    def docs_related(tema: str, engine: str = "") -> str:
        from cortex.semantic.vault_reader import VaultReader

        if not engine:
            return (
                "¿Qué precisión preferís?\n"
                "  · precise → e5-large multilingüe, máxima calidad (~2GB RAM)\n"
                "  · fast    → MiniLM, liviano y veloz (puede desviar)\n"
                "Respondé 'docs.related <tema> precise' o '... fast'."
            )
        model, backend = (
            ("intfloat/multilingual-e5-large", "fastembed")
            if engine.startswith("precise")
            else ("all-MiniLM-L6-v2", "onnx")
        )
        reader = VaultReader(
            vault_path=str(ctx.vault_path),
            embedding_model=model,
            embedding_backend=backend,
            vector_cache=None,
        )
        reader.sync()
        hits = reader.search(tema, top_k=5)
        if not hits:
            return f"Sin documentos relacionados con '{tema}' en este repo."
        lineas = [f"Documentos relacionados con '{tema}' ({model}):"]
        for i, h in enumerate(hits, 1):
            lineas.append(f"  {i}. {h.title} ({h.path})")
        return "\n".join(lineas)

    @tool("cortex.health", "Estado de salud de Cortex en este proyecto.", Tier.READ)
    def cortex_health() -> str:
        from cortex.tui.core import snapshot_home

        state = snapshot_home(ctx.layout.repo_root)
        items = "; ".join(f"{k}: {v}" for k, v in state.doctor_items)
        sesion = state.sesion_line or "ninguna activa"
        return (
            f"Salud Cortex — {items} · vault: {state.vault_notas} notas · "
            f"sesión: {sesion} · snapshot {state.elapsed_ms}ms"
        )

    @tool("vault.stats", "Conteos del vault y workspace.", Tier.READ)
    def vault_stats() -> str:
        vault = ctx.vault_path
        notas = len(list(vault.rglob("*.md"))) if vault.exists() else 0
        specs = len(list((vault / "specs").glob("*.md"))) if (vault / "specs").exists() else 0
        return f"Vault: {notas} notas .md ({specs} specs). Workspace: {ctx.dot_cortex}"

    @tool("session.current", "Sesión activa y sus checkpoints.", Tier.READ)
    def session_current() -> str:
        abiertas = [r for r in ctx.sessions.list() if r.status.value == "open"]
        if not abiertas:
            return "No hay sesión OPEN. Abrí una con `cortex start`."
        r = abiertas[0]
        return (
            f"Sesión {r.session_id} · OPEN · {len(r.checkpoints)} checkpoints · "
            f"abierta {r.opened_at:%Y-%m-%d %H:%M}"
        )

    # ── SAFE_ACTION ────────────────────────────────────────────────────

    @tool("webgraph.serve",
          "Levanta el visualizador del webgraph y reporta el puerto.",
          Tier.SAFE_ACTION)
    def webgraph_serve() -> str:
        from cortex.webgraph.config import WebGraphConfig

        config = WebGraphConfig.load(ctx.layout.workspace_root.parent if False else Path.cwd(),
                                     )
        puerto = config.server_port or 8000
        subprocess.Popen(
            [sys.executable, "-m", "cortex.cli.main", "webgraph", "serve", "--no-open"],
            cwd=str(Path.cwd()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"Webgraph abierto en http://127.0.0.1:{puerto} — mirá ese puerto."

    # ── propose-only: mutaciones NUNCA ejecutables acá ────────────────

    @tool("actions.propose",
          "Lista acciones sugeridas por el ActionEngine CON el comando exacto "
          "para ejecutarlas vos (el brain nunca muta).",
          Tier.READ)
    def actions_propose() -> str:
        from cortex.action_engine.actions import build_default_registry
        from cortex.action_engine.scheduler import Scheduler
        from cortex.action_engine.signals import leer_senales
        from cortex.action_engine.store import PreferencesStore

        registry = build_default_registry(ctx)
        sched = Scheduler(
            preferences=PreferencesStore(ctx.dot_cortex),
            senales=leer_senales(ctx.dot_cortex),
        )
        propuestas = sched.propose(registry)
        if not propuestas:
            return "Nada pendiente ✓"
        lineas = ["Acciones sugeridas (ejecutalas VOS con el comando indicado):"]
        for p in propuestas:
            lineas.append(f"  · {p.action.id} — {p.action.title}")
            lineas.append(f"      → cortex next --json   |   efecto: {p.action.effect}")
        lineas.append("El brain propone; la ejecución es tuya (modo estricto).")
        return "\n".join(lineas)

    return tools
