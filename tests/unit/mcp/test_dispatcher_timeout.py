"""Tests para el dispatch con ThreadPoolExecutor + timeout (Capa 1)."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import patch

from cortex.mcp.server import CortexMCPServer


def _make_server(tmp_path: Path) -> CortexMCPServer:
    return CortexMCPServer(project_root=tmp_path)


def test_dispatch_sync_returns_string_for_unknown_tool(tmp_path: Path):
    """Tool desconocida devuelve string de error, no propaga exception."""
    server = _make_server(tmp_path)
    result = server._dispatch_tool_sync("non-existent-tool", {})
    assert isinstance(result, str)
    assert "desconocida" in result.lower()


def test_dispatch_sync_returns_string_for_known_tool(tmp_path: Path):
    """Tool conocida devuelve string. Smoke test del dispatcher sin executor."""
    server = _make_server(tmp_path)
    # cortex_validate_handoff requires handoff_yaml; con string vacio devuelve un mensaje de error pero NO crashea
    result = server._dispatch_tool_sync("cortex_validate_handoff", {"handoff_yaml": ""})
    assert isinstance(result, str)
    assert "required" in result.lower() or "handoff" in result.lower()


def test_tool_timeouts_table_has_expected_keys(tmp_path: Path):
    """La tabla de timeouts por tool debe tener overrides para tools lentas conocidas."""
    server = _make_server(tmp_path)
    assert server._TOOL_TIMEOUT_DEFAULT > 0
    # cortex_search_vector carga ONNX la primera vez; debe tener timeout mayor.
    assert server._TOOL_TIMEOUTS.get("cortex_search_vector", 0) > server._TOOL_TIMEOUT_DEFAULT
    # cortex_sync_vault hace indexacion masiva; idem.
    assert server._TOOL_TIMEOUTS.get("cortex_sync_vault", 0) > server._TOOL_TIMEOUT_DEFAULT


def test_executor_is_initialized(tmp_path: Path):
    """El executor debe existir post-init y ser un ThreadPoolExecutor."""
    import concurrent.futures
    server = _make_server(tmp_path)
    assert isinstance(server._executor, concurrent.futures.ThreadPoolExecutor)


def test_shutdown_releases_executor(tmp_path: Path):
    """shutdown() cierra el executor y lo deja en None (idempotente)."""
    server = _make_server(tmp_path)
    assert server._executor is not None
    server.shutdown()
    assert server._executor is None


def test_shutdown_is_idempotent(tmp_path: Path):
    """Llamar shutdown() dos veces no rompe nada."""
    server = _make_server(tmp_path)
    server.shutdown()
    server.shutdown()  # NO debe lanzar exception
    assert server._executor is None


def test_executor_isolates_blocking_tool(tmp_path: Path):
    """Verificar que dispatch_tool_sync corre en thread (no bloquea event loop).

    Aprovecho que el executor existe y simulo: corro dispatch_tool_sync en
    el executor con un tool que duerme via monkeypatch, y verifico que
    el event loop sigue libre para correr otra tarea en paralelo.
    """
    server = _make_server(tmp_path)

    blocking_calls = []
    parallel_executed = []

    def slow_handler(arguments: dict) -> str:
        blocking_calls.append(time.time())
        time.sleep(0.3)
        return "slow result"

    async def run():
        loop = asyncio.get_running_loop()

        # Patcheo _search_text_dispatch para que sea lento
        with patch.object(server, "_search_text_dispatch", side_effect=slow_handler):
            # Lanzo el slow handler en el executor
            future = loop.run_in_executor(
                server._executor,
                server._dispatch_tool_sync,
                "cortex_search",
                {"query": "test"},
            )

            # Mientras el slow corre en el thread, el event loop debe poder
            # ejecutar otras corrutinas sin esperar al slow.
            await asyncio.sleep(0.05)
            parallel_executed.append(time.time())

            result = await asyncio.wait_for(future, timeout=2.0)
            return result

    result = asyncio.run(run())

    assert result == "slow result"
    assert len(blocking_calls) == 1
    assert len(parallel_executed) == 1
    # El parallel_executed timestamp debe ser ANTES o muy cerca del fin del slow,
    # demostrando que el event loop NO se bloqueo en el slow.
    assert parallel_executed[0] - blocking_calls[0] < 0.2, (
        "El event loop se bloqueo mientras el slow corria en el executor. "
        "El aislamiento no funciona."
    )
