#!/usr/bin/env python3
"""Oráculo de paridad P4 — Session primitive (Obra 07).

Crea sesiones fixture vía el SessionService REAL (modo gitless ⇒ placeholder
determinístico), en un workspace temporal, y captura:
  - sessions/*.yaml            los YAML tal cual los escribe el storage Python
  - dumps/<sid>.json           dump canónico normalizado ({{TS}}/{{ROOT}},
                               sort_keys=True)
  - active_pointer.txt         contenido del puntero
  - infer_mode.json            tabla de casos del infer_mode

El verificador Rust (examples/session_check.rs) carga esos mismos YAML con
los modelos serde, valida, produce el dump canónico y compara.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00")


def normalizar(texto: str, ws: str) -> str:
    texto = ISO_RE.sub("{{TS}}", texto)
    return texto.replace(ws, "{{ROOT}}")


def dump_canonico(record, ws: Path) -> str:
    d = json.loads(record.model_dump(mode="json", context=None) if False else record.model_dump_json())
    obj = json.loads(normalizar(json.dumps(d, sort_keys=True, ensure_ascii=False), str(ws)))
    # Normalizar timestamps explícitamente (por si algún campo escapa al regex).
    for k in ("opened_at", "closed_at"):
        if obj.get(k):
            obj[k] = "{{TS}}"
    for cp in obj.get("checkpoints", []):
        cp["timestamp"] = "{{TS}}"
    for vr in obj.get("verification_results", []):
        vr["run_at"] = "{{TS}}"
    for t in obj.get("tasks", []):
        if t.get("completed_at"):
            t["completed_at"] = "{{TS}}"
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_session")
    ns = ap.parse_args()
    out = ns.out
    out.mkdir(parents=True, exist_ok=True)

    from cortex.session.models import CheckpointSource, SessionStatus
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        storage_dir = ws / ".cortex" / "sessions"
        service = SessionService(storage=SessionStorage(sessions_dir=storage_dir), repo_root=ws)

        # ── s-open: OPEN con checkpoints mixtos (observed) ──
        r1 = service.open(spec_id="2026-08-24_fix-login", spec_path=ws / "specs" / "x.md",
                          spec_summary="Arregla login")
        service.checkpoint(r1.session_id, source=CheckpointSource.IDE_HOOK,
                           verified_claims=["tests corren"], note="hook del IDE")
        service.checkpoint(r1.session_id, source=CheckpointSource.MANUAL,
                           artifacts_touched=["src/auth.py"])

        # ── s-closed: CLOSED con verification results simulados ──
        r2 = service.open(spec_id="2026-08-24_add-api", spec_path=ws / "specs" / "y.md")
        service.checkpoint(r2.session_id, source=CheckpointSource.CORTEX_CODE_IMPLEMENTER,
                           verified_claims=["endpoint ok"])
        service.checkpoint(r2.session_id, source=CheckpointSource.CORTEX_SYNC,
                           unverified_claims=["perf por medir"])
        service.close(r2.session_id, status=SessionStatus.CLOSED,
                      documenter_decision=SessionStatus.CLOSED)

        # ── s-handoff: HANDOFF con tasks y bloqueo ──
        r3 = service.open(spec_id="2026-08-24_big-refactor", spec_path=ws / "specs" / "z.md",
                          spec_summary="Refactor grande")
        service.checkpoint(r3.session_id, source=CheckpointSource.USER_SKILL)
        r3 = service._storage.mutate(r3.session_id, lambda rec: rec.model_copy(update={
            "tasks": [
                {"id": "T1", "description": "extraer servicio", "status": "done",
                 "completed_at": "2026-08-24T12:00:00+00:00"},
                {"id": "T2", "description": "migrar tests", "status": "blocked", "note": "espera API"},
            ]
        }))
        service.close(r3.session_id, status=SessionStatus.HANDOFF,
                      documenter_decision=SessionStatus.HANDOFF)

        # ── s-byo: OPEN sin checkpoints ──
        r4 = service.open(spec_id="2026-08-24_experimento", spec_path=ws / "specs" / "w.md")

        # ── Captura (recargando SIEMPRE desde storage: estado real en disco) ──
        for sid in [r1.session_id, r2.session_id, r3.session_id, r4.session_id]:
            rec = service._storage.load(sid)
            src = storage_dir / f"{sid}.yaml"
            shutil.copy(src, out / src.name)
            (out / f"dump_{sid}.json").write_text(
                dump_canonico(rec, ws), encoding="utf-8"
            )
        pointer = storage_dir / "active.txt"
        (out / "active_pointer.txt").write_text(
            pointer.read_text(encoding="utf-8"), encoding="utf-8"
        )
        # Copia con el nombre real para que SessionStorage Rust lo lea.
        shutil.copy(pointer, out / "active.txt")

        # ── infer_mode table ──
        from cortex.session.models import Checkpoint
        from datetime import datetime, timezone as tz
        src_map = {c.value: c for c in CheckpointSource}
        def cp(source: str) -> Checkpoint:
            return Checkpoint(timestamp=datetime.now(tz.utc), source=src_map[source])
        casos = {
            "vacio": [],
            "ci_review": [cp("ci-bot")],
            "managed": [cp("cortex-sync"), cp("cortex-code-implementer")],
            "observed": [cp("ide-hook"), cp("cortex-sync")],
        }
        tabla = {n: SessionService.infer_mode(c).value for n, c in casos.items()}
        (out / "infer_mode.json").write_text(
            json.dumps(tabla, indent=1) + "\n", encoding="utf-8"
        )

    print(f"goldens session → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
