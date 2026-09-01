#!/usr/bin/env python3
"""Oráculo de paridad P6 — ActionEngine (`cortex next`) vs crate cortex-actions.

Sub-comandos:
  build-fixtures --out <dir>     genera los proyectos-fixture deterministas
  capture       --fixtures <dir> [--out bench/parity/golden_actions]
                                 captura salidas del CLI Python (oráculo)
  verify        [--fixtures <dir>] [--out …]
                                 regenera fixtures frescos en temp, captura y
                                 compara contra lo commiteado; exit 1 si difiere

Contrato de normalización (igual que capture_golden.py P0):
  - la ruta absoluta del fixture se reemplaza por ``{{ROOT}}``;
  - ``elapsed_ms`` se reemplaza por ``{{MS}}`` (depende del reloj);
  - un único ``\\n`` final. Todo lo demás byte-a-byte, incluido el ORDEN
    de las claves JSON.

Escenarios (todos deterministas para siempre):
  base         config+vault+log con ts fijos + feedback viejo + sesión OPEN
               >7d sin checkpoints → stale; sin git ⇒ checkpoint_now fuera.
  preferencias ídem + actions.yaml con never/skips/accepts.
  git-dirty    sesión OPEN CON checkpoints+spec + repo git sucio ⇒
               checkpoint_now/run_gates dentro; close_stale fuera.
  sin-config   sin config.yaml ⇒ error claro con exit 1 (se fija la SALIDA).

NOTA DE ALCANCE: el CLI `next` no inyecta señales al Scheduler (solo lo hacen
TUI/brain); la lógica de señales queda cubierta por unit tests espejo de
tests/unit/action_engine/test_fase_e.py, no por este golden.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

CORTEX_BIN = REPO / ".venv" / "bin" / "cortex"

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

# action_log.jsonl determinista: ts/duraciones fijos, mezcla auto/user/dry-run.
ACTION_LOG = (
    '{"id": "vault.reindex", "ts": "2026-08-20T15:04:05+00:00", "trigger": "on-open", '
    '"dry_run": false, "ok": true, "message": "Vault sincronizado — 12 docs indexados", '
    '"duration_ms": 1520, "via": "auto"}\n'
    '{"id": "vault.validate_docs", "ts": "2026-08-19T09:00:00+00:00", "trigger": "on-open", '
    '"dry_run": true, "ok": true, "message": "[dry-run] validaría ~2 docs", '
    '"duration_ms": 0, "via": "user"}\n'
    '{"id": "session.close_stale", "ts": "2026-08-19T10:30:00+00:00", "trigger": "on-open", '
    '"dry_run": false, "ok": true, "message": "sin sesiones stale", '
    '"duration_ms": 2, "via": "user"}\n'
    '{"id": "memory.prune", "ts": "2026-08-18T08:00:00+00:00", "trigger": "on-open", '
    '"dry_run": false, "ok": true, "message": "candidatos a olvidar (requiere confirmación aparte): mem_x", '
    '"duration_ms": 5, "via": "auto"}\n'
    '{"id": "vault.reindex", "ts": "2026-08-19T16:45:00+00:00", "trigger": "on-open", '
    '"dry_run": false, "ok": false, "message": "sync falló por permisos", '
    '"duration_ms": 210, "via": "auto"}\n'
    '{"id": "learn.topic", "ts": "2026-08-17T11:11:11+00:00", "trigger": "on-open", '
    '"dry_run": true, "ok": true, "message": "[dry-run] topic", '
    '"duration_ms": 0, "via": "user"}\n'
)

# feedback.jsonl con timestamps VIEJOS: fuera de la ventana de señales
# (neutras) pero DENTRO del conteo global de memory.prune (≥3 negativos).
FEEDBACK_VIEJO = "".join(
    json.dumps({"ts": ts, "feedback_type": tipo, "memory_id": mid}) + "\n"
    for ts, tipo, mid in [
        ("2026-01-05T12:00:00+00:00", "not_useful", "mem_x"),
        ("2026-01-06T12:00:00+00:00", "negative", "mem_y"),
        ("2026-01-07T12:00:00+00:00", "not_useful", "mem_z"),
        ("2026-01-08T12:00:00+00:00", "useful", "mem_w"),
    ]
)

ACTIONS_YAML_PREFERENCIAS = """\
acciones:
  vault.validate_docs:
    never: true
    skips: 0
    accepts: 0
  vault.reindex:
    never: false
    skips: 2
    accepts: 0
  learn.topic:
    never: false
    skips: 4
    accepts: 2
