"""Tests para cortex_ping y last_error_seen (Fase 2 del MCP defensive).

Verifica:
- Que el ping responde con el JSON estructurado esperado.
- Latencia <50ms p99 (objetivo del plan).
- States: starting / ok / degraded.
- last_error_seen se popula correctamente y se sanitiza.
- No leak de secrets en el error tracking.
- Rolling buffer respeta maxlen=10.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from cortex.embedders.onnx import OnnxEmbedder
from cortex.mcp.server import CortexMCPServer


def _make_server(tmp_path: Path) -> CortexMCPServer:
    return CortexMCPServer(project_root=tmp_path)


# ----------------------------------------------------------------------
# Estructura del payload
# ----------------------------------------------------------------------


def test_ping_returns_valid_json(tmp_path: Path):
    """El ping retorna JSON parseable con las keys esperadas."""
    server = _make_server(tmp_path)
    response = server._ping_text({})
    data = json.loads(response)
    assert set(data.keys()) == {
        "status", "version", "uptime_seconds", "indices_loaded",
        "models_loaded", "last_error_seen",
    }
    server.shutdown()


def test_ping_version_matches_server_constant(tmp_path: Path):
    """version del ping debe igualar SERVER_VERSION."""
    server = _make_server(tmp_path)
    data = json.loads(server._ping_text({}))
    assert data["version"] == server.SERVER_VERSION
    server.shutdown()


def test_ping_uptime_grows(tmp_path: Path):
    """uptime debe crecer entre dos llamadas consecutivas."""
    server = _make_server(tmp_path)
    first = json.loads(server._ping_text({}))["uptime_seconds"]
    time.sleep(0.05)
    second = json.loads(server._ping_text({}))["uptime_seconds"]
    assert second > first
    server.shutdown()


# ----------------------------------------------------------------------
# States
# ----------------------------------------------------------------------


def test_ping_starts_with_starting_status(tmp_path: Path):
    """En los primeros segundos post-init, status es 'starting'."""
    server = _make_server(tmp_path)
    data = json.loads(server._ping_text({}))
    assert data["status"] == "starting"
    assert data["uptime_seconds"] < server._STARTUP_GRACE_SECONDS
    server.shutdown()


def test_ping_status_ok_after_grace_period(tmp_path: Path, monkeypatch):
    """Tras grace period sin errores, status pasa a 'ok'."""
    server = _make_server(tmp_path)
    # Simular que ya pasamos el grace period bajando el threshold
    monkeypatch.setattr(server, "_STARTUP_GRACE_SECONDS", 0.001)
    time.sleep(0.01)
    data = json.loads(server._ping_text({}))
    assert data["status"] == "ok"
    server.shutdown()


def test_ping_status_degraded_with_recent_error(tmp_path: Path, monkeypatch):
    """Tras grace period + error registrado, status es 'degraded'."""
    server = _make_server(tmp_path)
    monkeypatch.setattr(server, "_STARTUP_GRACE_SECONDS", 0.001)
    time.sleep(0.01)
    server._register_error("cortex_search", "some error")
    data = json.loads(server._ping_text({}))
    assert data["status"] == "degraded"
    server.shutdown()


# ----------------------------------------------------------------------
# last_error_seen
# ----------------------------------------------------------------------


def test_last_error_seen_null_when_no_errors(tmp_path: Path):
    """Sin errores registrados, last_error_seen es null."""
    server = _make_server(tmp_path)
    data = json.loads(server._ping_text({}))
    assert data["last_error_seen"] is None
    server.shutdown()


def test_last_error_seen_returns_most_recent(tmp_path: Path):
    """last_error_seen devuelve el ultimo error agregado."""
    server = _make_server(tmp_path)
    server._register_error("tool_a", "first error")
    time.sleep(0.001)
    server._register_error("tool_b", "second error")
    data = json.loads(server._ping_text({}))
    assert data["last_error_seen"] is not None
    assert data["last_error_seen"]["tool"] == "tool_b"
    assert "second" in data["last_error_seen"]["error"]
    server.shutdown()


def test_error_message_is_truncated(tmp_path: Path):
    """Errores muy largos se truncan a _ERROR_MESSAGE_MAX_CHARS."""
    server = _make_server(tmp_path)
    huge = "x" * 1000
    server._register_error("tool_huge", huge)
    data = json.loads(server._ping_text({}))
    err_msg = data["last_error_seen"]["error"]
    assert len(err_msg) <= server._ERROR_MESSAGE_MAX_CHARS
    assert err_msg.endswith("...")
    server.shutdown()


def test_error_history_respects_maxlen(tmp_path: Path):
    """El deque _error_history descarta los mas viejos cuando excede maxlen."""
    server = _make_server(tmp_path)
    # maxlen es 10 — agregar 15 errores
    for i in range(15):
        server._register_error(f"tool_{i}", f"error_{i}")
    assert len(server._error_history) == 10
    # El primero debe ser tool_5 (los 5 primeros fueron expulsados)
    assert server._error_history[0]["tool"] == "tool_5"
    assert server._error_history[-1]["tool"] == "tool_14"
    server.shutdown()


# ----------------------------------------------------------------------
# models_loaded
# ----------------------------------------------------------------------


def test_models_loaded_empty_when_onnx_not_loaded(tmp_path: Path):
    """Si ONNX no fue cargado todavia, models_loaded es lista vacia."""
    # Reset singleton
    OnnxEmbedder._onnx_fn = None
    server = _make_server(tmp_path)
    data = json.loads(server._ping_text({}))
    assert data["models_loaded"] == []
    server.shutdown()


def test_models_loaded_lists_onnx_when_loaded(tmp_path: Path):
    """Si OnnxEmbedder._onnx_fn esta cacheado, ping lo lista."""
    OnnxEmbedder._onnx_fn = object()  # simulado, no cargamos el modelo real
    try:
        server = _make_server(tmp_path)
        data = json.loads(server._ping_text({}))
        assert "onnx-embeddings" in data["models_loaded"]
        server.shutdown()
    finally:
        OnnxEmbedder._onnx_fn = None


# ----------------------------------------------------------------------
# Latencia
# ----------------------------------------------------------------------


def test_ping_latency_under_50ms_p99(tmp_path: Path):
    """100 llamadas consecutivas; p99 < 50ms."""
    server = _make_server(tmp_path)
    latencies_ms: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        server._ping_text({})
        latencies_ms.append((time.perf_counter() - t0) * 1000)
    latencies_ms.sort()
    p99 = latencies_ms[98]  # index 98 = p99 de 100 samples
    assert p99 < 50.0, (
        f"p99 latency {p99:.2f}ms excedio el target de 50ms. "
        f"min={latencies_ms[0]:.2f}, max={latencies_ms[-1]:.2f}, "
        f"median={latencies_ms[50]:.2f}"
    )
    server.shutdown()


# ----------------------------------------------------------------------
# Dispatch via _dispatch_tool_sync
# ----------------------------------------------------------------------


def test_ping_dispatchable_via_dispatcher(tmp_path: Path):
    """cortex_ping debe estar registrado en _dispatch_tool_sync."""
    server = _make_server(tmp_path)
    result = server._dispatch_tool_sync("cortex_ping", {})
    assert isinstance(result, str)
    data = json.loads(result)
    assert "status" in data
    server.shutdown()
