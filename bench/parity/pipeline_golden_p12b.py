#!/usr/bin/env python3
"""Gate de paridad P12B-6 (pipeline). Genera golden_pipeline.txt con:

1. Workflow YAML byte-exacto para 2 sets canónicos de stages.
2. Orquestador con stages falsos: pass / fail-bloqueante (skip resto) /
   abort_early=False.
3. Renderings: summary(), to_markdown(), to_dict() con clock fijo.
4. `### DOCUMENTATION`: DocumentationStage REAL (nativo) sobre un fixture
   gitless fuera del repo (lección P12B-7) — docs-present, no-docs-fallback
   y no-docs-bloqueante — StageResult congelado vía reloj fijo.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from cortex.pipeline.domain.types import StageResult, StageStatus, StageType
from cortex.pipeline.orchestrator import PipelineOrchestrator
from cortex.pipeline.runners.github import GitHubActionsRunner

REPO = Path(__file__).resolve().parents[2]
DOC_GATE = REPO / "rust" / "target" / "debug" / "examples" / "documentation_gate"

FIXED_TS = "2026-08-25T12:00:00+00:00"
ID_RE = re.compile(r"sessions/[0-9a-f]{12}_[^/\s]+\.md")


def norm_docs(text: str, root: Path) -> str:
    """Normalización pactada del segmento ### DOCUMENTATION."""
    text = text.replace(str(root), "{{ROOT}}")
    return ID_RE.sub("sessions/{{ID}}.md", text)


def fixed_result(stage_type, name, status, message="", duration_ms=0):
    r = StageResult(
        stage_type=stage_type,
        stage_name=name,
        status=status,
        message=message,
        artifacts={"command": "fake"} if status != StageStatus.SKIPPED else {},
        duration_ms=duration_ms or 1234 if status == StageStatus.PASSED else 0,
    )
    object.__setattr__(r, "timestamp", datetime.fromisoformat(FIXED_TS))
    return r


class FakeStage:
    def __init__(self, name, stage_type, ok=True, block=True):
        self._name = name
        self._t = stage_type
        self._ok = ok
        self._block = block

    @property
    def name(self): return self._name
    @property
    def stage_type(self): return self._t
    @property
    def block_on_failure(self): return self._block
    def execute(self, ctx):
        status = StageStatus.PASSED if self._ok else StageStatus.FAILED
        return fixed_result(self._t, self._name, status)




def seg_workflows(lines):
    for label, stages in [
        ("full", [StageType.SECURITY_SCAN, StageType.LINT, StageType.TEST, StageType.DOCUMENTATION]),
        ("test_only", [StageType.TEST]),
    ]:
        runner = GitHubActionsRunner()
        lines.append(f"### WORKFLOW {label}\n")
        lines.append(runner.generate_pr_workflow(stages))
        lines.append("\n")


def seg_orchestrator(lines):
    # Flow A: todo pasa.
    stages = [
        FakeStage("Security Audit", StageType.SECURITY_SCAN),
        FakeStage("Lint", StageType.LINT),
        FakeStage("Tests", StageType.TEST),
    ]
    report = PipelineOrchestrator(stages).run(_ctx())
    _freeze(report)
    lines.append(json.dumps(report.to_dict(), indent=1, default=str) + "\n")
    lines.append(report.summary() + "\n")

    # Flow B: lint falla bloqueante → tests quedan SKIPPED.
    stages = [
        FakeStage("Security Audit", StageType.SECURITY_SCAN),
        FakeStage("Lint", StageType.LINT, ok=False),
        FakeStage("Tests", StageType.TEST),
    ]
    report = PipelineOrchestrator(stages).run(_ctx())
    lines.append(json.dumps([
        {"stage_name": r.stage_name, "status": r.status.value}
        for r in report.results
    ]) + "\n")
    lines.append(f"passed={report.passed}\n")

    # Flow C: abort_early=False corre todo.
    stages = [
        FakeStage("Security Audit", StageType.SECURITY_SCAN, ok=False),
        FakeStage("Tests", StageType.TEST),
    ]
    report = PipelineOrchestrator(stages, abort_early=False).run(_ctx())
    lines.append(json.dumps([r.status.value for r in report.results]) + "\n")

    # Flow D: no-bloqueante falla pero continúa.
    stages = [
        FakeStage("Docs", StageType.DOCUMENTATION, ok=False, block=False),
        FakeStage("Tests", StageType.TEST),
    ]
    report = PipelineOrchestrator(stages).run(_ctx())
    lines.append(json.dumps([r.status.value for r in report.results]) + "\n")
    lines.append(report.to_markdown() + "\n")


def _freeze(report):
    ts = datetime.fromisoformat(FIXED_TS)
    report.started_at = ts
    report.ended_at = ts
    for r in report.results:
        object.__setattr__(r, "timestamp", ts)


