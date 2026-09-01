#!/usr/bin/env python3
"""Captura/verifica goldens de config (P1) — espejo de capture_golden.py.

Para cada YAML en fixtures_config/ corre el oráculo config_dump.py y guarda
golden_config/<stem>.json. --verify re-corre y compara byte-a-byte.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures_config"
GOLDEN = Path(__file__).resolve().parent / "golden_config"
ORACLE = Path(__file__).resolve().parent / "config_dump.py"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ns = ap.parse_args()

    yamls = sorted(FIXTURES.glob("*.yaml"))
    if not yamls:
        print("sin fixtures", file=sys.stderr)
        return 1

    GOLDEN.mkdir(parents=True, exist_ok=True)
    fallas = 0
    for yml in yamls:
        proc = subprocess.run(
            [sys.executable, str(ORACLE), str(yml)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            print(f"[ERROR] {yml.name}: {proc.stderr.strip()[:200]}")
            fallas += 1
            continue
        salida = proc.stdout.rstrip("\n") + "\n"
        destino = GOLDEN / (yml.stem + ".json")
        if ns.verify:
            esperado = destino.read_text(encoding="utf-8")
            if salida == esperado:
                print(f"[PASS] {destino.name}")
            else:
                print(f"[FAIL] {destino.name} difiere del golden")
                fallas += 1
        else:
            destino.write_text(salida, encoding="utf-8")
            print(f"[capturado] {destino.name}")

    if ns.verify and fallas == 0:
        print("PARIDAD OK")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
