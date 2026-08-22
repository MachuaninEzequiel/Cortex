#!/usr/bin/env python3
"""Generador determinista del vault sintético para benchmarks (Obra 03).

Misma seed → mismos bytes → misma fingerprint → mismo trabajo. El
dataset generado SE COMITEA (bench/datasets/vault-synth-1k/) para que
cualquier máquina mida sobre idéntico corpus.

Uso:
    .venv/bin/python bench/datasets/generate_vault.py [--docs 1000] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent

# Palabras ES/EN mezcladas: el corpus debe ejercitar el pipeline bilingüe.
PALABRAS = [
    "autenticacion", "despliegue", "memoria", "vector", "indice", "cache",
    "sesion", "checkpoint", "verificacion", "cobertura", "pipeline",
    "seguridad", "rendimiento", "latencia", "bateria",
    "embeddings", "retrieval", "webgraph", "vault", "governance", "policy",
    "rollback", "migracion", "schema", "chunking", "bm25", "cosine",
    "onnx", "quantization", "throughput", "workspace", "handoff",
    "spec", "adr", "runbook", "postmortem", "glossary", "changelog",
    "auth", "deploy", "memory", "search", "scoring", "budget",
]

# (subfolder, prefijo archivo, doc_type frontmatter, peso)
TIPOS = [
    ("decisions", "ADR-{n:03d}", "adr", 10),
    ("decisions", "DEC-{n:03d}", "decision", 10),
    ("runbooks", "RUNBOOK-{n:03d}", "runbook", 10),
    ("incidents", "INC-{n:03d}", "incident", 10),
    ("postmortems", "PM-{n:03d}", "postmortem", 5),
    ("specs", "SPEC-{n:03d}", "spec", 10),
    ("hu", "HU-{n}", "hu", 15),
    ("sessions", "{date}-{n:04d}-session", "session", 20),
    ("glossary", "GLOS-{n:03d}", "glossary", 5),
    ("changelog", "CHG-{n:03d}", "changelog", 5),
]


def _fecha(rng: random.Random) -> str:
    mes = rng.choice(["2026-07", "2026-08"])
    return f"{mes}-{rng.randint(1, 28):02d}"


def generar_doc(
    rng: random.Random, n: int, total_docs: int
) -> tuple[Path, str, str]:
    """Devuelve (ruta_relativa, contenido, título)."""
    subfolder, prefijo, doc_type, _ = rng.choices(
        TIPOS, weights=[t[3] for t in TIPOS], k=1
    )[0]
    fecha = _fecha(rng)
    nombre = prefijo.format(n=n, date=fecha)
    slug_kw = "-".join(rng.choice(PALABRAS) for _ in range(rng.randint(2, 3)))
    titulo = f"{nombre} {slug_kw}"

    tags = sorted(rng.sample(PALABRAS, k=rng.randint(2, 5)))

    parrafos = []
    for _ in range(rng.randint(3, 6)):
        largo = rng.randint(40, 90)
        parrafos.append(" ".join(rng.choice(PALABRAS) for _ in range(largo)))

    # Wikilinks a otros docs del mismo tipo (determinista).
    links = []
    for _ in range(rng.randint(1, 3)):
        otro = rng.randint(1, max(1, total_docs - 1))
        if otro != n:
            links.append(f"[[{prefijo.format(n=otro, date=fecha)}]]")

    fm = (
        "---\n"
        f'title: "{titulo}"\n'
        f"doc_type: {doc_type}\n"
        f"tags: [{', '.join(tags)}]\n"
        "status: accepted\n"
        f"created: {fecha}\n"
        "---\n\n"
    )
    cuerpo_md = "\n\n".join(parrafos)
    seccion_links = "\n".join(f"- {l}" for l in links) if links else "- (sin enlaces)"
    contenido = f"{fm}# {titulo}\n\n{cuerpo_md}\n\n## Relaciones\n\n{seccion_links}\n"

    return Path(subfolder) / f"{nombre}.md", contenido, titulo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    etiqueta = f"{args.docs // 1000}k" if args.docs >= 1000 else str(args.docs)
    vault_dir = DATASETS_DIR / f"vault-synth-{etiqueta}"

    if vault_dir.exists():
        raise SystemExit(
            f"{vault_dir} ya existe — el dataset es inmutable una vez "
            "commiteado; borrálo explícitamente si sabés lo que hacés."
        )

    titulos_por_ruta: dict[str, str] = {}
    for n in range(1, args.docs + 1):
        ruta_rel, contenido, titulo = generar_doc(rng, n, args.docs)
        destino = vault_dir / ruta_rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        titulos_por_ruta[ruta_rel.as_posix()] = titulo

    # Queries deterministas derivadas del corpus (para retrieve/bm25):
    # 200 queries tomando keywords de títulos espaciados uniformemente.
    claves = sorted(titulos_por_ruta)
    step = max(1, len(claves) // 200)
    queries = []
    for rel in claves[::step][:200]:
        terminos = [
            w for w in titulos_por_ruta[rel].replace("—", " ").split()
            if w.isalnum()
        ]
        queries.append({
            "query": " ".join(terminos[1:5]) or titulos_por_ruta[rel],
            "source_doc": rel,
        })
    (DATASETS_DIR / "queries-synth.json").write_text(
        json.dumps(
            {"seed": args.seed, "docs": args.docs, "queries": queries},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"OK: {args.docs} docs en {vault_dir}")
    print(f"OK: {len(queries)} queries en {DATASETS_DIR / 'queries-synth.json'}")


if __name__ == "__main__":
    main()
