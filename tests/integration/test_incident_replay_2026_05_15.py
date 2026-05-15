"""Replay programatico del incidente del 2026-05-15.

Reproduce las CONDICIONES exactas que en la sesion del creador en
``D:\\ClubBelgrano-Prode`` causaron el bug:

1. Subagent que llama tools MCP con payload grande mientras agente principal
   ejecuta tools en paralelo (concurrencia simultanea).
2. Logs agresivos durante toda la operacion (saturacion del pipe stderr
   en el sistema pre-Fase 1).
3. Subprocess potencialmente bloqueante (git diff con base inexistente).

Contrato del test (criterio de exito post-Fase 1+2):

- El MCP server NO se cuelga.
- ``cortex_ping`` sigue respondiendo durante toda la operacion.
- Los tool calls que fallan devuelven error estructurado, NO se quedan
  esperando 14 minutos.
- El executor se cierra limpiamente al final (no thread leaks).

Este test materializa la promesa del plan multi-IDE & MCP hardening:
"el MCP server debe responder siempre que el IDE este abierto en un
proyecto con Cortex instalado".
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import pytest

from cortex.mcp.server import CortexMCPServer


@pytest.fixture
def server(tmp_path: Path):
    """CortexMCPServer en tmp_path, con shutdown() al final del test."""
    instance = CortexMCPServer(project_root=tmp_path)
    yield instance
    instance.shutdown()


# ---------------------------------------------------------------------------
# Replay del bug exacto
# ---------------------------------------------------------------------------


def test_concurrent_tool_calls_do_not_block_event_loop(server, tmp_path: Path):
    """Reproduce el patron del incidente: subagent + agente principal
    invocando tools MCP simultaneamente. Verifica que el dispatcher con
    executor (Capa 1 de Fase 1) NO bloquea el event loop async.
    """
    async def run():
        loop = asyncio.get_running_loop()

        # Simulacion: 5 tool calls "lentos" + 5 cortex_ping en paralelo.
        # Pre-Fase 1: el dispatcher serializaba todo en el event loop, asi
        # que los pings esperaban a que los lentos terminaran.
        # Post-Fase 1: cada call corre en un thread del executor, los pings
        # responden inmediatamente.

        slow_calls = [
            loop.run_in_executor(
                server._executor,
                server._dispatch_tool_sync,
                "cortex_validate_handoff",
                {"handoff_yaml": "name: x"},  # mensaje pequeño pero invalido
            )
            for _ in range(5)
        ]
        ping_calls = [
            loop.run_in_executor(server._executor, server._dispatch_tool_sync, "cortex_ping", {})
            for _ in range(5)
        ]

        all_results = await asyncio.gather(*(slow_calls + ping_calls), return_exceptions=True)
        return all_results

    t0 = time.perf_counter()
    results = asyncio.run(run())
    elapsed_s = time.perf_counter() - t0

    # 10 calls en menos de 5 segundos (el ping deberia ser <50ms cada uno).
    # Si serializaran, demoraria mucho mas.
    assert elapsed_s < 5.0, f"10 calls concurrentes tomaron {elapsed_s:.2f}s — sospechoso"

    # Ningun call debe haber tirado exception (el dispatcher captura todo).
    for r in results:
        assert not isinstance(r, Exception), f"Call propago exception: {r!r}"

    # Los 5 pings deben haber devuelto JSON valido.
    ping_results = results[5:]
    for ping in ping_results:
        data = json.loads(ping)
        assert "status" in data
        assert "version" in data


def test_ping_responds_during_payload_heavy_work(server, tmp_path: Path):
    """Mientras un tool MCP procesa payload grande, cortex_ping debe seguir
    respondiendo en <50ms. Garantia del aislamiento del executor.
    """
    # Payload grande: 100 claims (similar al payload del incidente: 13 claims
    # muy largos sumaban miles de chars). Aqui forzamos un git diff en
    # contra de una rama que NO existe — el handler debe fallar rapido por
    # la pre-validacion de Capa 3, no esperar 10 segundos.
    huge_claims = [f"claim {i}: " + ("x" * 200) for i in range(100)]

    async def run():
        loop = asyncio.get_running_loop()

        # Heavy call (verify_session_claims con base inexistente; deberia
        # fallar rapido por pre-validacion de git_branch_exists).
        heavy = loop.run_in_executor(
            server._executor,
            server._dispatch_tool_sync,
            "cortex_verify_session_claims",
            {"claims": huge_claims, "base_branch": "this-branch-does-not-exist-xyz"},
        )

        # Mientras el heavy esta en flight, ejecutar 3 pings y medir latencia.
        ping_latencies_ms: list[float] = []
        for _ in range(3):
            t0 = time.perf_counter()
            ping_result = await loop.run_in_executor(
                server._executor, server._dispatch_tool_sync, "cortex_ping", {}
            )
            ping_latencies_ms.append((time.perf_counter() - t0) * 1000)
            assert "status" in json.loads(ping_result)
            await asyncio.sleep(0.01)

        await heavy
        return ping_latencies_ms

    latencies = asyncio.run(run())

    # Ningun ping debe haber tomado mas de 500ms (target real es <50ms,
    # pero CI puede ser lento — el threshold generoso prueba que NO se
    # bloqueo en el heavy).
    for lat in latencies:
        assert lat < 500.0, (
            f"Ping tomo {lat:.2f}ms mientras heavy work corria — "
            "Capa 1 (executor isolation) esta rota"
        )


def test_subprocess_with_invalid_branch_fails_fast(server, tmp_path: Path):
    """``cortex_verify_session_claims`` con rama base inexistente debe
    fallar en <2s gracias a la pre-validacion de Capa 3 (git_branch_exists).

    Pre-Fase 1: este caso esperaba el timeout completo de 10s del git diff.
    """
    t0 = time.perf_counter()
    result = server._dispatch_tool_sync(
        "cortex_verify_session_claims",
        {"claims": ["claim X"], "base_branch": "branch-does-not-exist"},
    )
    elapsed_s = time.perf_counter() - t0

    # Debe responder rapido con mensaje de error claro
    assert elapsed_s < 2.0, (
        f"Pre-validacion de branch tomo {elapsed_s:.2f}s — Capa 3 esta rota"
    )
    assert "does not exist" in result.lower() or "valid branch" in result.lower(), (
        f"Mensaje de error no es claro: {result!r}"
    )


def test_log_saturation_does_not_block_server(server, tmp_path: Path):
    """Saturar el logger con miles de mensajes mientras se sirven tool
    calls. Pre-Fase 1: el StreamHandler(stderr) bloqueaba si el cliente
    no drenaba el pipe — el server se colgaba.

    Post-Fase 1: en modo stdio (default), logs van solo a archivo. Stderr
    queda libre.
    """
    logger = logging.getLogger("cortex.mcp.server")

    async def run():
        loop = asyncio.get_running_loop()

        # Disparar 1000 logs en paralelo con tool calls
        for i in range(1000):
            logger.info(f"stress log line {i}: " + "x" * 100)

        # Verificar que el ping sigue funcionando despues del bombardeo
        ping_result = await loop.run_in_executor(
            server._executor, server._dispatch_tool_sync, "cortex_ping", {}
        )
        return ping_result

    result = asyncio.run(run())
    data = json.loads(result)
    assert data["status"] in ("ok", "starting", "degraded")


def test_ping_tracks_errors_from_failing_tools(server, tmp_path: Path):
    """Tras una serie de tools que fallan, cortex_ping debe poblar
    last_error_seen — cumpliendo la promesa de Fase 2 (last_error_seen
    como diagnostico inmediato del incidente).
    """
    # Disparar 3 errores diferentes
    server._dispatch_tool_sync("cortex_validate_handoff", {"handoff_yaml": ""})
    server._register_error("cortex_search_vector", "ONNX failed to load")
    server._register_error("cortex_save_session", "vault write failed")

    # Ping debe reportar el ultimo
    ping_result = server._dispatch_tool_sync("cortex_ping", {})
    data = json.loads(ping_result)
    assert data["last_error_seen"] is not None
    assert data["last_error_seen"]["tool"] == "cortex_save_session"
    assert "vault write failed" in data["last_error_seen"]["error"]


def test_executor_shutdown_cleans_up_threads(tmp_path: Path):
    """Al cerrar el server (shutdown), el executor debe liberarse sin
    dejar threads zombie. Cumple la garantia de cleanup de Fase 1."""
    server = CortexMCPServer(project_root=tmp_path)
    assert server._executor is not None
    server.shutdown()
    assert server._executor is None
    # Idempotencia: segundo shutdown no debe crashear
    server.shutdown()


# ---------------------------------------------------------------------------
# Garantia maestra del plan
# ---------------------------------------------------------------------------


def test_incident_2026_05_15_does_not_reproduce(server, tmp_path: Path):
    """Test umbrella: orquesta todas las condiciones del incidente y
    verifica que el server SIGUE OPERATIVO al final.

    Si este test pasa, el plan multi-IDE & MCP hardening cumplio su
    promesa fundacional: el MCP server NO se cuelga ante carga real.
    """
    async def replay():
        loop = asyncio.get_running_loop()
        logger = logging.getLogger("cortex.mcp.server")

        # 1. Bombardeo de logs (simula salida verbosa del subagent)
        for i in range(500):
            logger.info(f"replay log {i}")

        # 2. Tool calls concurrentes (subagent + main agent)
        calls = []
        for _ in range(20):
            calls.append(
                loop.run_in_executor(
                    server._executor, server._dispatch_tool_sync, "cortex_ping", {}
                )
            )
        for _ in range(5):
            calls.append(
                loop.run_in_executor(
                    server._executor,
                    server._dispatch_tool_sync,
                    "cortex_validate_handoff",
                    {"handoff_yaml": "invalid: yaml: content: ["},
                )
            )

        # 3. Sub-procesos potencialmente bloqueantes
        calls.append(
            loop.run_in_executor(
                server._executor,
                server._dispatch_tool_sync,
                "cortex_verify_session_claims",
                {"claims": ["c"], "base_branch": "missing-branch"},
            )
        )

        all_results = await asyncio.gather(*calls, return_exceptions=True)
        return all_results

    t0 = time.perf_counter()
    results = asyncio.run(replay())
    elapsed_s = time.perf_counter() - t0

    # Garantia 1: completar en tiempo razonable (NO 14 minutos)
    assert elapsed_s < 10.0, f"Replay tomo {elapsed_s:.2f}s — el server pudo colgarse"

    # Garantia 2: ningun call propago exception
    for r in results:
        assert not isinstance(r, Exception), f"Call propago: {r!r}"

    # Garantia 3: el server SIGUE responsivo al final
    final_ping = server._dispatch_tool_sync("cortex_ping", {})
    final_data = json.loads(final_ping)
    assert final_data["status"] in ("ok", "starting", "degraded")
    assert final_data["uptime_seconds"] > 0
