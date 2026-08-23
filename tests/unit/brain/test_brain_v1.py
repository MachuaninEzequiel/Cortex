"""BRAIN-1: router determinista, tiers de herramientas y loop sin TTY/modelo."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

from rich.console import Console

from cortex.brain.chat import BrainSession
from cortex.brain.router import route_intent
from cortex.action_engine.context import ActionContext
from cortex.brain.tools import Tier, build_tools


def _ctx(tmp_path: Path):
    dot = tmp_path / ".cortex"
    dot.mkdir(parents=True, exist_ok=True)
    (dot / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n"
        "semantic:\n  vault_path: vault\n",
        encoding="utf-8",
    )
    vault = dot / "vault"
    vault.mkdir(exist_ok=True)
    (vault / "ADR-001.md").write_text(
        "---\ntitle: demo\ndoc_type: adr\nstatus: accepted\n---\n\n# d\n",
        encoding="utf-8",
    )
    layout = MagicMock()
    layout.workspace_root = tmp_path
    layout.repo_root = tmp_path
    layout.config_path = dot / "config.yaml"
    mem = MagicMock()
    sessions = MagicMock()
    sessions.list.return_value = []
    return ActionContext(layout=layout, _mem=mem, _sessions=sessions)


class TestRouter:
    def test_salud_a_cortex_health(self) -> None:
        assert route_intent("¿cómo está cortex?").tool == "cortex.health"

    def test_webgraph_a_serve(self) -> None:
        intent = route_intent("abrí el grafo")
        assert intent.tool == "webgraph.serve"

    def test_busqueda_extrae_query(self) -> None:
        intent = route_intent("busca docs sobre autenticación jwt")
        assert intent.tool == "memory.search"
        assert "autenticación" in intent.args["query"]

    def test_pregunta_abierta_va_a_related(self) -> None:
        intent = route_intent("que documentos hablan de la migracion de datos?")
        assert intent.tool == "docs.related"

    def test_slash_quit(self) -> None:
        assert route_intent("/quit").slash == "quit"

    def test_sin_match_devuelve_razon(self) -> None:
        intent = route_intent("xyzzy")
        assert intent.tool is None and intent.razon


class TestTiersYContrato:
    def test_no_hay_herramientas_mutadoras(self, tmp_path: Path) -> None:
        tools = build_tools(_ctx(tmp_path))
        mutadoras = {"vault.reindex", "session.checkpoint_now", "setup.finish_bootstrap"}
        assert not mutadoras & set(tools), "el brain NUNCA ejecuta mutaciones"

    def test_todas_read_o_safe(self, tmp_path: Path) -> None:
        for spec in build_tools(_ctx(tmp_path)).values():
            assert spec.tier in (Tier.READ, Tier.SAFE_ACTION)

    def test_webgraph_es_safe_action(self, tmp_path: Path) -> None:
        assert build_tools(_ctx(tmp_path))["webgraph.serve"].tier is Tier.SAFE_ACTION


class TestChatLoop:
    def test_dispatch_doctor_responde_sin_modelo(self, tmp_path: Path) -> None:
        sesion = BrainSession(project_root=tmp_path)
        assert sesion.abrir()
        salida = sesion.dispatch("¿cómo está cortex?")
        assert "Salud Cortex" in salida

    def test_propose_nunca_ejecuta_mutaaciones(self, tmp_path: Path) -> None:
        sesion = BrainSession(project_root=tmp_path)
        sesion.abrir()
        salida = sesion.dispatch("qué acciones pendientes tengo")
        assert "ejecutalas VOS" in salida  # propone, no ejecuta

    def test_desconocido_ofrece_ayuda(self, tmp_path: Path) -> None:
        sesion = BrainSession(project_root=tmp_path)
        sesion.abrir()
        salida = sesion.dispatch("xyzzy sin sentido")
        assert "Sé responder" in salida or "/help" in salida or "Comandos" in salida

    def test_banner_renderiza_en_80(self, tmp_path: Path) -> None:
        sesion = BrainSession(project_root=tmp_path)
        sesion.abrir()
        console = Console(record=True, width=80, file=io.StringIO())
        sesion.console_obj = console
        sesion.banner()
        lineas = console.export_text().splitlines()
        assert all(len(l) <= 80 for l in lineas)
