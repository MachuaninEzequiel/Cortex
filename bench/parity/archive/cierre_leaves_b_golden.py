#!/usr/bin/env python3
"""Golden BAJA DEFINITIVA RUTA 1 — MITAD B (ide ×4 + docs validate/restore/
list-backups/routing-table).

Compara el binario nativo `cortex-cli` contra el CLI Python REAL sobre un
fixture determinista (vault con 1 doc válido + 1 inválido, sub-proyectos
válido/sin-backups, backups reales creados por `cortex.documentation.backup`),
con normalizaciones pactadas SOLO:

- {{ROOT}}   : tmp del fixture
- {{TS}}     : timestamps ISO (drift de reloj; filenames de backups)
- {{ELAPSED}}, {{RUN}}, {{MEMID}}, {{SHA}}: no aplican a esta mitad
  (retenidas por el patrón del gate; no se añaden normalizaciones nuevas)
- scores a 4 decimales: idem (sin casos con scores).

Invocación Python: `.venv/bin/cortex` (console script). Motivo: los errores
typer (routing-table --doc-type inválido) llevan "Usage: cortex …" — con
`python -m cortex.cli.main` el programa se imprime como "python -m …" y la
paridad byte-a-byte es imposible sin hardcodear la invocación. El console
script es el "CLI Python REAL" para el usuario final (mismo app typer).

Modos:
  build  → congela la salida NORMALIZADA del CLI Python en golden_cierre_b.txt
  verify → corre ambos lados y compara normalizados (paridad byte-a-byte).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv" / "bin" / "cortex")
RS_DEFAULT = REPO / "rust" / "target" / "debug" / "cortex-cli"

ROOT_MARK = "{{ROOT}}"

FINGERPRINT = "a" * 64

VALID_DOC = (
    "---\ntitle: OK\ndoc_type: adr\nadr_number: 1\n"
    "created_at: 2026-08-01T10:00:00+00:00\n"
    "updated_at: 2026-08-01T10:00:00+00:00\nstatus: accepted\n"
    f"fingerprint: {FINGERPRINT}\n---\n\ncuerpo\n"
)
VALID_SPEC = (
    "---\ntitle: Auth\ndoc_type: spec\n"
    "created_at: 2026-08-01T10:00:00+00:00\n"
    "updated_at: 2026-08-01T10:00:00+00:00\nstatus: draft\n"
    f"fingerprint: {FINGERPRINT}\n---\n\nJWT\n"
)


def construir_fixture(root: Path) -> None:
    # Workspace principal.
    cortex = root / ".cortex"
    cortex.mkdir(parents=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\n", encoding="utf-8"
    )

    # Vault principal: 1 doc válido + 1 inválido (doc_type desconocido).
    vault = root / "vault"
    decisions = vault / "decisions"
    decisions.mkdir(parents=True)
    (decisions / "ADR-001-ok.md").write_text(VALID_DOC, encoding="utf-8")
    (decisions / "BROKEN.md").write_text(
        "---\ntitle: Broken\ndoc_type: weird\n---\n\ncuerpo\n", encoding="utf-8"
    )

    # Sub-proyecto con vault 100% válido (caso validate "vault válido").
    valid_proj = root / "valid-proj"
    (valid_proj / "vault" / "specs").mkdir(parents=True)
    (valid_proj / "vault" / "specs" / "auth.md").write_text(VALID_SPEC, encoding="utf-8")

    # Sub-proyecto sin .cortex/backups (caso list-backups vacío).
    no_backups = root / "no-backups"
    (no_backups / "vault").mkdir(parents=True)

    # Backups reales creados por el servicio Python (deterministas para
    # ambos lados: mismo archivo, mismo tamaño en build y verify). El sleep
    # evita colisión de timestamp (nombre con resolución de 1s) que haría
    # no-determinista el orden lexicográfico del listado. Congelamos mtimes
    # para que el .tar.gz (gzip con timestamp de los miembros) sea
    # byte-idéntico entre corridas ⇒ tamaño del listado determinista.
    import os
    import time
    from datetime import UTC, datetime

    fixed_ts = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC).timestamp()
    for p in sorted(vault.rglob("*")) + [vault]:
        os.utime(p, (fixed_ts, fixed_ts))

    from cortex.documentation.backup import create_backup

    create_backup(vault)
    time.sleep(1.1)
    create_backup(vault, label="keep")


def _run(binary: list[str], args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        binary + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env={**__import__("os").environ, "OMP_NUM_THREADS": "2"},
    )
    return proc.returncode, proc.stdout, proc.stderr


def normalize(text: str, root: Path) -> str:
    text = text.replace(str(root), ROOT_MARK)
    # Timestamps ISO (sufijo Z de backups/fixture) ⇒ {{TS}}.
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?",
        "{{TS}}",
        text,
    )
    # Filenames de backups del oráculo: strftime "%Y-%m-%dT%H%M%SZ" sin
    # dos puntos (vault-<ts>.tar.gz) — misma normalización {{TS}}.
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{6}Z", "{{TS}}", text)
    # SHAs de git / ids de 40 hex (contracto del patrón, sin casos propios).
    text = re.sub(r"\b[0-9a-f]{40}\b", "{{SHA}}", text)
    return text


def casos(root: Path) -> list[tuple[str, list[str]]]:
    backups = sorted((root / ".cortex" / "backups").glob("vault-*.tar.gz"))
    full_backup = str(backups[-1])
    r = lambda: str(root)  # noqa: E731
    return [
        ("B01 ide list texto", ["ide", "list"]),
        ("B02 ide list json", ["ide", "list", "--json"]),
        # Errores exactos del oráculo (raw, sin Typer panel para _fail).
        ("B03 ide setup sin --ide", ["ide", "setup", "--project-root", r()]),
        ("B04 ide status ide desconocido", ["ide", "status", "--ide", "nope", "--project-root", r()]),
        # Status sobre fixture limpio (texto + json + --ide).
        ("B05 ide status all texto", ["ide", "status", "--project-root", r()]),
        ("B06 ide status all json", ["ide", "status", "--project-root", r(), "--json"]),
        ("B07 ide status pi texto", ["ide", "status", "--ide", "pi", "--project-root", r()]),
        ("B08 ide status pi json", ["ide", "status", "--ide", "pi", "--project-root", r(), "--json"]),
        # docs validate: vault con issues + vault válido.
        ("B09 docs validate texto issues", ["docs", "validate", "--project-root", r()]),
        ("B10 docs validate json issues", ["docs", "validate", "--project-root", r(), "--json"]),
        ("B11 docs validate texto valido", ["docs", "validate", "--project-root", str(root / "valid-proj")]),
        ("B12 docs validate json valido", ["docs", "validate", "--project-root", str(root / "valid-proj"), "--json"]),
        # backups: vacío + con los 2 del fixture.
        ("B13 docs list-backups vacio", ["docs", "list-backups", "--project-root", str(root / "no-backups")]),
        ("B14 docs list-backups con backups", ["docs", "list-backups", "--project-root", r()]),
        # restore: nombre corto, ruta completa, inexistente.
        ("B15 docs restore nombre corto", ["docs", "restore", "--backup", "vault-", "--project-root", r(), "--target", str(root / "rest-a")]),
        ("B16 docs restore ruta completa", ["docs", "restore", "--backup", full_backup, "--project-root", r(), "--target", str(root / "rest-b")]),
        ("B17 docs restore inexistente", ["docs", "restore", "--backup", "vault-zzz-inexistente", "--project-root", r()]),
        # routing-table: texto (all + filtro) + json (all + filtro) + error.
        ("B18 docs routing-table texto", ["docs", "routing-table"]),
        ("B19 docs routing-table adr texto", ["docs", "routing-table", "--doc-type", "adr"]),
        ("B20 docs routing-table adr json", ["docs", "routing-table", "--doc-type", "adr", "--json"]),
        ("B21 docs routing-table json", ["docs", "routing-table", "--json"]),
        ("B22 docs routing-table doc_type invalido", ["docs", "routing-table", "--doc-type", "bogus"]),
        # setup real (inyecta bundle pi) → status post-setup → remove real.
        ("B23 ide setup pi real", ["ide", "setup", "--ide", "pi", "--project-root", r()]),
        ("B24 ide status pi post-setup json", ["ide", "status", "--ide", "pi", "--project-root", r(), "--json"]),
        ("B25 ide remove pi real", ["ide", "remove", "--ide", "pi", "--project-root", r()]),
        # Error path sin --ide: misma _require_ide que B03 con action "remove"
        # (determinista, sin efectos; rc 2).
        ("B26 ide remove sin --ide", ["ide", "remove", "--project-root", r()]),
    ]


def recolectar(binary: list[str], root: Path) -> str:
    blocks: list[str] = []
    for name, argv in casos(root):
        rc, out, err = _run(binary, argv, root)
        norm = normalize(out + (f"\n--stderr--\n{err}" if err.strip() else ""), root)
        blocks.append(f"### {name}\nrc={rc}\n{norm}")
    return "\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--out", default="bench/parity/.p12b-leaves-b")
    parser.add_argument("--rust-bin", default=str(RS_DEFAULT))
    args = parser.parse_args()

    golden_path = Path(args.out) / "golden_cierre_b.txt"

    with tempfile.TemporaryDirectory(prefix="cb_") as td:
        root = Path(td).resolve()
        construir_fixture(root)

        if args.mode == "build":
            report = recolectar([PY], root)
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(report, encoding="utf-8")
            print(f"[BUILD] {golden_path} ({len(report.splitlines())} líneas)")
            return 0

        expected = golden_path.read_text(encoding="utf-8")
        actual = recolectar([args.rust_bin], root)
        if actual != expected:
            exp_lines = expected.splitlines()
            got_lines = actual.splitlines()
            for i, (a, b) in enumerate(zip(exp_lines, got_lines)):
                if a != b:
                    print(f"[FAIL] primera divergencia en línea {i + 1}:")
                    print(f"  esperado: {a!r}")
                    print(f"  obtenido: {b!r}")
                    break
            else:
                print(f"[FAIL] longitud difiere: {len(exp_lines)} vs {len(got_lines)}")
            return 1
        print(
            f"[PASS] cierre_leaves_b byte-parity post-normalización "
            f"({len(expected.splitlines())} líneas)"
        )
        print("✅ PARIDAD BAJA DEFINITIVA — RUTA 1 MITAD B")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())