"""


def _escribir_sesion(dot_cortex: Path, session_id: str, *, opened_at: str,
                     con_checkpoints: bool) -> None:
    """Sesión canónica escrita con SessionStorage real (formato P4)."""
    from datetime import UTC, datetime

    from cortex.session.models import (
        Checkpoint,
        CheckpointSource,
        GITLESS_COMMIT_PLACEHOLDER,
        SessionRecord,
        SessionStatus,
    )
    from cortex.session.storage import SessionStorage

    record = SessionRecord(
        session_id=session_id,
        spec_path="vault/specs/demo.md",
        spec_summary="spec demo determinista",
        start_commit=GITLESS_COMMIT_PLACEHOLDER if not con_checkpoints else "a" * 40,
        start_branch="main",
        opened_at=datetime.fromisoformat(opened_at),
        status=SessionStatus.OPEN,
        checkpoints=[
            Checkpoint(
                timestamp=datetime(2026, 8, 20, 15, 0, 0, tzinfo=UTC),
                source=CheckpointSource.MANUAL,
                note="checkpoint fixture",
                verified_claims=["implementa X con test"],
            ),
        ]
        if con_checkpoints
        else [],
    )
    storage = SessionStorage(sessions_dir=dot_cortex / "sessions")
    storage.save(record)


def construir_fixture_base(destino: Path) -> None:
    (destino / "vault").mkdir(parents=True)
    (destino / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    (destino / "vault" / "nota-a.md").write_text(NOTA_A, encoding="utf-8")
    (destino / "vault" / "note-b.md").write_text(NOTE_B, encoding="utf-8")
    dot = destino / ".cortex"
    dot.mkdir()
    (dot / "action_log.jsonl").write_text(ACTION_LOG, encoding="utf-8")
    (dot / "feedback.jsonl").write_text(FEEDBACK_VIEJO, encoding="utf-8")
    _escribir_sesion(
        dot, "2026-07-25_stale-demo",
        opened_at="2026-07-25T09:00:00+00:00", con_checkpoints=False,
    )


def escenario_base(root: Path) -> Path:
    d = root / "base"
    construir_fixture_base(d)
    return d


def escenario_preferencias(root: Path) -> Path:
    d = root / "preferencias"
    construir_fixture_base(d)
    (d / ".cortex" / "actions.yaml").write_text(ACTIONS_YAML_PREFERENCIAS, encoding="utf-8")
    return d


def escenario_git_dirty(root: Path) -> Path:
    d = root / "git-dirty"
    construir_fixture_base(d)
    # sesión ACTIVA con checkpoints+spec (close_stale fuera, run_gates dentro)
    sesiones = d / ".cortex" / "sessions"
    for f in sesiones.glob("*.yaml"):
        f.unlink()  # quitar la stale; entra la activa
    _escribir_sesion(
        d / ".cortex", "2026-08-23_activa",
        opened_at="2026-01-10T08:00:00+00:00", con_checkpoints=True,
    )
    # repo git con cambios sin commit (porcelain no vacío, determinista)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    (d / "cambios.txt").write_text("pendiente\n", encoding="utf-8")
    return d


def escenario_sin_config(root: Path) -> Path:
    d = root / "sin-config"
    d.mkdir(parents=True)
    (d / "vault").mkdir()
    (d / "vault" / "nota.md").write_text("# vacío\n", encoding="utf-8")
    return d


ESCENARIOS = {
    "base": escenario_base,
    "preferencias": escenario_preferencias,
    "git-dirty": escenario_git_dirty,
    "sin-config": escenario_sin_config,
}

# (args, nombre, rc-permitidos) — igual patrón que capture_golden.py
COMANDOS: list[tuple[list[str], str, set[int]]] = [
    (["next", "--stats"], "next_stats.json", {0}),
    (["next", "--json"], "next_json.json", {0}),
    (["next", "--json", "--explain-why-not"], "next_why_not.json", {0}),
    (["next"], "next_texto.txt", {0}),
]


def normalizar(texto: str, fixture_root: Path) -> str:
    texto = texto.replace(str(fixture_root), "{{ROOT}}")
    texto = re.sub(r'"elapsed_ms": \d+', '"elapsed_ms": {{MS}}', texto)
    # El texto plano termina con el hint [dim]…ms · ejecutá …[/dim]
    texto = re.sub(
        r"\[dim\]\d+ms · ejecutá `cortex next --json` para salida machine-readable\[/dim\]",
        "[dim]{{MS}}ms · ejecutá `cortex next --json` para salida machine-readable[/dim]",
        texto,
    )
    return texto.rstrip("\n") + "\n"


def capturar(fixture: Path, args: list[str], rc_ok: set[int]) -> tuple[str, int]:
    proc = subprocess.run(
        [str(CORTEX_BIN), *args],
        cwd=fixture,
        capture_output=True,
        text=True,
        timeout=120,
    )
    salida = proc.stdout if proc.returncode == 0 else (proc.stdout + proc.stderr)
    return normalizar(salida, fixture), proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build-fixtures")
    p_build.add_argument("--out", required=True, type=Path)

    for name in ("capture", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--fixtures", type=Path, default=None,
                       help="fixtures ya construidos (capture). verify regenera en temp.")
        p.add_argument("--out", type=Path, default=REPO / "bench/parity/golden_actions")

    ns = ap.parse_args()

    if ns.cmd == "build-fixtures":
        for nombre, fabrica in ESCENARIOS.items():
            d = fabrica(ns.out)
            print(f"fixture {nombre} → {d}")
        return 0

    verificar = ns.cmd == "verify"
    ns.out.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        if verificar or ns.fixtures is None:
            fixtures_root = Path(tmp)
            for nombre, fabrica in ESCENARIOS.items():
                fabrica(fixtures_root)
        else:
            fixtures_root = ns.fixtures

        fallas = 0
        for nombre in ESCENARIOS:
            fixture = (fixtures_root / nombre).resolve()
            out_dir = ns.out / nombre
            out_dir.mkdir(parents=True, exist_ok=True)
            for args, fname, rc_ok in COMANDOS:
                salida, rc = capturar(fixture, args, rc_ok | {1})
                destino = out_dir / fname
                if verificar:
                    esperado = destino.read_text(encoding="utf-8")
                    if salida == esperado and rc in (rc_ok | {1}):
                        print(f"[PASS] {nombre}/{fname}")
                    else:
                        print(f"[FAIL] {nombre}/{fname} difiere ({destino})")
                        if salida != esperado:
                            print("--- esperado ---")
                            print(esperado[:600])
                            print("--- obtenido ---")
                            print(salida[:600])
                        fallas += 1
                else:
                    destino.write_text(salida, encoding="utf-8")
                    print(f"[capturado] {nombre}/{fname} (rc={rc})")

    if verificar:
        print(f"\n{'✅ VERIFICACIÓN OK' if fallas == 0 else f'❌ {fallas} diferencias'}")
        return 1 if fallas else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
