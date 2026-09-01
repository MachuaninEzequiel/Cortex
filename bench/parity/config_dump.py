#!/usr/bin/env python3
"""Oráculo de paridad P1: dump canónico de CortexConfig (Obra 07).

Carga un config.yaml con el modelo Pydantic REAL de cortex/core.py y emite
JSON canónico. La implementación Rust (crates/cortex-config) debe producir
bytes idénticos para el mismo YAML.

Forma del dump (orden fijo):
  ok                    bool    (false si la validación falla)
  warnings              [str]   mensajes de warnings.warn en orden
  config                objeto  model_dump completo, orden de declaración;
                                per_language con claves SORTED (canónico)
  embedding_block_active bool
  resolved_embedder     {"default":[model,backend],"es":[…],"en":[…],"fr":[…]}

Convenciones de serialización (deben espejarse en Rust):
  json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import yaml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ns = ap.parse_args()

    raw = yaml.safe_load(ns.config.read_text(encoding="utf-8")) or {}

    from cortex.core import CortexConfig, embedding_block_active, resolve_embedder

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            config = CortexConfig.model_validate(raw)
        except Exception:
            print(json.dumps({"ok": False}, indent=2, ensure_ascii=False))
            return 0

    dump = config.model_dump()
    # Canonical: per_language siempre sorted (HashMap/BTreeMap del lado Rust).
    if isinstance(dump["embedding"]["per_language"], dict):
        dump["embedding"]["per_language"] = dict(
            sorted(dump["embedding"]["per_language"].items())
        )

    out = {
        "ok": True,
        "warnings": [str(w.message) for w in caught],
        "config": dump,
        "embedding_block_active": embedding_block_active(config),
        "resolved_embedder": {
            "default": list(resolve_embedder(config)),
            "es": list(resolve_embedder(config, "es")),
            "en": list(resolve_embedder(config, "en")),
            "fr": list(resolve_embedder(config, "fr")),
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
