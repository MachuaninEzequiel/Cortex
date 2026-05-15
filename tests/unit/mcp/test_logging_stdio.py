"""Tests para el logging del MCP server en modo stdio.

Fase 1 — Capa 2 del plan multi-IDE & MCP hardening:
- Por default, el server NO debe agregar StreamHandler(sys.stderr) — eso
  causaba el incidente del 2026-05-15 (pipe stderr saturado bloqueando
  el handler async del server).
- Con CORTEX_MCP_LOG_TO_STDERR=1 en env, SI debe agregarlo (escape hatch).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture(autouse=True)
def _reset_root_logger():
    """basicConfig is a no-op si el root ya tiene handlers; limpiar antes y despues."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    root.handlers.clear()
    yield
    root.handlers.clear()
    root.handlers.extend(original_handlers)
    root.level = original_level


def _instantiate_server(tmp_path: Path) -> CortexMCPServer:
    """Build a CortexMCPServer in tmp_path with a minimal layout."""
    return CortexMCPServer(project_root=tmp_path)


def test_default_logging_does_not_attach_stderr_handler(tmp_path: Path, monkeypatch):
    """Sin la env var, el server no debe agregar StreamHandler(stderr).

    Nota: este test verifica el unico invariante critico de Capa 2 — que
    NO haya StreamHandler(sys.stderr). Otros subcomponentes (AgentMemory,
    AutopilotService) pueden reconfigurar handlers durante su init; el
    aserto sobre FileHandler vive separadamente.
    """
    monkeypatch.delenv("CORTEX_MCP_LOG_TO_STDERR", raising=False)
    _instantiate_server(tmp_path)

    root = logging.getLogger()
    stderr_handlers = [
        h for h in root.handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
        and getattr(h, "stream", None) is sys.stderr
    ]
    assert not stderr_handlers, (
        "Default config no debe incluir StreamHandler(sys.stderr). "
        "Razon: en stdio mode, si Claude Code no drena stderr, "
        "el server se bloquea (incidente 2026-05-15)."
    )


def test_default_logging_creates_log_file(tmp_path: Path, monkeypatch):
    """Verifica que el FileHandler quedo configurado (archivo de log creado)."""
    monkeypatch.delenv("CORTEX_MCP_LOG_TO_STDERR", raising=False)
    server = _instantiate_server(tmp_path)

    # logs_dir es resuelto por WorkspaceLayout. Verificar que existe y tiene
    # al menos un archivo mcp_calls_*.log (lo crea FileHandler al instanciarse).
    log_files = list(server._layout.logs_dir.glob("mcp_calls_*.log"))
    assert log_files, (
        f"Se esperaba al menos un archivo mcp_calls_*.log en {server._layout.logs_dir}. "
        "FileHandler debe crearse durante __init__."
    )


def test_env_var_enables_stderr_handler(tmp_path: Path, monkeypatch):
    """Con CORTEX_MCP_LOG_TO_STDERR=1, basicConfig recibe un StreamHandler(stderr).

    Nota: verificamos lo que el server *intenta* configurar (que es lo unico
    que controla). Subcomponentes posteriores como AgentMemory pueden
    reconfigurar handlers, pero esa es responsabilidad de esos componentes,
    no de la Capa 2 que estamos validando.
    """
    monkeypatch.setenv("CORTEX_MCP_LOG_TO_STDERR", "1")

    captured = {}

    real_basic_config = logging.basicConfig

    def spy(*args, **kwargs):
        captured["handlers"] = list(kwargs.get("handlers", []))
        return real_basic_config(*args, **kwargs)

    with patch("cortex.mcp.server.logging.basicConfig", side_effect=spy):
        _instantiate_server(tmp_path)

    handlers = captured.get("handlers", [])
    stderr_handlers = [
        h for h in handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
        and getattr(h, "stream", None) is sys.stderr
    ]
    assert stderr_handlers, (
        "Con CORTEX_MCP_LOG_TO_STDERR=1, basicConfig debe recibir un StreamHandler(sys.stderr). "
        f"handlers pasados: {handlers}"
    )


def test_env_var_other_value_does_not_enable(tmp_path: Path, monkeypatch):
    """CORTEX_MCP_LOG_TO_STDERR distinto de '1' NO debe activarlo."""
    monkeypatch.setenv("CORTEX_MCP_LOG_TO_STDERR", "true")  # not "1"

    captured = {}
    real_basic_config = logging.basicConfig

    def spy(*args, **kwargs):
        captured["handlers"] = list(kwargs.get("handlers", []))
        return real_basic_config(*args, **kwargs)

    with patch("cortex.mcp.server.logging.basicConfig", side_effect=spy):
        _instantiate_server(tmp_path)

    handlers = captured.get("handlers", [])
    stderr_handlers = [
        h for h in handlers
        if isinstance(h, logging.StreamHandler)
        and not isinstance(h, logging.FileHandler)
        and getattr(h, "stream", None) is sys.stderr
    ]
    assert not stderr_handlers, (
        "Solo el valor literal '1' debe activar el handler stderr (whitelist estricta). "
        f"handlers pasados: {handlers}"
    )
