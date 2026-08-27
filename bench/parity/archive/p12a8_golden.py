#!/usr/bin/env python3
"""Golden P12A-8 — cortex.documenter.interactive.

Máquina de estados del prompt interactivo de finish-session con I/O
stubbed (input_provider + editor). El rendering rich NO es contrato.

Determinista: sin relojes ni UUIDs.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cortex.documenter.adr_evaluator import ADRSuggestion  # noqa: E402
from cortex.documenter.interactive import InteractiveSession  # noqa: E402
from cortex.documenter.reconstruction import ReconstructionOutput  # noqa: E402
from cortex.documenter.spec_loader import LoadedSpec  # noqa: E402
from cortex.handoff import AgentHandoff  # noqa: E402
from cortex.session.models import (  # noqa: E402
    Checkpoint,
    CheckpointSource,
    SessionRecord,
    SessionStatus,
)

NOW = datetime(2026, 5, 16, 10, 0, 0, tzinfo=UTC)


def _spec() -> LoadedSpec:
    return LoadedSpec(
        path=Path("vault/specs/2026-05-16_demo.md"),
        title="Demo Spec",
        goal="Validate the interactive prompt",
        files_in_scope=[Path("src/a.py")],
        constraints=[],
        acceptance_criteria=["a.py is touched"],
        verification_hooks=[],
        raw_frontmatter={},
    )


def _session_record() -> SessionRecord:
    return SessionRecord(
        session_id="2026-05-16_demo",
        spec_path=Path("vault/specs/2026-05-16_demo.md"),
        spec_summary="demo",
        start_commit="a" * 40,
        start_branch="feature/demo",
        opened_at=NOW,
        checkpoints=[
            Checkpoint(
                timestamp=NOW,
                source=CheckpointSource.MANUAL,
                verified_claims=[],
                unverified_claims=[],
                artifacts_touched=["src/a.py"],
                note="hardcoded the TTL for now",
            )
        ],
    )


def _handoff() -> AgentHandoff:
    return AgentHandoff(
        agent="cortex-documenter",
        status="partial",
        verified_claims=[],
        unverified_claims=[],
        artifacts_produced=[],
        context_for_next=[],
    )


def _reconstruction(
    *,
    suggested_adrs=None,
    unimplemented=None,
    out_of_scope=None,
) -> ReconstructionOutput:
    return ReconstructionOutput(
        session_id="2026-05-16_demo",
        handoff=_handoff(),
        spec=_spec(),
        session_record=_session_record(),
        diff_text="diff --git a/src/a.py b/src/a.py\n+x\n",
        diff_entries=[],
        files_touched=[Path("src/a.py")],
        in_scope_files=[Path("src/a.py")],
        out_of_scope_files=out_of_scope or [],
        unimplemented_files=unimplemented or [],
        verification_results=[],
        contradictions=[],
        suggested_status=SessionStatus.HANDOFF,
        suggested_adrs=suggested_adrs or [],
        raw_checkpoints=_session_record().checkpoints,
        end_commit="b" * 40,
    )


def _adrs() -> list[ADRSuggestion]:
    return [
        ADRSuggestion(
            title="ADR 1", rationale="rationale 1",
            source_checkpoint_index=0, evidence="evidence 1", confidence="low",
        ),
        ADRSuggestion(
            title="ADR 2", rationale="rationale 2",
            source_checkpoint_index=None, evidence="evidence 2", confidence="low",
        ),
    ]


def make_session(inputs: list[str], *, editor_value: str | None = None):
    state = {"queue": list(inputs)}

    def input_provider(prompt: str = "") -> str:
        if not state["queue"]:
            raise AssertionError(f"sin más input; prompt={prompt!r}")
        return state["queue"].pop(0)

    sess = InteractiveSession(
        input_provider=input_provider,
        editor=lambda seed=None: editor_value,
    )
    return sess, state


def result_repr(out) -> str:
    forced = out.forced_status.value if out.forced_status is not None else None
    body = repr(out.edited_note_body) if out.edited_note_body is not None else "None"
    adrs = (
        "[" + ", ".join(str(i) for i in out.approved_adr_indices) + "]"
        if out.approved_adr_indices is not None
        else "None"
    )
    return "\n".join([
        f"action={out.action.value}",
        f"cancelled={out.cancelled}",
        f"forced={forced}",
        f"title={out.edited_note_title!r}",
        f"body={body}",
        f"adrs={adrs}",
    ])


def scenario(name: str, inputs: list[str], *, editor_value=None, recon=None):
    def fn():
        sess, state = make_session(inputs, editor_value=editor_value)
        try:
            out = sess.prompt(recon() if recon else _reconstruction())
            return result_repr(out) + f"\ninputs_left={len(state['queue'])}"
        except AssertionError as exc:
            return f"EXHAUSTED: {exc}"

    return name, fn


def build_report(root: Path) -> str:
    blocks: list[str] = []

    def emit(name, fn):
        try:
            blocks.append(f"### {name}\nrc=0\n{fn()}")
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"### {name}\nrc=1\nException: {type(exc).__name__}: {exc}")

    cases = [
        ("S01 approve", ["A"], dict()),
        ("S02 approve case-insensitive", ["approve"], dict()),
        ("S03 cancel", ["C"], dict()),
        ("S04 handoff con razón", ["H", "bcrypt incompatible with Lambda"], dict()),
        ("S05 handoff razón vacía vuelve al menú", ["H", "", "A"], dict()),
        ("S06 input inválido re-promptea", ["x", "?", "A"], dict()),
        ("S07 edit skip todo luego approve", ["E", "", "N", "A"], dict()),
        ("S08 edit reemplaza título", ["E", "Brand new title", "N", "A"], dict()),
        ("S09 edit cuerpo vía editor",
         ["E", "", "y", "A"],
         dict(editor_value="# Brand new body\n\nNew content here.\n")),
        ("S10 editor abortado", ["E", "", "y", "A"], dict(editor_value=None)),
        ("S11 edit luego cancel", ["E", "New Title", "N", "C"], dict()),
        ("S12 edit luego handoff", ["E", "", "N", "H", "blockers exist"], dict()),
        ("S13 approve default mantiene ADRs", ["A"], dict(recon=lambda: _reconstruction(suggested_adrs=_adrs()))),
        ("S14 rechaza un ADR",
         ["E", "", "N", "y", "n", "A"],
         dict(recon=lambda: _reconstruction(suggested_adrs=_adrs()))),
        ("S15 aprueba todos explícito",
         ["E", "", "N", "", "y", "A"],
         dict(recon=lambda: _reconstruction(suggested_adrs=_adrs()))),
    ]
    for name, inputs, kw in cases:
        emit(name, scenario(name.split(" ", 1)[1], inputs, **kw)[1])

    # S18: seed del editor (determinista)
    emit("S18 seed body", lambda: InteractiveSession._seed_body_for_editor(_reconstruction()))

    # S19: consumo exacto de inputs en el loop de inválidos
    def s19():
        sess, state = make_session(["x", "zzz", "h"])
        # h sin razón → vuelve; agotamos cola a propósito para ver el conteo.
        try:
            sess.prompt(_reconstruction())
            return "unexpected"
        except AssertionError as exc:
            return f"exhausted_ok={'sin más input' in str(exc)}"
    emit("S19 agotamiento de cola", s19)

    return "\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden = out_dir / "golden_p12a8.txt"

    tmp = Path(tempfile.mkdtemp(prefix="p12a8_oracle_"))
    try:
        first = build_report(tmp)
        second = build_report(tmp)
        if first != second:
            print("❌ ORÁCULO NO DETERMINISTA")
            import difflib

            for line in difflib.unified_diff(
                first.splitlines(), second.splitlines(), "1ª", "2ª", lineterm=""
            ):
                print(line)
            return 1
        print("✅ ORÁCULO DETERMINISTA")
        if args.command == "build":
            golden.write_text(first, encoding="utf-8")
            print(f"[OK] escrito {golden}")
            return 0
        expected = golden.read_text(encoding="utf-8")
        if first == expected:
            print("[PASS] golden_p12a8.txt")
            return 0
        print("[FAIL]")
        import difflib

        for line in difflib.unified_diff(
            expected.splitlines(), first.splitlines(), "py-guardado", "py-rerun",
            lineterm=""
        ):
            print(line)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
