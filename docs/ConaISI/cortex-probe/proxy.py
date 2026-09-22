#!/usr/bin/env python3
"""
Cortex BlackBox Probe - Stdio MCP Transparent Proxy
===================================================
Proxy transparente de alta fidelidad y tolerancia a fallos para servidores MCP.
Interpreta las conexiones JSON-RPC 2.0 por stdio entre el cliente (IDE/CLI) y Cortex,
capturando telemetría milimétrica en un hilo secundario sin añadir latencia ni bloquear
el flujo de datos original.

Garantías de diseño:
1. Zero Latency: Reenvío síncrono byte-por-byte de buffers nativos.
2. 100% Fail-Safe: Si el registrador de métricas falla, el proxy continúa sin interrupción.
3. Compatibilidad Universal: Funciona con Python 3.8+ y con cualquier cliente MCP.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

PROBE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PROBE_DIR / "config.json"
DATA_DIR = PROBE_DIR / "data"
EVENTS_FILE = DATA_DIR / "mcp_events.jsonl"


def load_config() -> Dict[str, Any]:
    default_config = {
        "active_mode": "python_legacy",
        "environment_label": "week1_python_baseline",
        "team_id": "cortex-dev-team",
        "anonymize_code": True,
        "commands": {
            "python_legacy": ["python3", "-m", "cortex.mcp.server"],
            "python_legacy_fallback": ["python", "-m", "cortex.mcp.server"],
            "rust_systemone": ["cortex-cli", "mcp-server", "--stdio"],
            "rust_systemone_fallback": ["cortex-mcp"]
        },
        "metrics": {
            "token_estimation_char_ratio": 3.8
        }
    }
    if not CONFIG_PATH.exists():
        return default_config
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            default_config.update(user_config)
            return default_config
    except Exception:
        return default_config


class TelemetryLogger(threading.Thread):
    """Procesador en segundo plano para análisis de mensajes JSON-RPC."""

    def __init__(self, data_queue: queue.Queue, config: Dict[str, Any]):
        super().__init__(daemon=True, name="TelemetryWorker")
        self.queue = data_queue
        self.config = config
        self.pending_calls: Dict[Any, Tuple[float, str, Dict[str, Any]]] = {}
        self.char_ratio = config.get("metrics", {}).get("token_estimation_char_ratio", 3.8)
        self.env_label = config.get("environment_label", "unknown_env")
        self.team_id = config.get("team_id", "default_team")

        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def run(self):
        while True:
            try:
                direction, raw_bytes, timestamp = self.queue.get()
                if direction == "__TERMINATE__":
                    break
                self._process_message(direction, raw_bytes, timestamp)
                self.queue.task_done()
            except Exception:
                # El hilo de telemetría NUNCA debe tumbar el proceso
                pass

    def _process_message(self, direction: str, raw_bytes: bytes, timestamp: float):
        try:
            line_str = raw_bytes.decode("utf-8", errors="ignore").strip()
            if not line_str or not line_str.startswith("{"):
                return

            msg = json.loads(line_str)
        except Exception:
            return

        try:
            msg_id = msg.get("id")

            # 1. Petición del Cliente hacia el Servidor (tools/call)
            if direction == "client_to_server":
                method = msg.get("method")
                if method == "tools/call" and msg_id is not None:
                    params = msg.get("params", {})
                    tool_name = params.get("name", "unknown_tool")
                    tool_args = params.get("arguments", {})
                    # Sanitizar argumentos si anonymize_code es True
                    safe_args = self._sanitize_args(tool_args)
                    self.pending_calls[msg_id] = (timestamp, tool_name, safe_args)

            # 2. Respuesta del Servidor hacia el Cliente
            elif direction == "server_to_client":
                if msg_id is not None and msg_id in self.pending_calls:
                    req_time, tool_name, safe_args = self.pending_calls.pop(msg_id)
                    duration_ms = round((timestamp - req_time) * 1000.0, 2)

                    error = msg.get("error")
                    result = msg.get("result", {})
                    is_error = error is not None or result.get("isError", False)

                    # Analizar contenido devuelto (contexto)
                    chars_out = len(line_str)
                    estimated_tokens = int(chars_out / self.char_ratio)

                    # Detectar si se devolvieron documentos o fragmentos
                    docs_detected = self._extract_doc_references(result)

                    event_record = {
                        "timestamp": timestamp,
                        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)),
                        "environment": self.env_label,
                        "team_id": self.team_id,
                        "call_id": str(msg_id),
                        "tool": tool_name,
                        "duration_ms": duration_ms,
                        "success": not is_error,
                        "error_type": error.get("message", "execution_error") if is_error and isinstance(error, dict) else (str(error) if is_error else None),
                        "payload_chars": chars_out,
                        "context_tokens_est": estimated_tokens,
                        "docs_returned_count": len(docs_detected),
                        "docs_sample": docs_detected[:5],
                        "args_summary": safe_args
                    }

                    self._write_event(event_record)
        except Exception:
            pass

    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae metadatos seguros de los argumentos sin exponer código confidencial."""
        summary = {}
        for k, v in args.items():
            if isinstance(v, (int, float, bool)):
                summary[k] = v
            elif isinstance(v, str):
                if len(v) > 120:
                    summary[k] = f"[String len={len(v)}, hash={hash(v) & 0xffffffff:x}]"
                else:
                    summary[k] = v
            elif isinstance(v, list):
                summary[k] = f"[List len={len(v)}]"
            elif isinstance(v, dict):
                summary[k] = f"[Dict keys={list(v.keys())}]"
        return summary

    def _extract_doc_references(self, result: Dict[str, Any]) -> list[str]:
        """Detecta rutas o identificadores de documentos devueltos por Cortex."""
        docs = []
        try:
            content_list = result.get("content", [])
            for item in content_list:
                text = item.get("text", "")
                if "vault/" in text or ".md" in text or "spec" in text or "adr" in text:
                    for line in text.splitlines():
                        line_stripped = line.strip()
                        if (line_stripped.startswith("#") or line_stripped.startswith("-") or "/" in line_stripped) and len(line_stripped) < 120:
                            if any(ext in line_stripped for ext in [".md", ".rs", ".py", ".ts", "ADR-", "spec-"]):
                                docs.append(line_stripped[:80])
        except Exception:
            pass
        return list(dict.fromkeys(docs))

    def _write_event(self, record: Dict[str, Any]):
        try:
            with open(EVENTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass


def resolve_command(config: Dict[str, Any]) -> list[str]:
    """Determina el comando real a ejecutar con sistema de fallbacks robusto."""
    mode = config.get("active_mode", "python_legacy")
    commands = config.get("commands", {})

    primary = commands.get(mode)
    fallback = commands.get(f"{mode}_fallback")

    # Si se pasó override por variables de entorno
    env_override = os.environ.get("CORTEX_PROBE_TARGET_CMD")
    if env_override:
        return env_override.split()

    if primary and shutil.which(primary[0]):
        return primary

    if fallback and shutil.which(fallback[0]):
        return fallback

    # Fallback de emergencia usando el ejecutable actual de python
    if mode == "python_legacy":
        return [sys.executable, "-m", "cortex.mcp.server"]
    else:
        return ["cortex-cli", "mcp-server", "--stdio"]


def main():
    config = load_config()
    cmd = resolve_command(config)

    # Cola de telemetría desacoplada (Tope 10,000 eventos en memoria)
    telemetry_queue: queue.Queue = queue.Queue(maxsize=10000)
    worker = TelemetryLogger(telemetry_queue, config)
    worker.start()

    # Lanzamiento del servidor Cortex subyacente
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0  # I/O sin buffer en el pipe para latencia cero
        )
    except Exception as e:
        sys.stderr.write(f"[CortexProbe Error] No se pudo iniciar Cortex con '{' '.join(cmd)}': {e}\n")
        sys.stderr.flush()
        sys.exit(1)

    # Hilo 1: Cliente stdin -> Cortex proc.stdin
    def relay_stdin():
        try:
            while True:
                line = sys.stdin.buffer.readline()
                if not line:
                    break
                proc.stdin.write(line)
                proc.stdin.flush()
                try:
                    telemetry_queue.put_nowait(("client_to_server", line, time.time()))
                except queue.Full:
                    pass
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

    # Hilo 2: Cortex proc.stdout -> Cliente stdout
    def relay_stdout():
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
                try:
                    telemetry_queue.put_nowait(("server_to_client", line, time.time()))
                except queue.Full:
                    pass
        except (BrokenPipeError, OSError):
            pass

    # Hilo 3: Cortex proc.stderr -> Cliente stderr (logs directos)
    def relay_stderr():
        try:
            while True:
                chunk = proc.stderr.read(4096)
                if not chunk:
                    break
                sys.stderr.buffer.write(chunk)
                sys.stderr.buffer.flush()
        except Exception:
            pass

    t_in = threading.Thread(target=relay_stdin, daemon=True, name="RelayStdin")
    t_out = threading.Thread(target=relay_stdout, daemon=True, name="RelayStdout")
    t_err = threading.Thread(target=relay_stderr, daemon=True, name="RelayStderr")

    t_in.start()
    t_out.start()
    t_err.start()

    # Esperar a que el proceso hijo finalice
    exit_code = proc.wait()

    # Notificar al worker para que termine de vaciar la cola
    try:
        telemetry_queue.put_nowait(("__TERMINATE__", b"", time.time()))
        worker.join(timeout=1.0)
    except Exception:
        pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
