#!/usr/bin/env python3
"""Oráculo P5c: DocumenterPersister → kwargs canónicos de create() + nota.

Stub de NoteService captura los kwargs EXACTOS que el persister pasa a
create(); la nota dorada se renderiza con jinja2 REAL sobre esos kwargs.
El Rust debe producir los mismos kwargs y renderizar el mismo body vía
minijinja.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

SPEC_MD = Path(__file__).parent.joinpath("golden_documenter", "spec_copy.md")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_documenter")
    ns = ap.parse_args()
    out = ns.out
    out.mkdir(parents=True, exist_ok=True)

    from cortex.documenter.persistence import DocumenterPersister
    from cortex.documenter.reconstruction import ReconstructionInput, Reconstructor
    from cortex.session.models import CheckpointSource
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage
    from cortex.session.verification import VerificationRunner

    captured: dict = {}

    class RecorderNotes:
        def __init__(self, vault_path: Path):
            self._vault_path = vault_path

        def create(self, **kwargs):
            captured["create_args"] = kwargs
            return self._vault_path / "sessions" / "note.md"

        def index_file(self, rel: str) -> bool:
            return True

        def sync(self) -> int:
            return 0

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
        specs_dir = ws / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        (specs_dir / "2026-08-24_demo.md").write_text(SPEC_MD.read_text(encoding="utf-8"))

        reconstructor = Reconstructor(
            session_service=service,
            verification_runner=VerificationRunner(repo_root=ws),
            repo_root=ws,
        )
        output = reconstructor.reconstruct(
            ReconstructionInput(session_id=rec.session_id, run_hooks=False)
        )

        persister = DocumenterPersister(
            note_service=RecorderNotes(vault_path=ws / "vault"),
            session_service=service,
            vault_path=ws / "vault",
        )
        result = persister.finalize(output)

        # ── Captura ──
        args = captured["create_args"]
        # Normalizaciones: rutas del tmp.
        texto = json.dumps(args, indent=2, ensure_ascii=False, sort_keys=True)
        texto = normalizar(texto, str(ws))
        (out / "create_args.json").write_text(texto + "\n", encoding="utf-8")

        # Body dorado: render con jinja2 REAL sobre los mismos kwargs.
        from cortex.documentation.templates_engine import render_template
        body = render_template("session.md.j2", args)
        (out / "note_body.md").write_text(body, encoding="utf-8")

        summary = normalizar(result.summary, str(ws))
        (out / "summary.txt").write_text(summary + "\n", encoding="utf-8")
        (out / "final_status.txt").write_text(result.final_status.value + "\n")

    print(f"goldens persister → {out}")
    return 0


def normalizar(texto: str, ws: str) -> str:
    import re

    texto = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00", "{{TS}}", texto)
    return texto.replace(ws, "{{ROOT}}")


if __name__ == "__main__":
    raise SystemExit(main())
