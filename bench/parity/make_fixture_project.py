#!/usr/bin/env python3
"""Genera un proyecto Cortex determinista para fixtures de paridad (Obra 07 P0).

El proyecto es byte-a-byte reproducible: mismos archivos, mismo contenido,
sin git, sin chroma, sin estado externo. Todo comando capturado sobre ESTE
proyecto debe producir salida idéntica entre corridas y entre implementaciones
(Python hoy / Rust mañana).

Uso: python make_fixture_project.py <dir-destino>
"""

from __future__ import annotations

import sys
from pathlib import Path

CONFIG_YAML = """\
episodic:
  persist_dir: .memory/chroma
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2
  embedding_backend: onnx
semantic:
  vault_path: vault
retrieval:
  top_k: 5
"""

NOTA_A = """\
# Nota A

Contenido de prueba en espanol con suficiente texto para deteccion heuristica
de idioma. La memoria episodica guarda eventos y decisiones del proyecto con
timestamps y entidades tipadas para retrieval posterior.
"""

NOTE_B = """\
# Note B

English content for testing purposes with enough words for language detection.
The episodic memory stores project events and decisions with typed entities
and timestamps for later retrieval by agents.
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("uso: make_fixture_project.py <dir-destino>", file=sys.stderr)
        return 1
    root = Path(sys.argv[1]).resolve()
    (root / "vault").mkdir(parents=True, exist_ok=True)
    (root / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    (root / "vault" / "nota-a.md").write_text(NOTA_A, encoding="utf-8")
    (root / "vault" / "note-b.md").write_text(NOTE_B, encoding="utf-8")
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
