"""Stress test del MCP server — Fase 7 del plan multi-IDE & MCP hardening.

Forzar las condiciones extremas que en producción podrían tumbar el MCP:

- N invocaciones concurrentes de tools liviano (cortex_ping).
- Mix concurrente de tools rapidos + tools que potencialmente bloquean.
- Saturacion del logger durante operacion sostenida.

Criterio: el MCP server NO crashea, NO se desconecta, sigue respondiendo.

Estos tests son mas pesados que los smoke. Pueden ejecutarse menos
frecuentemente que la suite normal (marcados @pytest.mark.slow opcional).
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture
def server(tmp_path: Path):
    instance = CortexMCPServer(project_root=tmp_path)
    yield instance
    instance.shutdown()


def test_50_concurrent_pings(server, tmp_path: Path):
    """50 invocaciones concurrentes de cortex_ping. Cada una <50ms target."""
    async def run():
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(server._executor, server._dispatch_tool_sync, "cortex_ping", {})
            for _ in range(50)
        ]
        return await asyncio.gather(*tasks)

    t0 = time.perf_counter()
    results = asyncio.run(run())
    elapsed_s = time.perf_counter() - t0

    # 50 pings concurrentes con executor de 4 workers: ~12 batches x <50ms = <1s teorico.
    # Threshold generoso para CI lento.
    assert elapsed_s < 5.0, f"50 pings concurrentes tomaron {elapsed_s:.2f}s — sospechoso"

    # Todos devolvieron JSON valido
    assert len(results) == 50
    for r in results:
        data = json.loads(r)
        assert data["status"] in ("ok", "starting", "degraded")
        assert "version" in data


def test_mixed_workload_under_pressure(server, tmp_path: Path):
    """Mix de tools rapidos + tools potencialmente bloqueantes en paralelo.

    Garantia: el ping sigue respondiendo durante toda la operacion.
    """
    async def run():
        loop = asyncio.get_running_loop()
        tasks = []

        # 15 pings rapidos
        tasks.extend(
            loop.run_in_executor(server._executor, server._dispatch_tool_sync, "cortex_ping", {})
            for _ in range(15)
        )

        # 5 validate_handoff con YAML invalido (handler defensivo, NO crashea)
        tasks.extend(
            loop.run_in_executor(
                server._executor,
                server._dispatch_tool_sync,
                "cortex_validate_handoff",
                {"handoff_yaml": "invalid: [yaml"},
            )
            for _ in range(5)
        )

        # 3 verify_session_claims con base inexistente (fail-fast por Capa 3)
        tasks.extend(
            loop.run_in_executor(
                server._executor,
                server._dispatch_tool_sync,
                "cortex_verify_session_claims",
                {"claims": ["c1"], "base_branch": "no-such-branch"},
            )
            for _ in range(3)
        )

        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(run())

    # Todos los results son strings (handler estructurado), NO exceptions
    for r in results:
        assert not isinstance(r, Exception), f"Tool propago: {r!r}"
        assert isinstance(r, str), f"Result no es string: {type(r)}"


def test_repeated_invocation_does_not_leak_resources(server, tmp_path: Path):
    """500 invocaciones secuenciales de cortex_ping. El server debe seguir
    responsivo y la latencia no debe degradar significativamente."""
    latencies_ms: list[float] = []
    for _ in range(500):
        t0 = time.perf_counter()
        result = server._dispatch_tool_sync("cortex_ping", {})
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        json.loads(result)  # validar JSON

    # p99 debe estar dentro del target (relajado para CI)
    latencies_ms.sort()
    p50 = latencies_ms[250]
    p99 = latencies_ms[495]
    assert p50 < 50.0, f"p50={p50:.2f}ms — degradado"
    assert p99 < 200.0, f"p99={p99:.2f}ms — sospechoso de leak"


def test_error_history_stays_bounded_under_repeated_failures(server, tmp_path: Path):
    """Disparar 100 errores. La rolling buffer (maxlen=10) debe mantenerse
    acotada — sin memory leak."""
    for i in range(100):
        server._register_error(f"tool_{i}", f"error msg {i}")

    assert len(server._error_history) == 10  # maxlen respetado
    # Los 10 mas recientes (90-99)
    assert server._error_history[0]["tool"] == "tool_90"
    assert server._error_history[-1]["tool"] == "tool_99"


def test_server_survives_concurrent_burst_then_idle(server, tmp_path: Path):
    """Burst de carga seguido de idle: server debe seguir responsivo
    despues de relajar la carga."""
    async def run():
        loop = asyncio.get_running_loop()

        # Burst: 30 calls concurrentes
        burst = [
            loop.run_in_executor(server._executor, server._dispatch_tool_sync, "cortex_ping", {})
            for _ in range(30)
        ]
        await asyncio.gather(*burst)

        # Idle 100ms
        await asyncio.sleep(0.1)

        # Single ping post-burst — debe responder normal
        post = await loop.run_in_executor(
            server._executor, server._dispatch_tool_sync, "cortex_ping", {}
        )
        return post

    result = asyncio.run(run())
    data = json.loads(result)
    assert data["status"] in ("ok", "starting", "degraded")
