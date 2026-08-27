#!/usr/bin/env python3
"""Golden MITAD A — BAJA DEFINITIVA RUTA 1 (session task/hooks + remember/forget).

Compara el binario nativo `cortex-cli` contra el CLI Python REAL
(`python -m cortex.cli.main`) sobre un fixture determinista (sesiones con
tasks + store episódico ChromaDB + export JSONL), con las normalizaciones
PACTADAS del package (ver PROMPT-BAJA-DEFINITIVA-RUTA1.md):

- {{ROOT}}   : tmp del fixture
- {{TS}}     : timestamps ISO (drift de reloj entre corridas)
- {{ELAPSED}}/{{RUN}}: no producidas por esta familia (reservadas)
- {{MEMID}}  : ids episódicos aleatorios (mem_{uuid8})
- {{SHA}}    : SHAs git de 40 hex (fixtures gitless ⇒ raramente)
- scores a 4 decimales (no producidos acá; reservado)

Modos:
  build  → congela la salida NORMALIZADA del CLI Python en
           goldens_leaves_a.txt (bajo bench/parity/.p12-cierre-leaves-a/)
  verify → corre ambos lados y compara normalizados (byte-a-byte
           post-normalización)
  bench  → cold start N=20 por subcomando liviano + medición honesta de
           remember/forget (binario nativo release por defecto)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("PYTHONHASHSEED", "0")

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv" / "bin" / "python")
RS_DEBUG = REPO / "rust" / "target" / "debug" / "cortex-cli"
RS_RELEASE = REPO / "rust" / "target" / "release" / "cortex-cli"

ROOT_MARK = "{{ROOT}}"

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

VAULT_FILES = {
    "specs/auth.md": (
        "---\ntitle: Auth spec\ndoc_type: spec\nstatus: draft\n"
        "tags: [auth, jwt]\n---\n\n## Goal\n\nAutenticación con JWT.\n"
    ),
    "notes/decisions.md": (
        "---\ntitle: Decisiones\ndoc_type: decision\nstatus: accepted\n"
        "tags: [pagos]\n---\n\nDecidimos usar Rust para el núcleo.\n"
    ),
}

TASK_T1_DESC = (
    "Tarea uno con una descripcion bastante larga para probar el truncado "
    "de 60 caracteres en la tabla"
)


def _build_session_svc(root: Path):
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage
    from cortex.workspace import WorkspaceLayout

    layout = WorkspaceLayout.discover(root)
    return SessionService(SessionStorage(layout.sessions_dir), repo_root=layout.repo_root)


def _seed_episodic(root: Path) -> None:
    """ChromaDB con ids FIJOS (forget determinista) + export JSONL nativo."""
    from cortex.episodic.memory_store import EpisodicMemoryStore

    store = EpisodicMemoryStore(persist_dir=str(root / ".cortex" / "memory"))
    store.add(
        content="Implementamos login con JWT",
        memory_type="session",
        tags=["auth"],
        files=["src/auth.py"],
    )
    store.add(
        content="Refactor del modulo de pagos en Rust",
        memory_type="session",
        tags=["pagos"],
        files=["src/pagos.rs"],
    )
    got = store._collection.get(include=["documents", "metadatas", "embeddings"])
    fixed = ["mem_aaaa1111", "mem_bbbb2222"]
    if got["ids"]:
        store._collection.delete(ids=list(got["ids"]))
        for i, mid in enumerate(sorted(got["ids"])):
            meta = dict(got["metadatas"][i] or {})
            meta["id"] = fixed[i]
            store._collection.add(
                ids=[fixed[i]],
                embeddings=[got["embeddings"][i]],
                documents=[got["documents"][i]],
                metadatas=[meta],
            )
    got = store._collection.get(include=["documents", "metadatas", "embeddings"])
    rows = []
    for i, mid in enumerate(got["ids"]):
        rows.append({
            "id": mid,
            "document": got["documents"][i],
            "meta": dict(got["metadatas"][i] or {}),
            "embedding": [float(x) for x in got["embeddings"][i]],
        })
    rows.sort(key=lambda r: r["id"])
    out = root / ".cortex" / "memory" / "episodic_export.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def construir_fixture(root: Path) -> None:
    cortex = root / ".cortex"
    cortex.mkdir(parents=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\n"
        "episodic:\n  persist_dir: memory\n"
        "llm:\n  provider: openai\n  model: gpt-4o\n",
        encoding="utf-8",
    )
    vault = cortex / "vault"
    for rel, cuerpo in VAULT_FILES.items():
        p = vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cuerpo, encoding="utf-8")

    _seed_episodic(root)

    from cortex.session.models import Task, TaskStatus
    import datetime as _dt

    svc = _build_session_svc(root)
    # Sesión sin tasks (casos "empty") — se abre PRIMERO para que la sesión
    # demo quede como activa al final del fixture.
    vacio = vault / "specs" / "2026-08-26_vacio.md"
    vacio.write_text("---\ntitle: Vacio\ndoc_type: spec\n---\n\ncuerpo\n", encoding="utf-8")
    svc.open(spec_id="2026-08-26_vacio", spec_path=vacio, spec_summary="vacio")
    spec = vault / "specs" / "2026-08-25_demo.md"
    spec.write_text("---\ntitle: Demo\ndoc_type: spec\n---\n\ncuerpo\n", encoding="utf-8")
    rec = svc.open(spec_id="2026-08-25_demo", spec_path=spec, spec_summary="demo")
    svc.add_task(rec.session_id, Task(
        id="T1",
        description=TASK_T1_DESC,
        files_in_scope=["a.py", "b.py", "c.py", "d.py"],
    ))
    svc.add_task(rec.session_id, Task(
        id="T1.2",
        description="Sub tarea",
        files_in_scope=["x.py"],
        status=TaskStatus.DONE,
        # Invariante del modelo: done ⇒ completed_at no nulo.
        completed_at=_dt.datetime.now(_dt.timezone.utc),
        note="hecha en la ronda 1",
    ))
    # Ojo: "módulo" lleva tilde a propósito — prueba non-ASCII crudo en
    # `task list --json` (el oráculo usa json.dumps(ensure_ascii=False)).
    svc.add_task(rec.session_id, Task(
        id="T2",
        description="Tarea dos: accionar el módulo de pagos",
        files_in_scope=["lib/pagos.rs", "lib/wallet.rs", "tests/pagos.rs", "benches/pagos.rs"],
        status=TaskStatus.IN_PROGRESS,
    ))


# ---------------------------------------------------------------------------
# Ejecución + normalización (mismas pactadas que cierre_cli_golden.py)
# ---------------------------------------------------------------------------

def _run(binary: list[str], args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        binary + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env={**os.environ, "OMP_NUM_THREADS": "2"},
    )
    return proc.returncode, proc.stdout, proc.stderr


def normalize(text: str, root: Path) -> str:
    text = text.replace(str(root), ROOT_MARK)
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?",
        "{{TS}}",
        text,
    )
    text = re.sub(r'"elapsed_ms": \d+', '"elapsed_ms": {{ELAPSED}}', text)
    text = re.sub(r'"enricher_run_id": "[0-9a-f]{12}"', '"enricher_run_id": "{{RUN}}"', text)
    text = re.sub(r"mem_[0-9a-f]{8}", "{{MEMID}}", text)
    text = re.sub(r"\b[0-9a-f]{40}\b", "{{SHA}}", text)

    def round_float(m: re.Match) -> str:
        return f"{m.group(1)}: {round(float(m.group(2)), 4)}"
    text = re.sub(r"(score[\"']?\s*[:=]\s*)(-?\d+\.\d{5,})", round_float, text)
    text = re.sub(
        r'"(score|enriched_score)": (-?\d+\.\d{5,})',
        lambda m: f'"{m.group(1)}": {round(float(m.group(2)), 4)}',
        text,
    )
    return text


def casos(root: Path) -> list[tuple[str, list[str]]]:
    r = str(root)
    return [
        # session task list ×9 (texto + --json + filtros + errores + empty)
        ("A01 task list texto", ["session", "task", "list", "--project-root", r]),
        ("A02 task list --json", ["session", "task", "list", "--json", "--project-root", r]),
        ("A03 task list --status pending", ["session", "task", "list", "--status", "pending", "--project-root", r]),
        ("A04 task list --status done --json", ["session", "task", "list", "--status", "done", "--json", "--project-root", r]),
        ("A05 task list --status bogus", ["session", "task", "list", "--status", "bogus", "--project-root", r]),
        ("A06 task list sesion inexistente", ["session", "task", "list", "--session-id", "2099-01-01_nope", "--project-root", r]),
        # session task done ×3 (texto + --json + error)
        ("A07 task done --note", ["session", "task", "done", "T1", "--note", "primer fix", "--project-root", r]),
        ("A08 task done --json", ["session", "task", "done", "T1", "--json", "--project-root", r]),
        ("A09 task done inexistente", ["session", "task", "done", "T99", "--project-root", r]),
        # session task in-progress ×2 (texto + --json)
        ("A10 task in-progress", ["session", "task", "in-progress", "T1", "--project-root", r]),
        ("A11 task in-progress --json", ["session", "task", "in-progress", "T1", "--json", "--project-root", r]),
        # session task skip ×2 (texto + --json)
        ("A12 task skip --reason", ["session", "task", "skip", "T1", "--reason", "falta contexto", "--project-root", r]),
        ("A13 task skip --reason --json", ["session", "task", "skip", "T1", "--reason", "falta contexto", "--json", "--project-root", r]),
        # session task block ×2 (texto + --json)
        ("A14 task block --reason", ["session", "task", "block", "T1", "--reason", "depende de T2", "--project-root", r]),
        ("A15 task block --reason --json", ["session", "task", "block", "T1", "--reason", "depende de T2", "--json", "--project-root", r]),
        # Estado final tras mutaciones + variantes de sesión sin tasks
        ("A16 task list tras mutaciones", ["session", "task", "list", "--project-root", r]),
        ("A17 task list empty sesion", ["session", "task", "list", "--session-id", "2026-08-26_vacio", "--project-root", r]),
        ("A18 task list empty sesion --json", ["session", "task", "list", "--json", "--session-id", "2026-08-26_vacio", "--project-root", r]),
        # session hooks list ×2 (texto + --json)
        ("A19 hooks list texto", ["session", "hooks", "list", "--project-root", r]),
        ("A20 hooks list --json", ["session", "hooks", "list", "--json", "--project-root", r]),
        # session hooks install ×4 (pi ×2, claude-code --json, error)
        ("A21 hooks install pi", ["session", "hooks", "install", "--ide", "pi", "--project-root", r]),
        ("A22 hooks install pi segunda vez", ["session", "hooks", "install", "--ide", "pi", "--project-root", r]),
        ("A23 hooks install claude-code --json", ["session", "hooks", "install", "--ide", "claude-code", "--json", "--project-root", r]),
        ("A24 hooks install ide desconocido", ["session", "hooks", "install", "--ide", "bogus", "--project-root", r]),
        # session hooks status ×3 (individual + todos --json + error)
        ("A25 hooks status pi", ["session", "hooks", "status", "--ide", "pi", "--project-root", r]),
        ("A26 hooks status todo --json", ["session", "hooks", "status", "--json", "--project-root", r]),
        ("A27 hooks status ide desconocido", ["session", "hooks", "status", "--ide", "bogus", "--project-root", r]),
        # session hooks uninstall ×2 (texto + --json)
        ("A28 hooks uninstall pi", ["session", "hooks", "uninstall", "--ide", "pi", "--project-root", r]),
        ("A29 hooks uninstall pi --json", ["session", "hooks", "uninstall", "--ide", "pi", "--json", "--project-root", r]),
        # remember / forget
        ("A30 remember sesion", ["remember", "Implementamos login con JWT en auth.py", "--type", "session", "--tag", "auth", "--file", "src/auth.py"]),
        ("A31 remember refactor --branch", ["remember", "Refactor del modulo de pagos en Rust", "--type", "refactor", "--branch", "feat/pagos"]),
        ("A32 forget ok", ["forget", "mem_aaaa1111"]),
        ("A33 forget inexistente", ["forget", "mem_zzzz9999"]),
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
    parser.add_argument("mode", choices=("build", "verify", "bench"))
    parser.add_argument("--out", default="bench/parity/.p12-cierre-leaves-a")
    parser.add_argument("--rust-bin", default=str(RS_DEBUG))
    parser.add_argument("--rust-bin-bench", default=str(RS_RELEASE))
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    golden_path = Path(args.out) / "goldens_leaves_a.txt"

    with tempfile.TemporaryDirectory(prefix="leaves_a_") as td:
        root = Path(td).resolve()
        construir_fixture(root)

        if args.mode == "build":
            report = recolectar([PY, "-m", "cortex.cli.main"], root)
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(report, encoding="utf-8")
            print(f"[BUILD] {golden_path} ({len(report.splitlines())} líneas)")
            return 0

        if args.mode == "bench":
            binary = [args.rust_bin_bench]
            # Un subcomando representativo por familia (independiente de ids).
            for key in ("task list", "hooks list", "remember", "forget"):
                name, argv = next((n, a) for n, a in casos(root) if key in n)
                # Medición honesta: cada corrida parte de cero (carga fría).
                times = []
                for _ in range(args.n):
                    t0 = time.perf_counter()
                    subprocess.run(
                        binary + argv, cwd=str(root), capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=300,
                        env={**os.environ, "OMP_NUM_THREADS": "2"},
                    )
                    times.append((time.perf_counter() - t0) * 1000)
                avg = sum(times) / len(times)
                p95 = sorted(times)[int(len(times) * 0.95) - 1]
                print(f"[COLD] {name}: N={args.n} avg={avg:.1f}ms p95={p95:.1f}ms max={max(times):.1f}ms")
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
            print("[DIFF] primeras 20 líneas del lado nativo:")
            for l in got_lines[:20]:
                print(f"  {l!r}")
            return 1
        print(
            f"[PASS] cierre_leaves_a byte-parity post-normalización "
            f"({len(expected.splitlines())} líneas)"
        )
        print("✅ PARIDAD MITAD A — BAJA DEFINITIVA RUTA 1")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())