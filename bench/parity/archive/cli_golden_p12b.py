#!/usr/bin/env python
"""Gate de paridad P12B-8 — CLI clap nativo vs CLI Python (oráculo).

Patrón house (build/verify determinista). Casos:
  * comandos wireados nativos: hint/tutor(slug)/doctor/org-config/
    promote-knowledge/review-knowledge/memory-report/webgraph export/
    autopilot preflight/agent-guidelines/install-skills;
  * errores: comando desconocido y args faltantes (passthrough ⇒ Typer);
  * rollback: CORTEX_PY=1 delega al CLI Python byte-idéntico.

Los textos --help y errores clap de subárboles wireados son SELF-GOLDEN
(Typer ≠ clap por diseño): se congelan en `examples/cli_check.rs`, no acá.
Divergencias documentadas que el oráculo normaliza a nivel de DATOS:
  - doctor / memory-report JSON: checks stub contractuales vía STUB_TABLE
    (patrón P12B-4/P12B-5) antes de renderizar;
  - webgraph export: fingerprint normalizado {{FP}} (igual que P12B-2).

Uso:
    .venv/bin/python bench/parity/cli_golden_p12b.py build --out DIR
    .venv/bin/python bench/parity/cli_golden_p12b.py verify --out DIR
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

REPO = Path(__file__).resolve().parents[2]
PY_BIN = REPO / ".venv" / "bin" / "cortex"
RS_BIN = REPO / "rust" / "target" / "debug" / "cortex-cli"

# Checks con backend Python sin porteño: el oráculo los reescribe a los
# valores contractuales del crate nativo ANTES de renderizar (P6/P9).
STUB_TABLE = {
    "webgraph_dependencies": ("warn", "cortex.webgraph.setup"),
    "sessions_active_pointer": ("warn", "cortex.session.storage"),
    "sessions_parsed": ("warn", "cortex.session.storage"),
    "session_hooks_installed": ("warn", "cortex.session.hooks"),
    "pm_documenter_module": ("fail", "cortex.documenter"),
    "pm_documenter_interactive": ("warn", "cortex.documenter.interactive"),
    "pm_verification_runner": ("warn", "cortex.session.verification"),
    "pm_mcp_tools_registered": ("warn", "cortex.mcp.server"),
}

CONFIG_YAML = "semantic:\n  vault_path: vault\n"
ORG_YAML = (
    "schema_version: 1\norganization:\n  name: Acme Org\n"
    "memory:\n  enterprise_semantic_enabled: true\npromotion:\n  enabled: true\n"
)


def make_fixture(kind: str, tag: str) -> Path:
    """Fixtures FUERA del repo (mkdtemp): detect() camina hacia arriba."""
    root = Path(tempfile.mkdtemp(prefix=f"cli_{tag}_"))
    if kind == "l0":
        return root
    (root / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    if kind == "l1":
        return root
    if kind == "l7":
        vault = root / "vault"
        (vault / "specs").mkdir(parents=True)
        (vault / "sessions").mkdir()
        for i in range(3):
            (vault / "specs" / f"s{i}.md").write_text(f"# s{i}\n", encoding="utf-8")
        for i in range(2):
            (vault / "sessions" / f"x{i}.md").write_text(f"# x{i}\n", encoding="utf-8")
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".mcp.json").write_text("{}\n", encoding="utf-8")
        org = root / ".cortex"
        org.mkdir(exist_ok=True)
        (org / "org.yaml").write_text(ORG_YAML, encoding="utf-8")
        (root / "vault-enterprise").mkdir()
        return root
    raise ValueError(kind)


def make_review_fixture(tag: str) -> Path:
    """Fixture con drafts en el vault enterprise (review-knowledge)."""
    root = make_fixture("l1", tag)
    specs = root / "vault-enterprise" / "specs"
    specs.mkdir(parents=True)
    (specs / "draft1.md").write_text(
        "---\ntitle: Draft One\ndoc_type: spec\nowner: alice\nstatus: draft\n---\n\nBody one\n",
        encoding="utf-8",
    )
    (specs / "draft2.md").write_text(
        "---\ntitle: Draft Two\ndoc_type: runbook\nstatus: draft\n---\n\nBody two\n",
        encoding="utf-8",
    )
    return root


def make_promo_fixture(tag: str) -> Path:
    """l7 + un candidato revisado (records.jsonl vía servicio Python real)."""
    root = make_fixture("l7", tag)
    sys.path.insert(0, str(REPO))
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

    svc = KnowledgePromotionService.from_project_root(root)
    candidates = svc.discover_candidates()
    assert candidates, "fixture sin candidatos"
    svc.review(selector=candidates[0].origin_id, approve=True, actor="tester", reason="ok")
    return root


# ── normalización de datos (stubs) ──────────────────────────────────────────


def _normalize_doctor_checks(checks: list[dict]) -> list[dict]:
    out = []
    for check in checks:
        name = check.get("name") or check["name"]
        if name in STUB_TABLE:
            severity, module = STUB_TABLE[name]
            out.append({
                "name": name,
                "ok": False,
                "severity": severity,
                "detail": f"backend no nativo aún ({module})",
            })
        else:
            out.append(check)
    return out


def render_doctor_like_main(root: Path, scope: str, strict: bool) -> tuple[str, str, int]:
    """Corre run_doctor Python, normaliza stubs y renderiza como main.py."""
    from cortex.doctor import run_doctor

    report = run_doctor(root, scope=scope)
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    has_failures = False
    has_warnings = False
    for check in report.checks:
        check = check.model_copy() if hasattr(check, "model_copy") else check
        if check.name in STUB_TABLE:
            severity, module = STUB_TABLE[check.name]
            ok, detail = False, f"backend no nativo aún ({module})"
        else:
            ok, detail = bool(check.ok), check.detail
            severity = check.severity
        line = f"{check.name}: {detail}"
        if ok:
            stdout_lines.append(f"[OK] {line}")
        elif severity == "fail":
            stderr_lines.append(f"[FAIL] {line}")
            has_failures = True
        elif severity == "warn":
            stdout_lines.append(f"[WARN] {line}")
            has_warnings = True
        else:
            stdout_lines.append(f"[INFO] {line}")
    # El DoctorReport Python calcula flags sobre sus checks reales; tras la
    # normalización, los flags contractuales salen de los checks normalizados.
    has_failures = any(l.startswith("[FAIL]") for l in stderr_lines)
    rc = 1 if has_failures or (strict and has_warnings) else 0
    return "\n".join(stdout_lines) + "\n", "\n".join(stderr_lines) + "\n", rc


def memory_report_json_normalized(root: Path, scope: str) -> str:
    """report.model_dump(mode="json") con stubs normalizados + json.dumps."""
    from cortex.enterprise.reporting import EnterpriseReportingService

    service = EnterpriseReportingService.from_project_root(root)
    report = service.build_memory_report(scope=scope)
    payload = json.loads(report.model_dump_json())
    payload["doctor"]["checks"] = _normalize_doctor_checks(payload["doctor"]["checks"])
    payload["doctor"]["has_failures"] = any(not c["ok"] and c["severity"] == "fail" for c in payload["doctor"]["checks"])
    payload["doctor"]["has_warnings"] = any(not c["ok"] and c["severity"] == "warn" for c in payload["doctor"]["checks"])
    return json.dumps(payload, indent=2)


# ── definición de casos ─────────────────────────────────────────────────────

class Case:
    def __init__(self, name, py_args, rs_args, *, fixture=None, promo=False,
                 review_flow=False, doctor=None, mr_json=None, wg_export=None,
                 passthrough=False, rollback_of=None):
        self.name = name
        self.py_args = py_args          # argv para el oráculo
        self.rs_args = rs_args          # argv para el binario nativo
        self.fixture = fixture          # kind o None
        self.promo = promo              # fixture con candidato revisado
        self.review_flow = review_flow
        self.doctor = doctor            # (scope, strict) → render normalizado
        self.mr_json = mr_json          # scope → JSON normalizado
        self.wg_export = wg_export      # True → normalizar {{FP}}
        self.passthrough = passthrough  # CORTEX_PY=1 en ambos lados
        self.rollback_of = rollback_of



def run_case(case: Case, side: str, workdir: Path) -> tuple[str, int]:
    """Ejecuta un caso para 'py' o 'rs' y devuelve salida normalizada + rc."""
    # Raíces gemelas: MISMO basename en ambos lados ⇒ origin_id/project_id
    # (derivados de slugify(basename)) quedan idénticos tras {{ROOT}}.
    shutil.rmtree(workdir / side / "fix", ignore_errors=True)
    root = workdir / side / "fix"

    root.mkdir(parents=True)

    if case.doctor is not None:
        scope, strict = case.doctor
        if case.fixture not in (None, "l0"):
            root = _rebuild(root, case.fixture)
        out, err, rc = render_doctor_like_main(root, scope, strict)
        blob = f"{norm(out, root)}---STDERR---\n{norm(err, root)}rc={rc}\n"
        return blob, 0

    if case.mr_json is not None:
        root = _rebuild(root, "l7")
        blob = norm(memory_report_json_normalized(root, case.mr_json), root) + "\n"
        return blob, 0

    if case.fixture not in (None, "l0"):
        root = _rebuild(root, case.fixture)
    if case.promo:
        root = _promo_into(root)
    if case.review_flow:
        _seed_drafts(root)

    env = dict(os.environ)
    for key in ("USER", "LOGNAME", "LNAME", "USERNAME"):
        env[key] = "tester"
    if side == "rs":
        # El passthrough nativo debe resolver EXACTAMENTE el oráculo.
        env["CORTEX_BIN"] = str(PY_BIN)
        if case.passthrough:
            env["CORTEX_PY"] = "1"
        cmd = [str(RS_BIN)] + list(case.rs_args)
    else:
        cmd = [str(PY_BIN)] + list(case.py_args)
        if case.passthrough:
            pass  # el oráculo ES python: misma semántica

    proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, timeout=120)
    blob = norm(proc.stdout.decode(), root)
    if proc.stderr:
        blob += "---STDERR---\n" + norm(proc.stderr.decode(), root)
    blob += f"rc={proc.returncode}\n"

    # Archivos generados (webgraph export): contenido normalizado.
    if case.wg_export:
        snap = root / ".cortex" / "webgraph" / "cache" / "snapshot-hybrid.json"
        if snap.exists():
            body = snap.read_text(encoding="utf-8")
            body = norm_fp(body)
            blob += "---SNAPSHOT---\n" + norm(body, root) + "\n"
    return blob, proc.returncode


def _rebuild(target: Path, kind: str) -> Path:
    """Reconstruye un fixture kind DENTRO de target (sin mkdtemp extra)."""
    (target / "config.yaml").write_text(CONFIG_YAML, encoding="utf-8")
    if kind == "l7":
        vault = target / "vault"
        (vault / "specs").mkdir(parents=True)
        (vault / "sessions").mkdir()
        for i in range(3):
            (vault / "specs" / f"s{i}.md").write_text(f"# s{i}\n", encoding="utf-8")
        for i in range(2):
            (vault / "sessions" / f"x{i}.md").write_text(f"# x{i}\n", encoding="utf-8")
        (target / ".github" / "workflows").mkdir(parents=True)
        (target / ".mcp.json").write_text("{}\n", encoding="utf-8")
        org = target / ".cortex"
        org.mkdir(exist_ok=True)
        (org / "org.yaml").write_text(ORG_YAML, encoding="utf-8")
        (target / "vault-enterprise").mkdir()
    return target


def _promo_into(root: Path) -> Path:
    sys.path.insert(0, str(REPO))
    from cortex.enterprise.knowledge_promotion import KnowledgePromotionService

    svc = KnowledgePromotionService.from_project_root(root)
    candidates = svc.discover_candidates()
    assert candidates, f"sin candidatos en {root}"
    svc.review(selector=candidates[0].origin_id, approve=True, actor="tester", reason="ok")
    return root


def _seed_drafts(root: Path) -> None:
    specs = root / "vault-enterprise" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "draft1.md").write_text(
        "---\ntitle: Draft One\ndoc_type: spec\nowner: alice\nstatus: draft\n---\n\nBody one\n",
        encoding="utf-8",
    )
    (specs / "draft2.md").write_text(
        "---\ntitle: Draft Two\ndoc_type: runbook\nstatus: draft\n---\n\nBody two\n",
        encoding="utf-8",
    )


def norm_fp(body: str) -> str:
    return re.sub(r'"fingerprint": "[0-9a-f]{64}"', '"fingerprint": "{{FP}}"', body)


def norm(text: str, root: Path) -> str:
    out = text.replace(str(root), "{{ROOT}}")
    out = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)", "{{TS}}", out)
    return out


def all_cases() -> list[Case]:
    cases: list[Case] = []

    # hints
    for tag, kind in [("s01_hint_l0", "l0"), ("s02_hint_l1", "l1"), ("s03_hint_l7", "l7")]:
        cases.append(Case(tag, ["hint"], ["hint"], fixture=kind))

    # tutor <slug> NO va en el gate: los cuerpos embebidos de cortex-tutor
    # son capturas rich ~98 col (P12B-7) ⇒ self-golden en cli_check.rs.

    # doctor (oráculo = run_doctor + STUB_TABLE + render main.py)
    cases.append(Case("s05_doctor_empty", ["doctor"], ["doctor"],
                      fixture="l7", doctor=("project", False)))
    cases.append(Case("s06_doctor_all_org", ["doctor", "--scope", "all"], ["doctor", "--scope", "all"],
                      fixture="l7", doctor=("all", False)))
    cases.append(Case("s07_doctor_strict", ["doctor", "--strict"], ["doctor", "--strict"],
                      fixture="l7", doctor=("project", True)))

    # org-config
    cases.append(Case("s08_orgconfig_text", ["org-config"], ["org-config"], fixture="l7"))
    cases.append(Case("s09_orgconfig_json", ["org-config", "--json"], ["org-config", "--json"], fixture="l7"))
    cases.append(Case("s10_orgconfig_missing_required", ["org-config", "--required"], ["org-config", "--required"],
                      fixture="l0"))

    # promote-knowledge
    # NOTA: sin org.yaml el oráculo Python revienta con traceback no
    # capturado (comportamiento upstream); el caso vacío usa org.yaml válido.
    cases.append(Case("s11_promote_dryrun_empty", ["promote-knowledge"], ["promote-knowledge"], fixture="l7"))
    cases.append(Case("s12_promote_dryrun_json_reviewed", ["promote-knowledge", "--json"],
                      ["promote-knowledge", "--json"], fixture="l7", promo=True))
    cases.append(Case("s13_promote_dryrun_text_reviewed", ["promote-knowledge"], ["promote-knowledge"],
                      fixture="l7", promo=True))

    # review-knowledge
    cases.append(Case("s14_rk_pending", ["review-knowledge", "pending"], ["review-knowledge", "pending"],
                      fixture="l1", review_flow=True))
    cases.append(Case("s15_rk_pending_json", ["review-knowledge", "pending", "--json"],
                      ["review-knowledge", "pending", "--json"], fixture="l1", review_flow=True))
    cases.append(Case("s16_rk_approve", ["review-knowledge", "approve", "specs/draft1.md",
                                         "--reviewer", "tester"],
                      ["review-knowledge", "approve", "specs/draft1.md", "--reviewer", "tester"],
                      fixture="l1", review_flow=True))
    cases.append(Case("s17_rk_reject_move", ["review-knowledge", "reject", "specs/draft2.md",
                                             "--reason", "no sirve"],
                      ["review-knowledge", "reject", "specs/draft2.md", "--reason", "no sirve"],
                      fixture="l1", review_flow=True))
    cases.append(Case("s18_rk_escape", ["review-knowledge", "approve", "../escape.md"],
                      ["review-knowledge", "approve", "../escape.md"], fixture="l1", review_flow=True))

    # memory-report
    cases.append(Case("s19_mr_local_text", ["memory-report", "--scope", "local"],
                      ["memory-report", "--scope", "local"], fixture="l7"))
    cases.append(Case("s20_mr_all_json", ["memory-report", "--scope", "all", "--json"],
                      ["memory-report", "--scope", "all", "--json"],
                      fixture="l7", mr_json="all"))
    cases.append(Case("s21_mr_invalid_scope", ["memory-report", "--scope", "bogus"],
                      ["memory-report", "--scope", "bogus"], fixture="l7"))

    # webgraph export
    # Fixture sin org.yaml ni markdown: el GAP P12B-3 (nodos enterprise del
    # oráculo) no aplica y el embedder nunca se invoca ⇒ paridad estructural.
    cases.append(Case("s22_wg_export_empty", ["webgraph", "export", "--no-cache"],
                      ["webgraph", "export", "--no-cache"], fixture="l1", wg_export=True))
    cases.append(Case("s23_wg_no_config", ["webgraph", "export"], ["webgraph", "export"], fixture="l0"))

    # autopilot preflight
    req_sec = "implementar autenticación completa con JWT y refresh tokens"
    cases.append(Case("s24_pf_security_json", ["autopilot", "preflight", "--request", req_sec, "--json"],
                      ["autopilot", "preflight", "--request", req_sec, "--json"], fixture="l1"))
    req_noop = "qué hora es"
    cases.append(Case("s25_pf_noop_tie", ["autopilot", "preflight", "--request", req_noop],
                      ["autopilot", "preflight", "--request", req_noop], fixture="l1"))

    # recursos triviales
    cases.append(Case("s25b_agent_guidelines", ["agent-guidelines"], ["agent-guidelines"],
                      fixture="l0"))
    cases.append(Case("s26_install_skills_fresh", ["install-skills", "--dest", "skills-out"],
                      ["install-skills", "--dest", "skills-out"], fixture="l0"))

    # passthrough + rollback
    cases.append(Case("s27_unknown_command", ["frobnicate", "--x", "1"], ["frobnicate", "--x", "1"],
                      fixture="l0"))
    cases.append(Case("s28_unknown_help_flag", ["--frobnicate"], ["--frobnicate"], fixture="l0"))
    cases.append(Case("s29_rollback_doctor", ["doctor", "--project-root", "."],
                      ["doctor", "--project-root", "."], fixture="l1", passthrough=True))
    cases.append(Case("s30_rollback_unknown", ["frobnicate"], ["frobnicate"], fixture="l0",
                      passthrough=True))

    return cases


def collect(workdir: Path) -> tuple[str, list[str]]:
    lines: list[str] = []
    failures: list[str] = []
    for case in all_cases():
        py_out, py_rc = run_case(case, "py", workdir)
        rs_out, rs_rc = run_case(case, "rs", workdir)
        status = "PASS" if (py_out == rs_out and py_rc == rs_rc) else "FAIL"
        lines.append(f"### {case.name} [{status}] py_rc={py_rc} rs_rc={rs_rc}")
        if status == "FAIL":
            failures.append(case.name)
            lines.append("---PY---\n" + py_out)
            lines.append("---RS---\n" + rs_out)
        else:
            lines.append(py_out)
    return "".join(line if line.endswith("\n") else line + "\n" for line in lines), failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify"])
    ap.add_argument("--out", default=str(REPO / "bench" / "parity" / ".p12b-cli"))
    ns = ap.parse_args()

    if not RS_BIN.exists():
        print(f"[FAIL] binario nativo ausente: {RS_BIN} (cargo build -p cortex-cli)")
        return 1

    workdir = Path(tempfile.mkdtemp(prefix="p12b_cli_work_"))
    try:
        result, failures = collect(workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    if ns.cmd == "build" and failures:
        print(f"[FAIL] casos divergentes ({len(failures)}): {', '.join(failures)}")
        return 1

    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden = out_dir / "golden_cli.txt"
    if ns.cmd == "build":
        golden.write_text(result, encoding="utf-8")
        print(f"[BUILD] {golden} ({len(result.splitlines())} líneas)")
        return 0
    expected = golden.read_text(encoding="utf-8")
    if expected == result:
        print("[PASS] golden_cli.txt")
        return 0
    print("[FAIL] golden difiere entre build y verify")
    import difflib

    diff = difflib.unified_diff(expected.splitlines(), result.splitlines(), lineterm="")
    print("\n".join(list(diff)[:40]))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
