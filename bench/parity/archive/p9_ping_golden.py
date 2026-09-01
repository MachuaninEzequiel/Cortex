#!/usr/bin/env python3
"""Oráculo P9: respuesta de ``cortex_ping`` para el server "bare".

Construye el mismo fixture que tests/unit/mcp/test_golden_contract.py
(``CortexMCPServer.__new__`` sin init) y captura ``_ping_text({})``.

Normalización pactada: ``uptime_seconds`` → {{UPTIME}} (varía por definición
entre corridas); TODO lo demás es byte-parity, incluida la serialización
json.dumps(indent=2, ensure_ascii=False).

Salida: bench/parity/golden_setup/ping/bare_ping.txt
El test Rust (cortex-mcp/tests/mcp_golden_contract.rs) reconstruye el
mismo fixture bare, normaliza su uptime y compara byte-a-byte.

Modo verify: .venv/bin/python bench/parity/p9_ping_golden.py --verify
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

OUT = REPO / "bench/parity/golden_setup/ping/bare_ping.txt"

UPTIME_RE = re.compile(r'"uptime_seconds": [0-9.eE+-]+')

from cortex.mcp.server import CortexMCPServer


def bare_server() -> CortexMCPServer:
    s = CortexMCPServer.__new__(CortexMCPServer)
    s._startup_time = __import__("datetime").datetime.now()
    s._error_history = deque(maxlen=10)
    return s


def normalized_ping() -> str:
    raw = bare_server()._ping_text({})
    return UPTIME_RE.sub('"uptime_seconds": {{UPTIME}}', raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        committed = OUT.read_text(encoding="utf-8")
        if committed == normalized_ping():
            print("VERIFY OK: ping bare reproducible")
            return 0
        print("VERIFY FAIL: ping bare difiere")
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = normalized_ping()
    OUT.write_text(payload, encoding="utf-8")
    print(f"OK: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
