#!/usr/bin/env python3
"""Oráculo P4-fin: VerificationRunner + quality_gates (Obra 07).

Casos deterministas; se normalizan duration_ms→{{D}} y run_at→{{TS}}.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "bench/parity/golden_session")
    ns = ap.parse_args()
    out = ns.out
    out.mkdir(parents=True, exist_ok=True)

    from cortex.session.models import Checkpoint, CheckpointSource, VerificationHook
    from cortex.session.verification import VerificationRunner
    from cortex.session.quality_gates import review_checkpoint
    from cortex.documenter.spec_loader import LoadedSpec
    from datetime import datetime, timezone as tz
    import re

    tmp = Path(__file__).parent / "golden_session"
    runner = VerificationRunner(repo_root=tmp)

    hooks = [
        VerificationHook(name="ok", command="echo hola-verificacion", timeout_seconds=10),
        VerificationHook(name="falla", command="echo detalle-error >&2; exit 3", timeout_seconds=10),
        VerificationHook(name="solo-stderr", command="echo solo-errores >&2", timeout_seconds=10),
        VerificationHook(name="timeout", command="sleep 5", timeout_seconds=1),
        VerificationHook(
            name="truncado",
            command="python3 -c \"print('x'*12000, end='')\"",
            timeout_seconds=15,
        ),
    ]

    resultados = []
    for h in hooks:
        r = runner.run_hook(h)
        d = json.loads(r.model_dump_json())
        d["duration_ms"] = "{{D}}"
        d["run_at"] = "{{TS}}"
        # El mensaje de timeout contiene los segundos — estable (siempre 1).
        resultados.append(d)

    (out / "verification_results.json").write_text(
        json.dumps(resultados, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # ── Quality gates: tabla de casos ──
    ts = "2026-08-24T00:00:00+00:00"
    def cp(verified, artifacts, note=""):
        return Checkpoint(
            timestamp=datetime.now(tz.utc), source=CheckpointSource.MANUAL,
            verified_claims=list(verified), unverified_claims=[],
            artifacts_touched=list(artifacts), note=note,
        )

    casos = [
        ("accept_ok", cp(["tests pasan correctamente"], ["src/a.py"]), ["src/a.py"]),
        ("redelegate_scope", cp(["algo"], ["src/fuera.py"]), ["src/otro.py"]),
        ("process_artifact_ok", cp(["diseño listo"], [".cortex/vault/designs/d.md"]), ["src/b.py"]),
        ("sin_senal", cp([], []), []),
        ("placeholder_note", cp(["tests ok"], ["src/a.py"], note="pendiente TBD"), []),
        ("claim_corto", cp(["tests"], ["src/a.py"]), ["src/a.py"]),
    ]
    verdicts = []
    for nombre, checkpoint, scope in casos:
        spec = LoadedSpec(
            path=tmp / "spec.md", title="t", goal="g",
            files_in_scope=[Path(x) for x in scope],
            constraints=[], acceptance_criteria=[], verification_hooks=[],
        )
        v = review_checkpoint(checkpoint, spec)
        verdicts.append({
            "caso": nombre,
            "accepted": v.accepted,
            "stage_1_passed": v.stage_1_passed,
            "stage_2_passed": v.stage_2_passed,
            "reason": v.reason,
            "action": v.action,
        })
    (out / "quality_gates.json").write_text(
        json.dumps(verdicts, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"goldens verification+gates → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
