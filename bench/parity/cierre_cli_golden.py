#!/usr/bin/env python3
"""Golden CIERRE T2 — subcomandos CLI wireados nativos.

Compara el binario nativo `cortex-cli` contra el CLI Python REAL
(`python -m cortex.cli.main`) sobre un fixture determinista construido por
el propio script (vault + chroma episódico + export JSONL P3), con
normalizaciones pactadas:

- {{ROOT}}   : tmp del fixture
- {{TS}}     : timestamps ISO (drift de reloj + sufijo Z de pydantic)
- {{ELAPSED}}: elapsed_ms de `next`
- {{RUN}}    : enricher_run_id aleatorio por corrida
- scores a 4 decimales: drift ~1e-7 entre SIMD chroma/ONNX y cómputo nativo
  (precedente P12A-1: tolerancia ≤1e-4; contrato = rankings exactos)

Modos:
  build  → congela la salida NORMALIZADA del CLI Python en golden_cierre_cli.txt
  verify → corre ambos lados y compara normalizados (paridad byte-a-byte
           post-normalización).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("PYTHONHASHSEED", "0")

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv" / "bin" / "python")
RS_DEFAULT = REPO / "rust" / "target" / "debug" / "cortex-cli"

ROOT_MARK = "{{ROOT}}"


# ---------------------------------------------------------------------------
# Fixture (mkdtemp FUERA del repo — lección P12B-7)
# ---------------------------------------------------------------------------

VAULT_FILES = {
    "specs/auth.md": (
        "---\ntitle: Auth spec\ndoc_type: spec\nstatus: draft\n"
        "tags: [auth, jwt]\n---\n\n## Goal\n\n"
        "Autenticación con JWT y refresh tokens para el módulo de pagos.\n"
    ),
    "notes/decisions.md": (
        "---\ntitle: Decisiones\ndoc_type: decision\nstatus: accepted\n"
        "tags: [pagos]\n---\n\nDecidimos usar Rust para el núcleo de pagos.\n"
    ),
}


def construir_fixture(root: Path) -> None:
    cortex = root / ".cortex"
    cortex.mkdir(parents=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nllm:\n  provider: openai\n  model: gpt-4o\n",
        encoding="utf-8",
    )
    vault = cortex / "vault"
    for rel, cuerpo in VAULT_FILES.items():
        p = vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cuerpo, encoding="utf-8")
        # `docs migrate` conserva el contrato histórico root/vault.
        legacy = root / "vault" / rel
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(cuerpo, encoding="utf-8")

    # Episódico real: store chroma + export JSONL para el lado nativo.
    from cortex.episodic.memory_store import EpisodicMemoryStore

    store = EpisodicMemoryStore(persist_dir=str(cortex / "memory"))
    store.add(
        content="Implementamos login con JWT",
        memory_type="session",
        tags=["auth"],
        files=["src/auth.py"],
    )
    store.add(
        content="Refactor del módulo de pagos en Rust",
        memory_type="session",
        tags=["pagos"],
        files=["src/pagos.rs"],
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
    out = cortex / "memory" / "episodic_export.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # git + commit inicial (para sesiones con HEAD real).
    env = dict(os.environ)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=env)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True, env=env)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True, env=env)
    (root / "auth.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-qm", "init"], cwd=root, check=True, capture_output=True, env=env
    )

    # Sesión activa con checkpoint (flujo canónico actual).
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage
    from cortex.workspace import WorkspaceLayout

    layout = WorkspaceLayout.discover(root)
    svc = SessionService(SessionStorage(layout.sessions_dir), repo_root=layout.repo_root)
    spec = vault / "specs" / "2026-08-25_demo.md"
    spec.write_text("---\ntitle: Demo\ndoc_type: spec\n---\n\ncuerpo demo\n", encoding="utf-8")
    rec = svc.open(spec_id="2026-08-25_demo", spec_path=spec, spec_summary="demo")
    (root / "gate.diff").write_text("--- a/auth.py\n+++ b/auth.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n", encoding="utf-8")
    svc.checkpoint(rec.session_id, source=__import__(
        "cortex.session.models", fromlist=["CheckpointSource"]
    ).CheckpointSource.MANUAL, note="trabajo inicial")


# ---------------------------------------------------------------------------
# Ejecución + normalización
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
    # Timestamps ISO (con o sin sufijo Z de pydantic) ⇒ {{TS}}.
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?",
        "{{TS}}",
        text,
    )
    # Rich session tables split timestamps into date/time cells.
    text = re.sub(r"(?<=│ )\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?=\s+│)", "{{TS}}", text)
    text = re.sub(r"(?<=│ )\d{4}-\d{2}-\d{2}(?=\s+│)", "{{TS}}", text)
    text = re.sub(r"(?<=│ )\d{2}:\d{2}(?::\d{2})?(?=\s+│)", "{{TS}}", text)
    text = re.sub(r'"elapsed_ms": \d+', '"elapsed_ms": {{ELAPSED}}', text)
    text = re.sub(r"\b\d+ms \u00b7 ejecut\u00e1", "{{ELAPSED}}ms · ejecutá", text)
    text = re.sub(r'"enricher_run_id": "[0-9a-f]{12}"', '"enricher_run_id": "{{RUN}}"', text)
    # Ids episódicos mem_{uuid8}: aleatorios por corrida del fixture.
    text = re.sub(r"mem_[0-9a-f]{8}", "{{MEMID}}", text)
    # SHAs de git del fixture: nuevos por rebuild.
    text = re.sub(r"\b[0-9a-f]{40}\b", "{{SHA}}", text)
    # Scores: drift float ~1e-7 SIMD vs nativo ⇒ 4 decimales.
    def round_float(m: re.Match) -> str:
        return f"{m.group(1)}: {round(float(m.group(2)), 4)}"
    text = re.sub(r"(score[\"']?\s*[:=]\s*)(-?\d+\.\d{5,})", round_float, text)
    text = re.sub(r'"(score|enriched_score)": (-?\d+\.\d{5,})', lambda m: f'"{m.group(1)}": {round(float(m.group(2)), 4)}', text)
    return text


def casos(root: Path) -> list[tuple[str, list[str]]]:
    """Casos (nombre, argv) — ≥2 por familia wireada."""
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    today = __import__("datetime").datetime.now(__import__("datetime").UTC).strftime("%Y-%m-%d")
    return [
        ("S01 search legacy texto", ["search", "JWT refresh tokens", "--top-k", "5"]),
        ("S02 search --json", ["search", "pagos rust", "--top-k", "3", "--json"]),
        ("S03 search vacío", ["search", "zzzznoexiste", "--json"]),
        ("S04 context markdown", ["context", "--files", "auth.py", "--format", "markdown"]),
        ("S05 context compact", ["context", "--files", "auth.py", "--format", "compact"]),
        ("S06 context json", ["context", "--files", "auth.py", "--format", "json"]),
        ("S07 stats", ["stats"]),
        ("S08 reindex dry-run", ["reindex", "--dry-run"]),
        ("S09 session current", ["session", "current"]),
        ("S10 session current --json", ["session", "current", "--json"]),
        ("S11 session show --json", ["session", "show", "--json"]),
        ("S12 session list --json", ["session", "list", "--json"]),
        ("S13 session checkpoint --json", [
            "session", "checkpoint", "--note", "ck del gate",
            "--verified-claim", "claim verificado", "--artifact", "auth.py",
            "--json",
        ]),
        ("S14 session switch inexistente", ["session", "switch", "no-existe"]),
        ("S15 next --json", ["next", "--json"]),
        ("S16 next texto", ["next"]),
        ("S17 hu list vacío", ["hu", "list"]),
        ("S18 hu show inexistente", ["hu", "show", "PROJ-999"]),
        # (S19 retirado: `hu import` sin providers lanza excepción NO
        # manejada en Python ⇒ traceback rich con rutas/frames no portables.
        # El CLI nativo falla con el mismo origen y mensaje limpio
        # "Unknown work item provider: jira" — mejora deliberada documentada
        # en progreso-cierre.md.)
        ("S20 pr-context capture", [
            "pr-context", "capture", "--title", "Demo PR",
            "--body", "cuerpo del PR", "--author", "ana",
            "--branch", "feat/x", "--labels", "api, core",
        ]),
        ("S21 session list texto", ["session", "list"]),
        ("S22 session show texto", ["session", "show"]),
        # docs search está cubierto por el test Rust enfocado: el comando Python
        # real está roto en HEAD (AgentMemory.from_config fue retirado).
        ("S25 docs migrate dry-run texto", ["docs", "migrate"]),
        ("S26 docs migrate dry-run json", ["docs", "migrate", "--json"]),
        ("S27 ci validate json", ["ci", "validate-pr", "--diff", "gate.diff", "--format", "json"]),
        ("S28 ci validate texto", ["ci", "validate-pr", "--diff", "gate.diff", "--format", "text"]),
        ("S29 ci open texto", ["ci", "open-review-session", "--base-commit", sha, "--head-branch", "feat/review", "--pr-number", "42"]),
        ("S30 ci open json", ["ci", "open-review-session", "--base-commit", sha, "--head-branch", "feat/review-json", "--pr-number", "43", "--json"]),
        ("S31 ci report json", ["ci", "report-checkpoint", "--session-id", f"{today}_pr-42-review", "--manual-claim", "ok", "--json"]),
        ("S32 ci close json", ["ci", "close-review-session", "--session-id", f"{today}_pr-42-review", "--status", "closed", "--json"]),
        ("S33 setup agent dry", ["setup", "agent", "--dry-run", "--non-interactive"]),
        ("S34 setup pipeline dry", ["setup", "pipeline", "--dry-run", "--non-interactive"]),
        ("S35 setup full dry", ["setup", "full", "--dry-run", "--non-interactive", "--ide", "pi"]),
        ("S36 setup webgraph dry", ["setup", "webgraph", "--dry-run"]),
        ("S37 setup enterprise custom error", ["setup", "enterprise", "--non-interactive", "--preset", "custom"]),
        ("S38 setup enterprise error", ["setup", "enterprise", "--non-interactive"]),
        ("S39 pr-context store", ["pr-context", "store"]),
        ("S40 pr-context search", ["pr-context", "search", "--top-k", "2"]),
        ("S41 pr-context generate", ["pr-context", "generate", "--vault", "generated-vault"]),
        ("S42 pr-context full", ["pr-context", "full", "--title", "Full Demo", "--author", "ana", "--branch", "feat/full", "--vault", "full-vault", "--context-file", ".full-context.json"]),
    ]


CASE_OUTPUT_FILE = {
    "S20 pr-context capture": ".pr-context.json",
    "S40 pr-context search": ".past-context.json",
    "S42 pr-context full": ".full-context.json",
}


def _drop_nulls(value):
    """Anexo A: rmcp omission is canonical; null and absent are equivalent."""
    if isinstance(value, dict):
        return {k: _drop_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_nulls(v) for v in value]
    return value


def mcp_exchange(binary: list[str], root: Path) -> list[dict]:
    proc = subprocess.Popen(
        binary + ["mcp-server", "--project-root", str(root)], cwd=root,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", bufsize=1, env={**os.environ, "OMP_NUM_THREADS": "2"},
    )
    assert proc.stdin is not None and proc.stdout is not None
    requests = [
        {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"cierre-cli","version":"1"}}},
        {"jsonrpc":"2.0","method":"notifications/initialized"},
        {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}},
        {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cortex_self_review_note","arguments":{"body":"Implemented native CLI.","verification_hooks_passed":True}}},
    ]
    responses = []
    try:
        for request in requests:
            proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            if "id" in request:
                responses.append(_drop_nulls(json.loads(proc.stdout.readline())))
        proc.stdin.close()
        proc.wait(timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.read() if proc.stderr else "MCP exited non-zero")
    finally:
        if proc.poll() is None:
            proc.kill()
    return responses


def recolectar(binary: list[str], root: Path) -> str:
    blocks: list[str] = []
    for name, argv in casos(root):
        rc, out, err = _run(binary, argv, root)
        extra = ""
        artifact = CASE_OUTPUT_FILE.get(name)
        if artifact and (root / artifact).exists():
            data = json.loads((root / artifact).read_text(encoding="utf-8"))
            extra = f"\nARTIFACT_KEYS={'|'.join(data.keys())}"
            if artifact != ".pr-context.json":
                (root / artifact).unlink()
        norm = normalize(out + (f"\n--stderr--\n{err}" if err.strip() else ""), root)
        blocks.append(f"### {name}\nrc={rc}\n{norm}{extra}")
    exchange = mcp_exchange(binary, root)
    blocks.append("### MCP stdio initialize + tools/list + tools/call\n" + json.dumps(exchange, ensure_ascii=False, indent=2))
    return "\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--out", default="bench/parity/.p12-cierre-cli")
    parser.add_argument("--rust-bin", default=str(RS_DEFAULT))
    args = parser.parse_args()

    golden_path = Path(args.out) / "golden_cierre_cli.txt"

    with tempfile.TemporaryDirectory(prefix="cierre_cli_") as td:
        root = Path(td).resolve()
        construir_fixture(root)

        if args.mode == "build":
            rc, out, err = _run([PY, "-m", "cortex.cli.main"], [], root)
            report = recolectar([PY, "-m", "cortex.cli.main"], root)
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
            f"[PASS] cierre_cli byte-parity post-normalización "
            f"({len(expected.splitlines())} líneas)"
        )
        print("✅ PARIDAD CIERRE T2")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
