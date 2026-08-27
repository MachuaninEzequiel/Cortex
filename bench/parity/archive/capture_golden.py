#!/usr/bin/env python3
"""Captura/verifica salidas doradas del CLI Python para paridad Obra 07 (P0).

Contrato (docs/transformacion/08-MIGRACION-TOTAL-RUST.md §3.2):
  - Los comandos se corren sobre el proyecto-fixture determinista.
  - La salida se normaliza: la ruta absoluta del fixture se reemplaza por
    ``{{ROOT}}`` y se garantiza un único ``\\n`` final. Todo lo demás debe ser
    byte-a-byte idéntico — incluido el ORDEN de las claves JSON.
  - Modo capture: escribe golden/<cmd>.out
  - Modo --verify: re-captura y compara contra lo commiteado; exit 1 si difiere.

Los comandos piloto son deliberadamente baratos (cero modelos, cero red):
  doctor            texto normalizado
  next --stats      JSON crudo normalizado
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_BIN = REPO / ".venv" / "bin" / "cortex"

# (args, nombre-de-archivo, rc-permitidos)
# doctor en un fixture incompleto LEGÍTIMAMENTe sale !=0 (reporta FAILs);
# lo que fijamos es la SALIDA, no el código.
COMANDOS: list[tuple[list[str], str, set[int]]] = [
    (["doctor"], "doctor.txt", {0, 1}),
    (["next", "--stats"], "next_stats.json", {0}),
]


def normalizar(texto: str, fixture_root: Path) -> str:
    texto = texto.replace(str(fixture_root), "{{ROOT}}")
    return texto.rstrip("\n") + "\n"


def capturar(bin_cortex: Path, fixture: Path, args: list[str], rc_ok: set[int]) -> str:
    proc = subprocess.run(
        [str(bin_cortex), *args],
        cwd=fixture,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode not in rc_ok:
        raise RuntimeError(
            f"{args} exit={proc.returncode} (esperaba {sorted(rc_ok)}): "
            f"{proc.stderr.strip()[:300]}"
        )
    return normalizar(proc.stdout, fixture)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True, type=Path, help="proyecto fixture")
    ap.add_argument("--out", type=Path, default=REPO / "bench/parity/golden")
    ap.add_argument("--cortex-bin", type=Path, default=DEFAULT_BIN)
    ap.add_argument("--verify", action="store_true", help="comparar vs golden existente")
    ns = ap.parse_args()

    fixture = ns.fixture.resolve()
    if not (fixture / "config.yaml").exists():
        print(f"fixture inválido: {fixture}", file=sys.stderr)
        return 1

    ns.out.mkdir(parents=True, exist_ok=True)
    fallas = 0
    for args, nombre, rc_ok in COMANDOS:
        salida = capturar(ns.cortex_bin, fixture, args, rc_ok)
        destino = ns.out / nombre
        if ns.verify:
            esperado = destino.read_text(encoding="utf-8")
            if salida == esperado:
                print(f"[PASS] {nombre}")
            else:
                print(f"[FAIL] {nombre} difiere del golden ({destino})")
                fallas += 1
        else:
            destino.write_text(salida, encoding="utf-8")
            print(f"[capturado] {nombre} → {destino}")

    if ns.verify and fallas == 0:
        print("PARIDAD OK")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
