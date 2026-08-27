#!/usr/bin/env python3
"""Oráculo de paridad P12B-1 — workspace/layout+misc vs cortex-workspace.

Sub-comandos:
  build   — construye los fixtures deterministas y captura el golden.
  verify  — regenera TODO en temp y compara contra lo commiteado.

Uso:
  python workspace_golden_p12b.py build --out bench/parity/golden_workspace \
      [--fixtures /tmp/p12bfix]
  python workspace_golden_p12b.py verify --out bench/parity/golden_workspace

El lado Rust se verifica con:
  cargo run -q -p cortex-workspace --example workspace_check -- \
      <fixtures_dir> <golden_dir>

CONTRATO de normalización (documentado; el resto es byte-parity):
  1. ``{{ROOT}}`` reemplaza la ruta absoluta de la base de fixtures.
  2. Un único ``\\n`` final.

DETERMINISMO DEL FIXTURE (para siempre):
  - Escenarios de layout S01–S08 creados con marcadores fijos; discovery
    camina hacia arriba ⇒ los padres del tmpdir NO deben contener
    ``config.yaml``/``.cortex`` (condición estándar de máquina de captura;
    idéntica en ambos lados ⇒ la paridad es robusta aunque varíe).
  - Repo git REAL (S09) con fecha fijada y branch ``feature/Mi_Rama``:
    ``rev-parse`` es puro naming ⇒ determinista entre corridas/máquinas.
  - Skills: hashes SHA-256 de los recursos del paquete instalado (el lado
    Rust los tiene embebidos desde los mismos archivos).
  - Fixtures SIN symlinks: ``Path.resolve()`` ≡ canonicalización léxica.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
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
    "GIT_AUTHOR_DATE": "2026-08-20T12:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-08-20T12:00:00+00:00",
}

WS_YAML_V2 = (
    "layout_version: 2\nprojects:\n- id: primary\n  path: .\n  role: owner\n"
)


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, env=GIT_ENV,
        capture_output=True, text=True, check=True,
    )
    return r.stdout.strip()


# ── construcción de escenarios ──────────────────────────────────────────────

def s01_new_full(base: Path) -> Path:
    repo = base / "s01_new_full"
    (repo / ".cortex" / "vault").mkdir(parents=True)
    (repo / ".cortex" / "config.yaml").write_text(
        "episodic:\n  persist_dir: memory\n", encoding="utf-8")
    (repo / ".cortex" / "workspace.yaml").write_text(WS_YAML_V2, encoding="utf-8")
    (repo / ".git").mkdir()
    return repo


def s02_new_no_wsyaml(base: Path) -> Path:
    repo = base / "s02_new_no_wsyaml"
    (repo / ".cortex" / "vault").mkdir(parents=True)
    (repo / ".cortex" / "config.yaml").write_text(
        "episodic:\n  persist_dir: memory\n", encoding="utf-8")
    (repo / ".git").mkdir()
    return repo


def s03_legacy(base: Path) -> Path:
    repo = base / "s03_legacy"
    (repo / "vault").mkdir(parents=True)
    (repo / ".memory").mkdir()
    (repo / ".cortex" / "skills").mkdir(parents=True)
    (repo / ".cortex" / "subagents").mkdir()
    (repo / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n", encoding="utf-8")
    (repo / ".cortex" / "org.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    (repo / ".git").mkdir()
    return repo


def s04_bootstrap(base: Path) -> Path:
    repo = base / "s04_bootstrap"
    repo.mkdir()
    return repo


def s05_both_configs(base: Path) -> Path:
    repo = base / "s05_both_configs"
    (repo / ".cortex").mkdir(parents=True)
    (repo / "config.yaml").write_text("legacy: true\n", encoding="utf-8")
    (repo / ".cortex" / "config.yaml").write_text("new: true\n", encoding="utf-8")
    (repo / ".cortex" / "workspace.yaml").write_text(WS_YAML_V2, encoding="utf-8")
    (repo / ".git").mkdir()
    return repo


def s06_ws_yaml_v1(base: Path) -> Path:
    repo = base / "s06_ws_yaml_v1"
    (repo / ".cortex").mkdir(parents=True)
    (repo / ".cortex" / "workspace.yaml").write_text(
        "layout_version: 1\nprojects: []\n", encoding="utf-8")
    (repo / "config.yaml").write_text("x: y\n", encoding="utf-8")
    (repo / ".git").mkdir()
    return repo


def s07_legacy_subdir(base: Path) -> Path:
    """Mismo legacy; el DISCOVERY arranca desde repo/vault/specs."""
    repo = base / "s07_legacy_subdir"
    (repo / "vault" / "specs").mkdir(parents=True)
    (repo / ".memory").mkdir()
    (repo / ".cortex" / "subagents").mkdir(parents=True)
    (repo / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n", encoding="utf-8")
    (repo / ".git").mkdir()
    return repo / "vault" / "specs"


def s08_start_inside_cortex(base: Path) -> Path:
    """Start DENTRO de .cortex ⇒ ese nivel se salta y halla el repo padre."""
    repo = base / "s08_inside_cortex"
    (repo / ".cortex" / "skills").mkdir(parents=True)
    (repo / ".cortex" / "workspace.yaml").write_text(WS_YAML_V2, encoding="utf-8")
    (repo / ".git").mkdir()
    return repo / ".cortex" / "skills"


def s09_real_git_repo(base: Path) -> Path:
    repo = base / "s09_real_git"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "x.py").write_text("def x(): return 1\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "feature/Mi_Rama")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


ESCENARIOS = [
    ("S01_new_full", s01_new_full),
    ("S02_new_no_wsyaml", s02_new_no_wsyaml),
    ("S03_legacy", s03_legacy),
    ("S04_bootstrap", s04_bootstrap),
    ("S05_both_configs", s05_both_configs),
    ("S06_ws_yaml_v1", s06_ws_yaml_v1),
    ("S07_legacy_subdir", s07_legacy_subdir),
    ("S08_start_inside_cortex", s08_start_inside_cortex),
]

# ── sección layout: dump canónico ───────────────────────────────────────────

PROPIEDADES = [
    "config_path", "org_config_path", "vault_path", "enterprise_vault_path",
    "episodic_memory_path", "enterprise_memory_path", "skills_dir",
    "sessions_dir", "subagents_dir", "agent_guidelines_path",
    "system_prompt_path", "workspace_yaml_path", "webgraph_dir",
    "webgraph_config_path", "webgraph_workspace_path", "webgraph_cache_dir",
    "logs_dir", "scripts_dir", "workflows_dir", "promotion_records_path",
    "promotion_dir", "context_md_path", "vault_index_path", "gitignore_path",
    "legacy_config_path", "legacy_vault_path", "legacy_memory_path",
    "legacy_org_config_path",
]


def dump_layout(nombre: str, start: Path, base: Path) -> str:
    from cortex.workspace import WorkspaceLayout

    l = WorkspaceLayout.discover(start)
    data = {
        "escenario": nombre,
        "repo_root": str(l.repo_root),
        "workspace_root": str(l.workspace_root),
        "is_legacy_layout": l.is_legacy_layout,
        "is_new_layout": l.is_new_layout,
    }
    for prop in PROPIEDADES:
        data[prop] = str(getattr(l, prop))
    data["resolve_vault"] = str(l.resolve_workspace_relative(Path("vault")))
    data["resolve_memory"] = str(l.resolve_workspace_relative(Path(".memory")))
    data["resolve_abs"] = str(l.resolve_workspace_relative(
        base / "abs" / "passthrough.md"))
    data["repr"] = repr(l)
    texto = json.dumps(data, indent=2, ensure_ascii=False)
    return texto.replace(str(base), "{{ROOT}}")


# ── sección handoff ─────────────────────────────────────────────────────────

CLAIMS_ZOO = [
    "Decisión: usar RRF",
    "123",
    "yes",
    "null",
    "abc # comment",
    "- item",
    "con espacio ",
    "ver https://x.io/a",
    "[algo], {otro}",
    "*ref",
    "&ancla",
    "%tag",
    "@user",
    "`code`",
    "'citado",
    'dijo "hola"',
    "d'junio",
    "-> flecha",
    "? duda",
]


def seccion_handoff() -> str:
    from cortex.handoff import AgentHandoff, ArtifactProduced

    bloques: list[str] = []

    def emitir(tag: str, h: AgentHandoff) -> None:
        bloques.append(f"### {tag}\n{h.to_yaml()}roundtrip: "
                       f"{'OK' if AgentHandoff.from_yaml(h.to_yaml()) == h else 'FAIL'}")

    emitir("H01_tipico", AgentHandoff(
        agent="cortex-code-implementer", status="complete",
        verified_claims=["auth refactorizada a JWT"],
        suggested_adr=True, suggested_adr_reason="decisión de tokens"))
    emitir("H02_artifacts", AgentHandoff(
        agent="cortex-documenter", status="partial",
        verified_claims=["docs generados"],
        artifacts_produced=[
            ArtifactProduced(path="src/auth.py", action="modified",
                             lines_changed=47),
            ArtifactProduced(path="docs/nuevo.md", action="created",
                             lines_added=120),
        ],
        context_for_next=["revisar gates de calidad"],
        suggested_adr=False))
    emitir("H03_folding", AgentHandoff(
        agent="cortex-sync", status="complete",
        verified_claims=["una afirmación bastante larga que supera los ochenta "
                         "caracteres de ancho para ver el plegado"]))
    emitir("H04_zoo", AgentHandoff(
        agent="cortex-security-auditor", status="blocked",
        verified_claims=list(CLAIMS_ZOO)))
    emitir("H05_multiline_tab", AgentHandoff(
        agent="cortex-test-verifier", status="partial",
        verified_claims=["linea1\nlinea2", "tab\taqui"]))
    emitir("H06_minimo", AgentHandoff(
        agent="cortex-SDDwork", status="complete"))

    # Validaciones: entradas inválidas deben ser RECHAZADAS en ambos lados
    # (los mensajes de error son específicos de cada runtime, no se congelan).
    invalidos = [
        "- solo\n- lista\n",                                  # raíz no-mapping
        "agent: desconocido\nstatus: complete\n",             # literal agent
        "agent: cortex-sync\nstatus: done\n",                 # literal status
        "agent: cortex-sync\n",                               # falta status
    ]
    for i, texto in enumerate(invalidos, 1):
        try:
            AgentHandoff.from_yaml(texto)
            bloques.append(f"### invalid_{i}\nFALLO: aceptó entrada inválida")
        except Exception:
            bloques.append(f"### invalid_{i}\nRECHAZADO")
    try:
        h = AgentHandoff.from_yaml(
            "agent: cortex-sync\nstatus: complete\nextra: se ignora\n")
        bloques.append(f"### unknown_field\nOK(agent={h.agent},status={h.status})")
    except Exception as exc:  # pragma: no cover
        bloques.append(f"### unknown_field\nFALLO: {exc}")

    return "\n".join(bloques)


# ── sección git_policy + runtime_context ────────────────────────────────────

SLUGIFY_CASOS = [
    "Mi Rama Feature",
    "¡Hola, Mundo!",
    "feature/Mi_Rama",
    "   ",
    "---",
    "ya-tiene-formato.ok_v1",
]


def seccion_politicas(repo_nuevo: Path, repo_legacy: Path,
                      repo_real: Path, work_skills: Path) -> str:
    from cortex.git_policy import (
        recommended_gitignore_snippet, gitignore_contains,
    )
    from cortex.runtime_context import (
        slugify, detect_git_branch, detect_git_repo_path,
        resolve_episodic_persist_dir,
    )
    from cortex.skills import install_skills
    from cortex.workspace import WorkspaceLayout

    bloques: list[str] = []
    ln = WorkspaceLayout.discover(repo_nuevo)
    ll = WorkspaceLayout.discover(repo_legacy)

    bloques.append("### snippet_new\n" + recommended_gitignore_snippet(layout=ln))
    bloques.append("### snippet_legacy\n" + recommended_gitignore_snippet(layout=ll))
    bloques.append("### snippet_default\n" + recommended_gitignore_snippet())

    gi = repo_nuevo / ".gitignore"
    gi.write_text("# comentario\n\n.memory/\n  *.chroma/  \n", encoding="utf-8")
    chequeos = [".memory/", "  .memory/  ", "*.chroma/",
                "vault/sessions/", "# comentario"]
    filas = [f"{c!r}={gitignore_contains(repo_nuevo, c)}" for c in chequeos]
    bloques.append("### gitignore_contains\n" + "\n".join(filas))

    filas = [f"{v!r}={slugify(v)!r}" for v in SLUGIFY_CASOS]
    filas.append(f"fallback={slugify('   ', fallback='fb')!r}")
    bloques.append("### slugify\n" + "\n".join(filas))

    # Fake git (directorio .git vacío): fallbacks deterministas.
    fake = repo_nuevo  # no tiene repo válido… usamos bootstrap dir dedicado
    fake = repo_nuevo.parent / "fake_git"
    fake.mkdir(exist_ok=True)
    (fake / ".git").mkdir(exist_ok=True)
    bloques.append("### git_fake\n"
                   f"branch={detect_git_branch(fake)!r}\n"
                   f"toplevel={detect_git_repo_path(fake)!r}")
    cfgs = [("memory", "project", ""), (".memory/chroma", "branch", ""),
            ("memory", "custom", "Mi Equipo!"), ("memory", "custom", "  ")]
    for pd, mode, ns in cfgs:
        out = resolve_episodic_persist_dir(fake, {"persist_dir": pd,
                                                  "namespace_mode": mode,
                                                  "namespace_value": ns})
        bloques.append(f"persist({mode},{pd!r},{ns!r})={out!r}")

    # Repo git REAL: branch y toplevel reales.
    bloques.append("### git_real\n"
                   f"branch={detect_git_branch(repo_real)!r}\n"
                   f"toplevel={{ROOT}}")
    for pd, mode, ns in [("memory", "project", ""), (".memory/c", "branch", "")]:
        out = resolve_episodic_persist_dir(repo_real, {"persist_dir": pd,
                                                       "namespace_mode": mode,
                                                       "namespace_value": ns})
        bloques.append(f"real_persist({mode},{pd!r})="
                       + str(out).replace(str(repo_real), "{{ROOT}}"))

    # Skills: instalación fresca + re-instalación, con hashes.
    destino = work_skills / "skills"
    primera = install_skills(destino)
    segunda = install_skills(destino)
    filas = []
    for nombre in primera:
        base_skill = destino / nombre.split(" ")[0]
        archivos = sorted(p.relative_to(base_skill).as_posix()
                          for p in base_skill.rglob("*") if p.is_file())
        hashes = ";".join(
            f"{rel}:{hashlib.sha256((base_skill / rel).read_bytes()).hexdigest()[:12]}"
            for rel in archivos)
        filas.append(f"{nombre}::{hashes}")
    bloques.append("### skills_fresh\n" + "\n".join(filas))
    bloques.append("### skills_again\n" + "\n".join(segunda))

    return "\n".join(bloques).replace(str(repo_nuevo), "{{ROOT}}")


# ── secuencia completa ──────────────────────────────────────────────────────

def construir_fixtures(base: Path) -> tuple[list[tuple[str, Path]], Path, Path]:
    pares = [(n, fn(base)) for n, fn in ESCENARIOS]
    real = s09_real_git_repo(base)
    legacy = base / "s03_legacy"
    nuevo = base / "s01_new_full"
    return pares, nuevo, legacy, real


def correr_secuencia(base: Path) -> str:
    pares, nuevo, legacy, real = construir_fixtures(base)
    work_skills = base / "work"
    work_skills.mkdir(exist_ok=True)

    bloques: list[str] = []
    for nombre, start in pares:
        bloques.append(dump_layout(nombre, start, base))
    bloques.append(seccion_handoff())
    bloques.append(seccion_politicas(nuevo, legacy, real, work_skills))
    return "\n".join(bloques) + "\n"


def _normalizar(texto: str, base: Path) -> str:
    texto = texto.replace(str(base), "{{ROOT}}")
    if not texto.endswith("\n"):
        texto += "\n"
    return texto


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--out", type=Path,
                       default=REPO_ROOT / "bench/parity/golden_workspace")
        p.add_argument("--fixtures", type=Path, default=None)
    ns = ap.parse_args()
    verificar = ns.cmd == "verify"

    ns.out.mkdir(parents=True, exist_ok=True)
    destino_golden = ns.out / "golden_workspace.txt"

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "fixtures"
        base.mkdir()
        contenido = _normalizar(correr_secuencia(base), base)

        if verificar:
            esperado = destino_golden.read_text(encoding="utf-8")
            if contenido == esperado:
                print("[PASS] golden_workspace.txt")
                print("\n✅ ORÁCULO DETERMINISTA")
                rc = 0
            else:
                print("[FAIL] golden_workspace.txt difiere")
                for l in list(difflib.unified_diff(
                        esperado.splitlines(), contenido.splitlines(),
                        lineterm=""))[:80]:
                    print(l)
                print(f"\n❌ diferencias ({destino_golden})")
                rc = 1
        else:
            destino_golden.write_text(contenido, encoding="utf-8")
            print(f"[capturado] {destino_golden}")
            rc = 0

        if ns.fixtures:
            if ns.fixtures.exists():
                shutil.rmtree(ns.fixtures)
            ns.fixtures.mkdir(parents=True)
            construir_fixtures(ns.fixtures)
            print(f"fixture reconstruido → {ns.fixtures}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
