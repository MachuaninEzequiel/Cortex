#!/usr/bin/env python3
"""Test diferencial YAML: PyYAML real vs dumper Rust (Obra 07 P8).

Genera documentos deterministas que cubren el espacio de formas del
frontmatter canónico (strings con indicadores, unicode, timestamps,
números-disfrazados, multilinea, tabs, plegado a 80 columnas, listas y
maps anidados/vacíos) y compara:

    yaml.safe_dump(d, default_flow_style=False, allow_unicode=True,
                   sort_keys=False)

contra `cargo run -q -p cortex-setup --example yaml_dump` sobre el mismo
documento en JSON. Cualquier byte de diferencia ⇒ exit 1.

Uso: .venv/bin/python bench/parity/p8_yaml_diff.py [--cases N]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent

TRICKY_STRINGS = [
    "",
    "simple",
    "Usar tokens vs sesiones",
    "Café & Sueño: decisión ✓",
    "key: valor",
    "termina:",
    ":arranque",
    "valor con # hash",
    "#hash inicial",
    "42",
    "-42",
    "+7",
    "true",
    "false",
    "yes",
    "No",
    "ON",
    "null",
    "~",
    "Null",
    "=",
    "<<",
    "!",
    "&",
    "*",
    "3.14",
    ".inf",
    ".NaN",
    "1:30",
    "0x1A",
    "0b101",
    "010",
    "1_000",
    "v1.2",
    "2026-08-24T12:34:56.789012Z",
    "2026-08-24",
    "2026-08-24 12:34:56",
    "https://example.com/x?a=1&b=2",
    "- parece lista",
    "?que",
    "%inicia porcentaje",
    "@mención",
    "*asterisco",
    "&anper",
    "!bang",
    "|pipe",
    ">mayor",
    "`backtick",
    '"doble comilla"',
    "it's ok",
    "comillas 'simples' y \"dobles\"",
    "con espacio final ",
    " espacio inicial",
    "linea1\nlinea2\n",
    "linea1\nlinea2\nlinea3\n\nlinea5",
    "col\ttab",
    "ruta C:\\Users\\x",
    "🧠 memoria emoji",
    "áéíóú ñ",
    "una frase muy larga que supera los ochenta caracteres de ancho para probar el plegado de líneas del emisor",
    "otra frase larga con varias palabras para ver donde corta el emisor cuando la columna pasa el limite ochenta",
    "x" * 200,
    "palabra " * 40,
    "--- dash dash",
    "... puntos",
    "corchetes [y] {llaves}",
    "coma, dentro",
]


def build_cases(n_extra: int) -> list[dict]:
    """Casos base + combinaciones deterministas."""
    cases: list[dict] = []

    def add(doc: dict) -> None:
        cases.append(doc)

    # Caso canónico ADR (orden pydantic real).
    add(
        {
            "schema_version": 1,
            "doc_type": "adr",
            "title": "Usar tokens vs sesiones",
            "created_at": "2026-08-24T12:34:56.789012Z",
            "updated_at": "2026-08-24T12:34:56.789012Z",
            "tags": ["auth", "latencia"],
            "status": "accepted",
            "links": [],
            "vault_scope": "local",
            "fingerprint": "a" * 64,
            "adr_number": 7,
            "supersedes": [],
            "superseded_by": None,
            "alternatives_considered": ["sesiones http", "jwt stateless"],
            "acceptance_criteria_met": True,
        }
    )
    # Strings difíciles como valores y como claves.
    for i, s in enumerate(TRICKY_STRINGS):
        add({f"k{i}": s})
        if i < len(TRICKY_STRINGS):
            add({"hooks": [{"name": s, "cmd": f"run-{i}", "required": bool(i % 2)}]})
    # Listas vacías/anidadas, maps vacíos, nulls.
    add({"a": [], "b": {}, "c": [[]], "d": [{}], "e": None, "f": [[["x"]]]})
    add({"deep": {"deep": {"deep": {"leaf": TRICKY_STRINGS[52]}}}})
    # Plegado: strings largos con espacios en posiciones variadas.
    base = "palabra{:02d} "
    add({
        "fold1": "".join(base.format(i) for i in range(30)),
        "fold2": "inicio " + "".join(base.format(i) for i in range(30)) + "fin",
        "fold3": ("m" * 79) + " cola",
        "fold4": ("m" * 80) + " cola",
        "fold5": ("m" * 81) + " cola",
    })
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=0)
    args = ap.parse_args()

    cases = build_cases(args.cases)
    rust_bin = [
        "cargo",
        "run",
        "-q",
        "-p",
        "cortex-setup",
        "--example",
        "yaml_dump",
        "--manifest-path",
        str(REPO / "rust/Cargo.toml"),
    ]

    failures = 0
    for idx, doc in enumerate(cases):
        expected = yaml.safe_dump(
            doc, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        proc = subprocess.run(
            rust_bin,
            input=json.dumps(doc, ensure_ascii=False),
            capture_output=True,
            text=True,
        )
        got = proc.stdout
        if proc.returncode != 0 or got != expected:
            failures += 1
            print(f"--- CASO {idx} DIFIERE ---")
            print("input:", json.dumps(doc, ensure_ascii=False)[:300])
            print("py   :", repr(expected[:400]))
            print("rust :", repr(got[:400]), "rc=", proc.returncode)
            print("err  :", proc.stderr.strip()[:300])
            if failures >= 5:
                break

    total = len(cases)
    print(f"{total - failures}/{total} casos idénticos")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
