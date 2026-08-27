#!/usr/bin/env python3
"""Oráculo de paridad P11-ci — plugin CI (`cortex ci`) vs cortex-app nativo.

Sub-comandos:
  build   — construye el fixture determinista (repo git con fechas fijadas +
            sesiones de servicio) y captura los goldens de los comandos CI.
  verify  — regenera TODO en temp y compara contra lo commiteado.

Uso:
  python ci_golden_p11.py build --out bench/parity/golden_ci \
      [--fixtures /tmp/p11fix]
  python ci_golden_p11.py verify --out bench/parity/golden_ci

El lado Rust se verifica con:
  cargo run -q -p cortex-app --example ci_check -- <fixtures_dir> <golden_dir>

CONTRATO de normalización (documentado; el resto es byte-parity):
  1. ``{{ROOT}}`` reemplaza la ruta absoluta del fixture/workdir.
  2. ``"duration_ms": N`` → ``{{MS}}`` (los tiempos de hooks son reales).
  3. Duraciones Markdown ``(X.Xs,`` → ``({{DUR}}s,`` en render_pr_comment.
  4. Ids de review-session generados con la fecha de HOY
     (``YYYY-MM-DD_<slug>-review``) → prefijo ``{{DATE}}_``. Los ids de las
     sesiones del fixture usan fechas fijas de 2026-05 y NO se normalizan.
  5. Un único ``\\n`` final.

DETERMINISMO DEL FIXTURE (para siempre):
  - Commits git con GIT_AUTHOR_DATE/GIT_COMMITTER_DATE fijados ⇒ SHAs
    reproducibles entre corridas y máquinas.
  - Sesiones creadas vía SessionService.open con specs commiteadas;
    estados terminales (HANDOFF/ABANDONED) vía service.close.
  - Hooks deterministas: comandos ``true`` / ``false`` (exit 0/1).
  - El flujo de review-session (mutante) corre sobre una COPIA del fixture;
    el fixture dejado en --fixtures queda PRISTINE para el checker Rust.
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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Cortex Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@cortex.local",
    "GIT_COMMITTER_NAME": "Cortex Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@cortex.local",
    "GIT_AUTHOR_DATE": "2026-05-10T12:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-05-10T12:00:00+00:00",
}

SPEC_TMPL = """---
title: {title}
doc_type: spec
goal: {goal}
files_in_scope:
{scope}
verification_hooks:
  - {{name: smoke, command: "{cmd}", required: {required}, success_criteria: "exit 0", timeout_seconds: 30}}
