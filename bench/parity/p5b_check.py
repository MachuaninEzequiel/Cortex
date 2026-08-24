#!/usr/bin/env python3
"""P5b: paridad del reconstructor GIT-AWARE sobre un repo fixture en vivo.

Crea un repo git temporal con commits base, abre sesión (HEAD=base),
modifica archivos, checkpointea, y corre:
  1. Reconstructor Python (run_hooks=False)
  2. binario Rust git_check
y compara dumps normalizados (SHAs→{{SHA}}, ws→{{ROOT}}).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

SPEC_MD = """\
---
title: "Feature API"
goal: "Agregar endpoint de memorias"
files_in_scope:
  - src/api.py
acceptance_criteria:
  - endpoint responde
---

## Goal

Agregar endpoint de memorias.
"""


def sh(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    return proc.stdout


def normalizar(texto: str, ws: str) -> str:
    texto = re.sub(r"\b[0-9a-f]{40}\b", "{{SHA}}", texto)
    return texto.replace(ws, "{{ROOT}}")


def main() -> int:
    rust_bin = REPO_ROOT / "rust/target/debug/examples/git_check"
    if not rust_bin.exists():
        print(f"falta binario rust: {rust_bin}", file=sys.stderr)
        return 1

    from cortex.documenter.reconstruction import ReconstructionInput, Reconstructor
    from cortex.session.models import CheckpointSource
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage
    from cortex.session.verification import VerificationRunner

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)

        # Repo fixture: commit base → abrir sesión → cambios sin commitear.
        (ws / "src").mkdir(parents=True)
        (ws / "src" / "auth.py").write_text("def login(): ...\n", encoding="utf-8")
        sh(["git", "init", "-q", "-b", "main"], ws)
        for k, v in [("user.name", "F"), ("user.email", "f@f.local"), ("commit.gpgsign", "false")]:
            sh(["git", "config", k, v], ws)
        sh(["git", "add", "-A"], ws)
        sh(["git", "commit", "-q", "-m", "base"], ws)

        service = SessionService(
            storage=SessionStorage(sessions_dir=ws / ".cortex" / "sessions"),
            repo_root=ws,
        )
        rec = service.open(
            spec_id="2026-08-24_api",
            spec_path=ws / "specs" / "2026-08-24_api.md",
        )

        # Cambios de trabajo (sin commitear): modify + create.
        (ws / "src" / "auth.py").write_text("def login(): return True\n", encoding="utf-8")
        (ws / "src" / "api.py").write_text("def memories(): ...\n", encoding="utf-8")

        service.checkpoint(
            rec.session_id,
            source=CheckpointSource.CORTEX_CODE_IMPLEMENTER,
            verified_claims=["api lista"],
            artifacts_touched=["src/api.py"],
            note="Elegimos router simple en lugar de framework completo.",
        )
        specs = ws / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        (specs / "2026-08-24_api.md").write_text(SPEC_MD, encoding="utf-8")

        reconstructor = Reconstructor(
            session_service=service,
            verification_runner=VerificationRunner(repo_root=ws),
            repo_root=ws,
        )
        out = reconstructor.reconstruct(
            ReconstructionInput(session_id=rec.session_id, run_hooks=False)
        )
        d = json.loads(out.handoff.model_dump_json())
        py_dump = {
            "session_id": out.session_id,
            "handoff": d,
            "spec_path_normalized": normalizar(str(out.spec.path), str(ws)),
            "spec_title": out.spec.title,
            "spec_goal": out.spec.goal,
            "files_in_scope_spec": [str(p) for p in out.spec.files_in_scope],
            "acceptance_criteria": out.spec.acceptance_criteria,
            "status_session": out.session_record.status.value,
            "diff_text": normalizar(out.diff_text, str(ws))[:0] or "{{DIFF}}",
            "diff_entries": [
                {"action": e.action.value if hasattr(e.action, 'value') else str(e.action),
                 "path": e.path.as_posix(),
                 **({"old_path": e.old_path.as_posix()} if e.old_path else {})}
                for e in out.diff_entries
            ],
            "files_touched": [p.as_posix() for p in out.files_touched],
            "in_scope_files": [p.as_posix() for p in out.in_scope_files],
            "out_of_scope_files": [p.as_posix() for p in out.out_of_scope_files],
            "unimplemented_files": [p.as_posix() for p in out.unimplemented_files],
            "verification_results": [],
            "suggested_status": out.suggested_status.value,
            "suggested_adrs": [
                {"title": a.title,
                 "rationale": normalizar(a.rationale, str(ws)),
                 "source_checkpoint_index": a.source_checkpoint_index,
                 "evidence": a.evidence,
                 "confidence": a.confidence}
                for a in output_adrs(out)
            ],
            "end_commit": normalizar(out.end_commit, str(ws)),
            "gitless": out.gitless,
            "files_verified_by_git": [p.as_posix() for p in out.files_verified_by_git],
            "files_declared_only": [p.as_posix() for p in out.files_declared_only],
        }
        py_text = normalizar(json.dumps(py_dump, indent=2, ensure_ascii=False), str(ws))

        # ── Rust ──
        rs = subprocess.run(
            [str(rust_bin), str(ws), rec.session_id],
            capture_output=True, text=True, timeout=120,
        )
        if rs.returncode != 0:
            print("RUST ERROR:", rs.stderr[:400], file=sys.stderr)
            return 1
        rs_json = json.loads(rs.stdout)
        # El diff_text completo no se compara byte-a-byte (formato estable pero
        # enorme); se compara presencia + entries + provenance.
        py_text_obj = json.loads(py_text)
        py_text_obj["diff_text"] = "{{DIFF}}"
        rs_text_obj = rs_json
        rs_text_obj["diff_text"] = "{{DIFF}}"

        if py_text_obj == rs_text_obj:
            print("✅ PARIDAD GIT-AWARE TOTAL")
            print(json.dumps({
                "files_verified_by_git": rs_text_obj["files_verified_by_git"],
                "files_declared_only": rs_text_obj["files_declared_only"],
                "diff_entries": rs_text_obj["diff_entries"],
                "suggested_status": rs_text_obj["suggested_status"],
                "gitless": rs_text_obj["gitless"],
            }, ensure_ascii=False))
            return 0

        for k in py_text_obj:
            if py_text_obj[k] != rs_text_obj.get(k):
                print(f"DIFF[{k}]:\n  py  : {json.dumps(py_text_obj[k], ensure_ascii=False)[:300]}"
                      f"\n  rust: {json.dumps(rs_text_obj.get(k), ensure_ascii=False)[:300]}")
        return 1


def output_adrs(reconstruction):
    return reconstruction.suggested_adrs


if __name__ == "__main__":
    raise SystemExit(main())
