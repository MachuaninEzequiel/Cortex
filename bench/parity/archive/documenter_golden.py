#!/usr/bin/env python3
"""Oráculo P5a: Reconstructor gitless sobre sesión fixture (Obra 07).

Genera workspace temporal SIN git (placeholder determinista), abre sesión,
agrega checkpoints (uno con keywords de decisión ADR), escribe spec con
frontmatter, corre el Reconstructor REAL con run_hooks=False y captura:
  - session.yaml + spec_copy.md   (entradas para el verificador Rust)
  - dump_<sid>.json               salida canónica normalizada
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

SPEC_MD = """\
---
title: "Demo refactor"
goal: "Mejorar la autenticación del servicio"
files_in_scope:
  - src/auth.py
acceptance_criteria:
  - tests verdes
---

## Goal

Mejorar la autenticación del servicio.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_documenter")
    ns = ap.parse_args()
    out = ns.out
    out.mkdir(parents=True, exist_ok=True)

    from cortex.documenter.reconstruction import ReconstructionInput, Reconstructor
    from cortex.session.models import CheckpointSource, SessionStatus
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage
    from cortex.session.verification import VerificationRunner

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        service = SessionService(
            storage=SessionStorage(sessions_dir=ws / ".cortex" / "sessions"),
            repo_root=ws,
        )
        rec = service.open(
            spec_id="2026-08-24_demo",
            spec_path=ws / "specs" / "2026-08-24_demo.md",
            spec_summary="Demo P5",
        )
        service.checkpoint(
            rec.session_id,
            source=CheckpointSource.CORTEX_CODE_IMPLEMENTER,
            verified_claims=["auth refactorizada"],
            artifacts_touched=["src/auth.py", "src/nuevo.py"],
            note="Decidimos usar tokens vs sesiones por trade-off de latencia.",
        )
        service.checkpoint(
            rec.session_id,
            source=CheckpointSource.MANUAL,
            artifacts_touched=[".cortex/session.lock"],
        )

        # Spec real en disco.
        specs_dir = ws / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        spec_path = specs_dir / "2026-08-24_demo.md"
        spec_path.write_text(SPEC_MD, encoding="utf-8")

        reconstructor = Reconstructor(
            session_service=service,
            verification_runner=VerificationRunner(repo_root=ws),
            repo_root=ws,
        )
        output = reconstructor.reconstruct(
            ReconstructionInput(session_id=rec.session_id, run_hooks=False)
        )

        # ── Captura ──
        shutil.copy(spec_path, out / "spec_copy.md")
        shutil.copy(storage_yaml(service, rec.session_id), out / "session.yaml")

        d = {
            "session_id": output.session_id,
            "handoff": json.loads(output.handoff.model_dump_json()),
            "spec_path_normalized": normalizar(str(output.spec.path), str(ws)),
            "spec_title": output.spec.title,
            "spec_goal": output.spec.goal,
            "files_in_scope_spec": [str(p) for p in output.spec.files_in_scope],
            "acceptance_criteria": output.spec.acceptance_criteria,
            "status_session": output.session_record.status.value,
            "diff_text": "",
            "diff_entries": [],
            "files_touched": [p.as_posix() for p in output.files_touched],
            "in_scope_files": [p.as_posix() for p in output.in_scope_files],
            "out_of_scope_files": [p.as_posix() for p in output.out_of_scope_files],
            "unimplemented_files": [p.as_posix() for p in output.unimplemented_files],
            "verification_results": [],
            "suggested_status": output.suggested_status.value,
            "suggested_adrs": [
                {
                    "title": a.title,
                    "rationale": normalizar(a.rationale, str(ws)),
                    "source_checkpoint_index": a.source_checkpoint_index,
                    "evidence": a.evidence,
                    "confidence": a.confidence,
                }
                for a in output.suggested_adrs
            ],
            "end_commit": output.end_commit.replace(str(ws), "{{ROOT}}"),
            "gitless": output.gitless,
            "files_verified_by_git": [p.as_posix() for p in output.files_verified_by_git],
            "files_declared_only": [p.as_posix() for p in output.files_declared_only],
        }
        texto = normalizar(json.dumps(d, indent=2, ensure_ascii=False), str(ws))
        (out / f"dump_{rec.session_id}.json").write_text(texto + "\n", encoding="utf-8")
        (out / "session_id.txt").write_text(rec.session_id + "\n", encoding="utf-8")

    print(f"goldens documenter → {out}")
    return 0


def storage_yaml(service: SessionService, sid: str) -> Path:
    return service._storage.file_path(sid)


def normalizar(texto: str, ws: str) -> str:
    import re

    texto = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00", "{{TS}}", texto)
    return texto.replace(ws, "{{ROOT}}")


if __name__ == "__main__":
    raise SystemExit(main())