---
"""

DIFF_IN_SCOPE = "--- a/src/x.py\n+++ b/src/x.py\n@@ -1 +1,2 @@\n x\n+new\n"
DIFF_OUT_SCOPE = (
    DIFF_IN_SCOPE + "--- a/src/unexpected.py\n+++ b/src/unexpected.py\n@@\n"
)
DIFF_OTHER = "--- a/src/other.py\n+++ b/src/other.py\n@@\n"


def _git(repo: Path, *args: str, env: dict | None = None) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, env=env or GIT_ENV,
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


def construir_fixture(base: Path) -> Path:
    """Repo determinista + 6 sesiones de servicio. Devuelve el root."""
    from cortex.session import SessionStatus
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage

    repo = base / "proyecto"
    (repo / ".cortex" / "sessions").mkdir(parents=True)
    (repo / "vault" / "specs").mkdir(parents=True)
    (repo / "src").mkdir()

    def spec_file(name: str, title: str, goal: str, scope: list[str],
                  cmd: str = "true", required: bool = True) -> None:
        body = SPEC_TMPL.format(
            title=title, goal=goal,
            scope="".join(f"  - {s}\n" for s in scope),
            cmd=cmd, required="true" if required else "false",
        )
        (repo / "vault" / "specs" / f"{name}.md").write_text(
            body, encoding="utf-8"
        )

    spec_file("2026-05-10_abandoned", "abandoned", "x", ["src/x.py"])
    spec_file("2026-05-11_handoff", "handoff", "x", ["src/x.py"])
    spec_file("2026-05-12_hookfail", "hookfail", "x", ["src/x.py"], cmd="false")
    spec_file("2026-05-13_optfail", "optfail", "x", ["src/x.py"],
              cmd="false", required=False)
    spec_file("2026-05-14_demo", "demo", "keep x working", ["src/x.py"])

    (repo / "src" / "x.py").write_text("def x(): return 1\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")

    # Segundo commit: agrega src/other.py ⇒ HEAD2 (fechas distintas ⇒ SHA distinto).
    (repo / "src" / "other.py").write_text("# other\n", encoding="utf-8")
    _git(repo, "add", ".")
    env2 = {**GIT_ENV, "GIT_AUTHOR_DATE": "2026-05-11T12:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-05-11T12:00:00+00:00"}
    _git(repo, "commit", "-q", "-m", "second", env=env2)
    head2 = _git(repo, "rev-parse", "HEAD")

    service = SessionService(SessionStorage(repo / ".cortex" / "sessions"),
                             repo_root=repo)

    # Sesión en rama feature/x (para matching by_branch).
    _git(repo, "checkout", "-q", "-b", "feature/x")
    service.open(spec_id="2026-05-15_branchy",
                 spec_path="vault/specs/2026-05-14_demo.md",
                 spec_summary="branchy")
    _git(repo, "checkout", "-q", "main")

    for sid, estado in [
        ("2026-05-10_abandoned", SessionStatus.ABANDONED),
        ("2026-05-11_handoff", SessionStatus.HANDOFF),
        ("2026-05-12_hookfail", None),
        ("2026-05-13_optfail", None),
        ("2026-05-14_demo", None),
    ]:
        rec = service.open(spec_id=sid, spec_path=f"vault/specs/{sid}.md",
                           spec_summary=sid.split("_")[1])
        if estado is not None:
            service.close(rec.session_id, status=estado,
                          documenter_decision=estado)

    # Manifest para el checker Rust (SHA deterministas).
    (repo / ".cortex" / "p11_manifest.json").write_text(
        json.dumps({"head2": head2}), encoding="utf-8"
    )
    return repo


# ── secuencia de escenarios ────────────────────────────────────────────────

def correr_secuencia(work: Path) -> str:
    """Ejecuta todos los escenarios sobre `work` y devuelve la salida
    cruda concatenada con headers de rc (sin normalizar)."""
    from cortex.cli.ci import ci_app
    from typer.testing import CliRunner

    runner = CliRunner()
    head2 = json.loads(
        (work / ".cortex" / "p11_manifest.json").read_text(encoding="utf-8")
    )["head2"]
    root = ["--project-root", str(work)]
    bloques: list[str] = []
    ids: dict[str, str] = {}   # rsN → session_id de open-review-session

    def ci(titulo: str, *args: str) -> int:
        # --project-root es opción de CADA comando (no del sub-app): va
        # primero tras el nombre del comando.
        r = runner.invoke(ci_app, [args[0], *root, *args[1:]])
        bloques.append(f"### {titulo} · rc={r.exit_code}\n{r.output}")
        return r.exit_code

    def diff_file(name: str, content: str) -> str:
        p = work / name
        p.write_text(content, encoding="utf-8")
        return str(p)

    d_in = diff_file("in.diff", DIFF_IN_SCOPE)
    d_out = diff_file("out.diff", DIFF_OUT_SCOPE)
    d_other = diff_file("other.diff", DIFF_OTHER)

    # JSON crudo de S06 (para --from-validation-result posterior).
    rc = ci("S00 validate-pr optfail crudo (no golden)", "validate-pr",
            "--diff", d_in, "--session", "2026-05-13_optfail",
            "--format", "json")
    assert rc == 1, "escenario semilla debía warn"
    r_semilla = runner.invoke(ci_app, ["validate-pr", *root, "--diff", d_in,
                                       "--session", "2026-05-13_optfail",
                                       "--format", "json"])
    (work / "validation_optfail.json").write_text(r_semilla.output,
                                                  encoding="utf-8")
    bloques.clear()  # S00 no entra al golden

    ci("S01 validate-pr explicit pass (json)", "validate-pr",
       "--diff", d_in, "--session", "2026-05-14_demo", "--format", "json")
    ci("S02 validate-pr no-match blocked (json)", "validate-pr",
       "--diff", d_in, "--format", "json")
    ci("S03 validate-pr out-of-scope warn (json)", "validate-pr",
       "--diff", d_out, "--session", "2026-05-14_demo", "--format", "json")
    ci("S04 validate-pr unimplemented blocked (json)", "validate-pr",
       "--diff", d_other, "--session", "2026-05-14_demo", "--format", "json")
    ci("S05 validate-pr required-hook-fail blocked (json)", "validate-pr",
       "--diff", d_in, "--session", "2026-05-12_hookfail", "--format", "json")
    ci("S06 validate-pr optional-hook-fail warn (json)", "validate-pr",
       "--diff", d_in, "--session", "2026-05-13_optfail", "--format", "json")
    ci("S07 validate-pr handoff warn (json)", "validate-pr",
       "--diff", d_in, "--session", "2026-05-11_handoff", "--format", "json")
    ci("S08 validate-pr abandoned blocked (json)", "validate-pr",
       "--diff", d_in, "--session", "2026-05-10_abandoned", "--format", "json")
    ci("S09 validate-pr by_branch pass (json)", "validate-pr",
       "--diff", d_in, "--head-branch", "feature/x", "--format", "json")
    ci("S10 validate-pr by_commit->abandoned blocked (json)", "validate-pr",
       "--diff", d_in, "--base-commit", head2, "--format", "json")
    ci("S11 validate-pr out-of-scope warn (text)", "validate-pr",
       "--diff", d_out, "--session", "2026-05-14_demo", "--format", "text")
    ci("S12 validate-pr pass (pr-comment)", "validate-pr",
       "--diff", d_in, "--session", "2026-05-14_demo", "--format",
       "pr-comment")
    ci("S13 validate-pr no-match (pr-comment)", "validate-pr",
       "--diff", d_in, "--format", "pr-comment")

    def open_rs(tag: str, titulo: str, *extra: str) -> int:
        rc = ci(titulo, "open-review-session", *extra, "--json")
        import json as _j
        payload = _j.loads(bloques[-1].split("\n", 1)[1])
        ids[tag] = payload["session_id"]
        return rc

    def last_payload_line() -> str:
        return bloques[-1].rstrip("\n").split("\n")[-1]

    open_rs("rs1", "S14 open-review-session pr42 (json)",
            "--pr-number", "42", "--base-commit", "a" * 40,
            "--head-branch", "feature/ci")
    ci("S15 report-checkpoint manual (json)", "report-checkpoint",
       "--session-id", ids["rs1"], "--manual-claim", "manual claim",
       "--manual-artifact", "src/x.py", "--note", "initial review", "--json")
    ci("S16 report-checkpoint from-validation (json)", "report-checkpoint",
       "--session-id", ids["rs1"], "--from-validation-result",
       str(work / "validation_optfail.json"), "--json")
    ci("S17 close-review-session closed (json)", "close-review-session",
       "--session-id", ids["rs1"], "--status", "closed", "--json")

    rc = ci("S18 open-review-session branch (texto)", "open-review-session",
            "--base-commit", "b" * 40, "--head-branch", "feature/ci")
    assert rc == 0
    # Formato texto ⇒ la salida es el session_id pelado.
    ids["rs2"] = last_payload_line().strip()
    ci("S19 report-checkpoint from-validation (texto)", "report-checkpoint",
       "--session-id", ids["rs2"], "--from-validation-result",
       str(work / "validation_optfail.json"))
    ci("S20 close-review-session handoff reason (texto)",
       "close-review-session", "--session-id", ids["rs2"],
       "--status", "handoff", "--reason", "hooks failed")

    open_rs("rs3", "S21 open-review-session pr7 (json)",
            "--pr-number", "7", "--base-commit", "c" * 40,
            "--head-branch", "feature/cr")
    ci("S22 report-checkpoint from-validation (json)", "report-checkpoint",
       "--session-id", ids["rs3"], "--from-validation-result",
       str(work / "validation_optfail.json"), "--json")
    ci("S23 close-review-session closed ci-review (json)",
       "close-review-session", "--session-id", ids["rs3"],
       "--status", "closed", "--json")

    return "".join(bloques)


# ── normalización ──────────────────────────────────────────────────────────

def _normalizar(texto: str, work: Path) -> str:
    texto = texto.replace(str(work), "{{ROOT}}")
    texto = re.sub(r'"duration_ms": \d+', '"duration_ms": "{{MS}}"', texto)
    texto = re.sub(r"\(\d+\.\ds,", "({{DUR}}s,", texto)
    # Ids de review-session generados hoy ⇒ fecha normalizada (sufijo -review).
    texto = re.sub(
        r"\d{4}-\d{2}-\d{2}_(?=[a-z0-9-]+-review\b)", "{{DATE}}_", texto
    )
    if not texto.endswith("\n"):
        texto += "\n"
    return texto


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path,
                       default=REPO_ROOT / "bench/parity/golden_ci")
        p.add_argument("--fixtures", type=Path, default=None)
    ns = ap.parse_args()
    verificar = ns.cmd == "verify"

    ns.out.mkdir(parents=True, exist_ok=True)
    destino_golden = ns.out / "golden_ci.txt"

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        pristine = construir_fixture(base / "fixtures")
        work = base / "work"
        shutil.copytree(pristine, work)

        contenido = _normalizar(correr_secuencia(work), work)

        if verificar:
            esperado = destino_golden.read_text(encoding="utf-8")
            if contenido == esperado:
                print("[PASS] golden_ci.txt")
                print("\n✅ ORÁCULO DETERMINISTA")
                return 0
            print("[FAIL] golden_ci.txt difiere")
            import difflib
            for l in list(difflib.unified_diff(
                    esperado.splitlines(), contenido.splitlines(),
                    lineterm=""))[:80]:
                print(l)
            print(f"\n❌ diferencias ({destino_golden})")
            return 1

        destino_golden.write_text(contenido, encoding="utf-8")
        print(f"[capturado] {destino_golden}")

        if ns.fixtures:
            if ns.fixtures.exists():
                shutil.rmtree(ns.fixtures)
            real = construir_fixture(ns.fixtures)
            print(f"fixture reconstruido → {real}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
