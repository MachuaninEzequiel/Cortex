#!/usr/bin/env python3
"""Golden P12A-9 — handlers MCP in-process de la familia sesiones.

Stub backend determinista compartido (semántica idéntica en Python y Rust).
Determinista puro: timestamps/commits fijados en fixtures.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40


# ---------------------------------------------------------------------------
# Stub backend (espejo exacto del StubSessionsBackend Rust)
# ---------------------------------------------------------------------------

class Rec(dict):
    """dict con acceso por atributo para comodidad."""

    def __getattr__(self, k):
        return self[k]


def new_record(spec_id="2026-05-16_demo", summary="demo"):
    return {
        "session_id": spec_id,
        "spec_path": f"vault/specs/{spec_id}.md",
        "spec_summary": summary,
        "start_commit": COMMIT_A,
        "start_branch": "feature/demo",
        "opened_at": "2026-05-16T10:00:00+00:00",
        "status": "open",
        "mode": "unknown",
        "checkpoints": [],
        "verification_results": [],
        "tasks": [],
        "closed_at": None,
        "end_commit": None,
        "documenter_decision": None,
        "session_note_path": None,
        "adrs_created": [],
    }


class StubBackend:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self.active: str | None = None
        self.note_path = "/tmp/fake/session-note.md"

    # -- sessions ---------------------------------------------------------
    def open_session(self, spec_id, spec_path, spec_summary):
        r = new_record(spec_id, spec_summary)
        r["spec_path"] = spec_path
        self.records[spec_id] = r
        self.active = spec_id
        return r

    def checkpoint_session(self, sid, source, verified, unverified, artifacts, note):
        r = self.records[sid]
        r["checkpoints"].append({
            "timestamp": "2026-05-16T11:00:00+00:00",
            "source": source,
            "verified_claims": verified,
            "unverified_claims": unverified,
            "artifacts_touched": artifacts,
            "note": note,
        })
        return r

    def close_session(self, sid, status, decision, note_path, adrs):
        r = self.records[sid]
        r["status"] = status
        r["documenter_decision"] = decision
        r["closed_at"] = "2026-05-16T12:00:00+00:00"
        r["end_commit"] = COMMIT_B
        r["mode"] = "observed" if r["checkpoints"] else "byo"
        if note_path:
            r["session_note_path"] = note_path
        r["adrs_created"] = list(adrs)
        return r

    def get_active_session(self):
        if self.active and self.records[self.active]["status"] == "open":
            return self.records[self.active]
        return None

    def get_session(self, sid):
        return self.records[sid]

    def list_sessions(self, status=None):
        out = [r for r in self.records.values() if status is None or r["status"] == status]
        return sorted(out, key=lambda r: r["session_id"])

    # -- tasks ------------------------------------------------------------
    def list_tasks(self, sid, status=None):
        ts = self.records[sid]["tasks"]
        if status is not None:
            ts = [t for t in ts if t["status"] == status]
        return ts

    def add_task(self, sid, task):
        self.records[sid]["tasks"].append(task)

    def update_task(self, sid, tid, status, note, ckp_index):
        for t in self.records[sid]["tasks"]:
            if t["id"] == tid:
                t["status"] = status
                t["note"] = note
                t["checkpoint_index"] = ckp_index
                if status in ("done", "skipped"):
                    t["completed_at"] = "2026-05-16T11:30:00+00:00"
                return
        raise ValueError(f"Task '{tid}' does not exist")

    # -- misc ---------------------------------------------------------------
    def save_session_note(self, args):
        return self.note_path

    def spec_files_in_scope(self, spec_path):
        return ["src/a.py", "src/b.py"]


# ---------------------------------------------------------------------------
# Escenarios
# ---------------------------------------------------------------------------

def build_report(root: Path) -> str:
    blocks: list[str] = []

    def emit(name, fn):
        try:
            blocks.append(f"### {name}\nrc=0\n{fn()}")
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"### {name}\nrc=1\nException: {type(exc).__name__}: {exc}")

    def j(v):
        return json.dumps(v, ensure_ascii=False)

    # ---- session_open -------------------------------------------------
    def s01():
        b = StubBackend()
        args = {"spec_id": "2026-05-16_demo", "spec_path": "vault/specs/demo.md", "spec_summary": "demo"}
        sid = str(args.get("spec_id", "")).strip()
        sp = str(args.get("spec_path", "")).strip()
        if not sid or not sp:
            return "❌ spec_id and spec_path are required for cortex_session_open."
        rec = b.open_session(sid, sp, str(args.get("spec_summary", "")))
        return j({"session_id": rec["session_id"], "opened_at": rec["opened_at"],
                  "start_commit": rec["start_commit"], "start_branch": rec["start_branch"]})
    emit("S01 open happy", s01)

    def s02():
        return "❌ spec_id and spec_path are required for cortex_session_open."
    emit("S02 open faltan campos", s02)

    # ---- checkpoint -----------------------------------------------------
    def s03():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        b.checkpoint_session("2026-05-16_demo", "manual", ["x"], [], ["src/a.py"], "nota")
        b.checkpoint_session("2026-05-16_demo", "user-skill", [], ["y"], [], "")
        r = b.records["2026-05-16_demo"]
        return j({
            "session_id": r["session_id"],
            "checkpoint_count": len(r["checkpoints"]),
            "last_checkpoint_at": r["checkpoints"][-1]["timestamp"],
        })

    emit("S03 checkpoint happy", s03)

    def s04():
        return "❌ session_id and source are required for cortex_session_checkpoint."
    emit("S04 checkpoint faltan campos", s04)

    def s05():
        from cortex.mcp.schemas import _CHECKPOINT_SOURCE_VALUES
        src = "nope"
        if src not in _CHECKPOINT_SOURCE_VALUES:
            return f"❌ Invalid source '{src}'. Must be one of: {', '.join(_CHECKPOINT_SOURCE_VALUES)}"
    emit("S05 checkpoint source inválida", s05)

    # ---- session_close ----------------------------------------------------
    def s06():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        r = b.close_session("2026-05-16_demo", "closed", "closed", None, [])
        return j({"session_id": r["session_id"], "closed_at": r["closed_at"],
                  "end_commit": r["end_commit"], "mode_inferred": r["mode"]})
    emit("S06 close happy", s06)

    def s07():
        b = StubBackend()
        out = []
        out.append(session_close_err({"session_id": "", "status": "", "documenter_decision": ""}))
        out.append(session_close_err({"session_id": "s", "status": "open", "documenter_decision": "closed"}))
        out.append(session_close_err({"session_id": "s", "status": "closed", "documenter_decision": "open"}))
        return "\n".join(out)

    def session_close_err(args):
        valid = ("closed", "handoff", "abandoned")
        sid = args.get("session_id", "").strip()
        st = args.get("status", "").strip()
        dec = args.get("documenter_decision", "").strip()
        if not sid or not st or not dec:
            return "❌ session_id, status and documenter_decision are required for cortex_session_close."
        if st not in valid:
            return f"❌ Invalid status '{st}'. Must be one of: {', '.join(valid)}"
        return f"❌ Invalid documenter_decision '{dec}'. Must be one of: {', '.join(valid)}"

    emit("S07 close errores", s07)

    # ---- status -------------------------------------------------------------
    def s08():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "resumen")
        return j(b.get_session("2026-05-16_demo"))
    emit("S08 status dump completo", s08)

    def s09():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        rec = b.get_active_session()
        assert rec is not None
        return j(rec)
    emit("S09 status activa", s09)

    def s10():
        b = StubBackend()
        assert b.get_active_session() is None
        return "❌ No active session. Pass session_id or open one first."
    emit("S10 sin activa", s10)

    # ---- list --------------------------------------------------------------
    def s11():
        b = StubBackend()
        b.open_session("2026-05-15_aaa", "p1", "uno")
        b.open_session("2026-05-16_bbb", "p2", "dos")
        b.close_session("2026-05-15_aaa", "handoff", "handoff", None, [])
        items = []
        for r in b.list_sessions(None):
            items.append({"session_id": r["session_id"], "status": r["status"],
                          "mode": r["mode"], "opened_at": r["opened_at"],
                          "closed_at": r["closed_at"], "checkpoint_count": len(r["checkpoints"]),
                          "spec_summary": r["spec_summary"]})
        only_open = [i["session_id"] for i in [] ]  # filtro se prueba vía handler
        return j(items)
    emit("S11 list", s11)

    # ---- tasks -----------------------------------------------------------
    def s12():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        return j(b.list_tasks("2026-05-16_demo", None))
    emit("S12 task_list vacío", s12)

    def s13():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        b.add_task("2026-05-16_demo", {"id": "T1", "description": "hacer", "files_in_scope": [],
                                       "depends_on": [], "status": "pending", "completed_at": None,
                                       "checkpoint_index": None, "note": ""})
        b.update_task("2026-05-16_demo", "T1", "done", "ok", 0)
        return j(b.list_tasks("2026-05-16_demo", None)[0])
    emit("S13 task_update done", s13)

    def s14():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        existing = b.list_tasks("2026-05-16_demo")
        if not any(t["id"] == "T9" for t in existing):
            desc = "nueva"
            if not desc:
                return f"❌ Task 'T9' does not exist; pass `description` to create it on the fly."
            b.add_task("2026-05-16_demo", {"id": "T9", "description": desc, "files_in_scope": [],
                                           "depends_on": [], "status": "pending", "completed_at": None,
                                           "checkpoint_index": None, "note": ""})
        b.update_task("2026-05-16_demo", "T9", "in-progress", "", None)
        return j(b.list_tasks("2026-05-16_demo", None)[0])
    emit("S14 auto-crear", s14)

    def s15():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        return "❌ Task 'TX' does not exist; pass `description` to create it on the fly."
    emit("S15 auto-crear sin descripción", s15)

    # ---- review_checkpoint --------------------------------------------------
    def _mk_cp(artifacts, note, verified):
        return {"timestamp": "2026-05-16T11:00:00+00:00", "source": "manual",
                "verified_claims": verified, "unverified_claims": [],
                "artifacts_touched": artifacts, "note": note}

    def s16():
        from cortex.session.quality_gates import review_checkpoint
        # El handler resuelve files_in_scope vía backend (stub fijo).
        files = ["src/a.py", "src/b.py"]
        out = []
        cases = [
            ("accept", _mk_cp(["src/a.py"], "todo bien, tests pasan", ["tests pasan"])),
            ("redelegate", _mk_cp(["src/fuera.py"], "trabajo fuera", [])),
            ("warn", _mk_cp(["src/a.py"], "fixme pendiente", [])),
        ]
        for label, cp in cases:
            # réplica del handler: files_in_scope del spec cargado; stub fijo:
            verdict = review_checkpoint(_to_py_checkpoint(cp), _FakeSpec(files))
            out.append(j({"accepted": verdict.accepted, "stage_1_passed": verdict.stage_1_passed,
                          "stage_2_passed": verdict.stage_2_passed, "reason": verdict.reason,
                          "action": verdict.action}))
        return "\n".join(out)

    class _FakeSpec:
        def __init__(self, files):
            self.files_in_scope = files

    def _to_py_checkpoint(d):
        from cortex.session.models import Checkpoint, CheckpointSource
        return Checkpoint(
            timestamp=__import__("datetime").datetime.fromisoformat(d["timestamp"]),
            source=CheckpointSource(d["source"]),
            verified_claims=d["verified_claims"],
            unverified_claims=d["unverified_claims"],
            artifacts_touched=d["artifacts_touched"],
            note=d["note"],
        )

    emit("S16 review veredictos", s16)

    def s17():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        return "❌ Session has no checkpoints to review."
    emit("S17 review sin checkpoints", s17)

    # ---- cortex_close_session ----------------------------------------------
    def s18():
        b = StubBackend()
        b.open_session("2026-05-16_demo", "vault/specs/demo.md", "")
        b.checkpoint_session("2026-05-16_demo", "manual", [], [], [], "n")
        r = b.close_session("2026-05-16_demo", "handoff", "handoff", "notes/x.md", ["decisions/ADR-001.md"])
        return j({"session_id": r["session_id"], "final_status": r["status"], "mode": r["mode"],
                  "closed_at": r["closed_at"], "end_commit": r["end_commit"],
                  "session_note_path": r["session_note_path"], "adrs_created": r["adrs_created"]})
    emit("S18 cortex_close_session happy", s18)

    # ---- save_session --------------------------------------------------------
    def s19():
        b = StubBackend()
        return f"Session note saved -> {b.save_session_note({})}"
    emit("S19 save_session", s19)

    # ---- validate_handoff -----------------------------------------------------
    def s20():
        yaml_ok = (
            "agent: cortex-documenter\n"
            "status: partial\n"
            "verified_claims:\n  - a\n"
            "unverified_claims:\n  - b\n"
            "artifacts_produced:\n  - path: src/x.py\n    action: modified\n    lines_changed: 12\n"
            "context_for_next:\n  - seguir\n"
            "suggested_adr: true\n"
            "suggested_adr_reason: decision no trivial\n"
            "suggested_context_terms:\n  - token\n"
        )
        from cortex.handoff import AgentHandoff
        h = AgentHandoff.from_yaml(yaml_ok)
        lines = [
            f"✅ Handoff validated for {h.agent} (status: {h.status})",
            f"  verified_claims: {len(h.verified_claims)}",
            f"  unverified_claims: {len(h.unverified_claims)}",
            f"  artifacts: {len(h.artifacts_produced)}",
            f"  context_for_next: {len(h.context_for_next)}",
        ]
        if h.suggested_adr:
            reason = h.suggested_adr_reason or "(no reason given)"
            lines.append(f"  ⚠ suggested ADR: {reason}")
        if h.suggested_context_terms:
            lines.append(f"  📚 CONTEXT.md terms: {', '.join(h.suggested_context_terms)}")
        return "\n".join(lines)
    emit("S20 validate_handoff happy", s20)

    def s21():
        return "\n".join([
            "❌ handoff_yaml is required and must not be empty.",
            "❌ Agent mismatch: handoff says 'cortex-documenter' but expected 'otro'.",
        ])
    emit("S21 validate_handoff errores", s21)

    # ---- verify_session_claims ---------------------------------------------------
    def git(*args, cwd):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)

    def s22():
        repo = root / "gitrepo"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True)
        for c in [["init", "-q", "-b", "main", "."], ["config", "user.email", "t@t.io"],
                  ["config", "user.name", "T"]]:
            git(*c, cwd=repo)
        (repo / "auth_login.py").write_text("token = 'refresh'\n", encoding="utf-8")
        git("add", ".", cwd=repo)
        git("commit", "-qm", "init", cwd=repo)
        (repo / "auth_login.py").write_text("token = 'rotated refresh'\nbcrypt_hash()\n",
                                            encoding="utf-8")
        diff = git("diff", "--unified=0", "main", "--", cwd=repo)
        assert diff.returncode == 0
        text = diff.stdout
        low = text.lower()

        def classify(claim):
            tokens = [t.lower() for t in claim.replace("_", " ").replace("/", " ").split() if len(t) > 3]
            hits = sum(1 for t in tokens if t in low)
            return "verified" if hits >= 2 else "asserted"

        claims = ["auth login token refresh", "bcrypt hash added", "completamente ajeno"]
        verified = [c for c in claims if classify(c) == "verified"]
        asserted = [c for c in claims if classify(c) == "asserted"]
        lines = [
            f"Verification of {len(claims)} claims against branch main:",
            f"  ✅ verified: {len(verified)}",
            f"  ⚠ asserted: {len(asserted)}",
            "  ❌ contradicted: 0",
        ]
        if verified:
            lines.append("\nVerified:")
            lines.extend(f"  - {c}" for c in verified)
        if asserted:
            lines.append("\nAsserted (no diff evidence):")
            lines.extend(f"  - {c}" for c in asserted)
        base_missing = git("rev-parse", "--verify", "--quiet", "nope", cwd=repo)
        extra = ""
        if base_missing.returncode != 0:
            extra = ("\n❌ Base branch 'nope' does not exist in this repo. "
                     "Pass a valid branch via `base_branch` argument.")
        return "\n".join(lines) + extra
    emit("S22 verify_session_claims", s22)

    return "\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden = out_dir / "golden_p12a9.txt"

    tmp = Path(tempfile.mkdtemp(prefix="p12a9_oracle_"))
    try:
        first = build_report(tmp)
        second = build_report(tmp)
        if first != second:
            print("❌ ORÁCULO NO DETERMINISTA")
            import difflib

            for line in difflib.unified_diff(first.splitlines(), second.splitlines(),
                                             "1ª", "2ª", lineterm=""):
                print(line)
            return 1
        print("✅ ORÁCULO DETERMINISTA")
        if args.command == "build":
            golden.write_text(first, encoding="utf-8")
            print(f"[OK] escrito {golden}")
            return 0
        expected = golden.read_text(encoding="utf-8")
        if first == expected:
            print("[PASS] golden_p12a9.txt")
            return 0
        print("[FAIL]")
        import difflib

        for line in difflib.unified_diff(expected.splitlines(), first.splitlines(),
                                         "py-guardado", "py-rerun", lineterm=""):
            print(line)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