# ---------------------------------------------------------------------------
# ### DOCUMENTATION — DocumentationStage REAL (nativo) sobre fixture gitless
# ---------------------------------------------------------------------------

SPEC_BODY = (
    "---\ntitle: PR spec\ngoal: Implement password reset flow\n"
    "files_in_scope:\n  - src/auth.py\nacceptance_criteria:\n  - Reset works\n"
    "---\n\n## Goal\n\nImplement password reset flow.\n"
)


def construir_fixture_docs(root: Path) -> None:
    """Vault + sesión gitless REAL (SessionService Python) + spec en disco.

    Layout v2 ⇒ vault en `.cortex/vault` y sesiones en `.cortex/sessions`
    (misma resolución que el checker Rust vía WorkspaceLayout). El fixture
    vive FUERA del repo para que `is_git_repo` (rev-parse, ancestros) sea
    real: si estuviera dentro del repo, la sesión no sería gitless.
    """
    from cortex.session.service import SessionService as PySessionService
    from cortex.session.storage import SessionStorage as PySessionStorage
    from cortex.workspace.layout import WorkspaceLayout

    cortex = root / ".cortex"
    cortex.mkdir(parents=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    layout = WorkspaceLayout.discover(root)
    vault = layout.vault_path
    (vault / "specs").mkdir(parents=True)
    (vault / "specs" / "pr-spec.md").write_text(SPEC_BODY, encoding="utf-8")

    storage = PySessionStorage(layout.sessions_dir)
    svc = PySessionService(storage, layout.repo_root)
    svc.open(
        spec_id="2026-08-25_docspr",
        spec_path=vault / "specs" / "pr-spec.md",
        spec_summary="Implement password reset flow",
    )
    # Gitless ⇒ start_branch vacío; fijar el branch del PR para el match
    # by_branch de find_for_pr (la stage nativa usa ctx.source_branch).
    yaml = layout.sessions_dir / "2026-08-25_docspr.yaml"
    text = yaml.read_text(encoding="utf-8")
    assert "start_branch: ''" in text, text
    yaml.write_text(text.replace("start_branch: ''", "start_branch: feature/pr-docs"), encoding="utf-8")


def run_docs_gate(root: Path, block: int, changed: str, pr_ctx: str) -> str:
    if not DOC_GATE.exists():
        return (
            "[FAIL] binario nativo ausente: "
            f"{DOC_GATE} (cargo build -p cortex-pipeline --example documentation_gate)"
        )
    proc = subprocess.run(
        [str(DOC_GATE), str(root), FIXED_TS, str(block), changed, pr_ctx],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        return f"[FAIL] documentation_gate rc={proc.returncode}: {proc.stderr.strip()}"
    return proc.stdout.strip()


def seg_documentation(lines) -> None:
    """Corre el DocumentationStage REAL (native) y congela su StageResult."""
    lines.append("### DOCUMENTATION\n")
    root = Path(tempfile.mkdtemp(prefix="p12b_docs_"))
    try:
        construir_fixture_docs(root)
        for label, block, changed, pr_ctx in [
            ("docs_present", 0, "vault/specs/pr-spec.md", "1"),
            ("no_docs_fallback", 0, "src/auth.py", "1"),
            ("no_docs_block", 1, "src/auth.py", "1"),
        ]:
            out = norm_docs(run_docs_gate(root, block, changed, pr_ctx), root)
            lines.append(f"## CASE {label}\n")
            lines.append(out + "\n")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _ctx():
    from cortex.pipeline.domain.context import PipelineContext
    return PipelineContext(vault_path="vault")


def build(out_dir: Path) -> int:
    workdir = out_dir / ".work"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    lines = ["### WORKFLOWS\n"]
    seg_workflows(lines)
    lines.append("### ORCHESTRATOR\n")
    seg_orchestrator(lines)
    seg_documentation(lines)
    (out_dir / "golden_pipeline.txt").write_text("".join(lines), encoding="utf-8")
    shutil.rmtree(workdir, ignore_errors=True)
    print(f"[OK] golden generado: {out_dir / 'golden_pipeline.txt'}")
    return 0


def verify(out_dir: Path) -> int:
    golden = out_dir / "golden_pipeline.txt"
    if not golden.exists():
        print("[FAIL] no existe el golden")
        return 1
    expected = golden.read_text(encoding="utf-8")
    build(out_dir)
    if (out_dir / "golden_pipeline.txt").read_text(encoding="utf-8") == expected:
        print("[PASS] golden_pipeline.txt determinista")
        return 0
    print("[FAIL] golden difiere")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify"])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    out_dir = Path(ns.out); out_dir.mkdir(parents=True, exist_ok=True)
    return build(out_dir) if ns.cmd == "build" else verify(out_dir)


if __name__ == "__main__":
    sys.exit(main())
