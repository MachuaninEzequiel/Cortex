#!/usr/bin/env python3
"""Oráculo P8d: inyección/uninstall de los 11 IDE adapters byte-a-byte.

Genera un proyecto fixture determinista (SSoT de skills/subagents bajo
.cortex/) + un HOME fixture redirigido, congela el reloj y corre cada
adapter de cortex/ide/adapters/ en tres escenarios:

    <ide>__fresh      proyecto limpio → inject_profiles + inject_mcp
    <ide>__existing   proyecto/home con configs ajenas pre-sembradas → inject
    <ide>__uninstall  existing → inject → uninstall → árbol final

Salida (por escenario):
    bench/parity/golden_setup/ide/<ide>__<scenario>/manifest.json

con ``reports`` (listas devueltas, ordenadas — el glob de subagents de
opencode.py NO es determinista y solo cambia el ORDEN de la lista, no los
archivos escritos) y ``files`` (map "<scope>:<relpath>" → contenido,
scope ∈ {project,home}).

Normalizaciones pactadas (igual que P6):
    str(project_root) → {{ROOT}}
    str(home)         → {{HOME}}

Reloj congelado 2026-08-24T12:34:56 patcheando ``datetime`` en
cortex.ide.base Y en antigravity/windsurf (tienen _unique_backup propio con
timestamp microsegundo). ``HOME`` se redirige por env var (expanduser) y
``CODEX_HOME`` apunta a <home>/.codex.

El test Rust (cortex-setup/tests/ide_parity.rs) reconstruye los mismos
fixtures, corre sus adapters con IdeCtx{home, now congelado} y compara los
manifests estructuralmente (mapas sin orden, arrays de reports ordenados).

Modo verify (regenera en temp y compara contra lo commiteado):

    .venv/bin/python bench/parity/p8_ide_golden.py --verify
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

OUT = REPO / "bench/parity/golden_setup/ide"

FROZEN = datetime(2026, 8, 24, 12, 34, 56)

IDES = [
    "claude_code",
    "opencode",
    "pi",
    "codex",
    "cursor",
    "claude_desktop",
    "vscode",
    "windsurf",
    "zed",
    "antigravity",
    "hermes",
]

SCENARIOS = ["fresh", "existing", "uninstall"]

# ---------------------------------------------------------------------------
# SSoT fixture: skills y subagents canónicos (.cortex/)
# ---------------------------------------------------------------------------

SKILLS = {
    "cortex-sync": """\
---
name: cortex-sync
description: Cortex PRE-FLIGHT (Spec Creation Only). NO WRITE PERMISSIONS.
---

# Cortex Sync - Gobernanza de Analisis

Anchor de inicio. Llama a `cortex_sync_ticket` antes que nada.
Acentos de prueba: áéíóú. Emoji: ⚠️.
""",
    "cortex-SDDwork": """\
---
name: cortex-SDDwork
description: Implementación orquestada de la spec persistida.
---

# Cortex SDDwork

Middle pluggable. Fast Track para edits directos; Deep Track con
delegación a los subagents canónicos (explorer / designer / implementer).
""",
    "cortex-documenter": """\
---
name: cortex-documenter
description: Anchor de cierre con criterio editorial.
---

# Cortex Documenter

Cierra la Session: decide doc types, escribe nota a mano, llama
`cortex_self_review_note`, persiste vía `cortex_write_doc` y cierra con
`cortex_close_session`.
""",
}

SUBAGENTS = {
    "cortex-code-designer": """\
---
name: cortex-code-designer
description: Produce design doc antes de implementar.
tools: read_file, cortex_context, cortex_create_spec
---

# Cortex Code Designer

Diseña antes de tocar código. Salida: design note revisable.
""",
    "cortex-code-explorer": """\
---
name: cortex-code-explorer
description: Análisis read-only de arquitectura.
tools: read_file, execute_command, cortex_search, cortex_ping
---

# Cortex Code Explorer

Explora el repositorio sin mutar estado. Emite checkpoint al terminar.
""",
    "cortex-code-implementer": """\
---
name: cortex-code-implementer
description: Implementa siguiendo el design doc.
tools: read_file, write_file, edit_file, execute_command, cortex_session_checkpoint
---

# Cortex Code Implementer

Deep Track. Implementa la spec con edits quirúrgicos.
""",
    "cortex-documenter": """\
---
name: cortex-documenter
description: DEPRECATED - usar /cortex-documenter skill.
tools: read_file, cortex_documenter_briefing, cortex_self_review_note, cortex_write_doc, cortex_close_session
---

# Cortex Documenter (subagent legacy)

Flujo antiguo de reconstrucción. Mantenido por compatibilidad.
""",
}

# Pre-sembrado del escenario existing/existing-derived (ajeno a Cortex).
PRESEED_PROJECT = {
    "CLAUDE.md": "# Mi proyecto\n\nNotas propias del humano.\n",
    "AGENTS.md": "# Agentes del proyecto\n\nConvenciones locales.\n",
    ".mcp.json": json.dumps(
        {"mcpServers": {"local-dev": {"command": "npx", "args": ["-y", "thing"]}}},
        indent=2,
    )
    + "\n",
    ".claude/settings.json": json.dumps(
        {"enabledMcpjsonServers": ["other"], "permissions": {"allow": ["Bash"]}},
        indent=2,
    )
    + "\n",
}

PRESEED_HOME = {
    ".cursor/mcp.json": json.dumps(
        {"mcpServers": {"other-server": {"command": "other"}}}, indent=2
    )
    + "\n",
    ".codex/config.toml": 'model = "gpt-5-codex"\n\n[mcp_servers.other]\ncommand = "other"\n',
    ".codeium/windsurf/mcp_config.json": json.dumps(
        {"mcpServers": {"existing": {"command": "x"}}}, indent=2
    )
    + "\n",
    ".config/opencode/opencode.json": json.dumps({"theme": "dark"}, indent=2) + "\n",
    ".config/hermes/config.json": json.dumps(
        {"model": "hermes-3", "temperature": 0.7}, indent=2
    )
    + "\n",
    ".gemini/settings.json": json.dumps({"theme": "dark"}, indent=2) + "\n",
    ".zed/agents.json": json.dumps({"existing": {"command": "z"}}, indent=2) + "\n",
    ".config/Claude/claude_desktop_config.json": json.dumps(
        {"mcpServers": {"global-server": {"command": "g"}}}, indent=2
    )
    + "\n",
}


class FrozenDateTime(datetime):  # noqa: D401 (espejo mínimo de datetime)
    """datetime.now() congelado para captura determinista."""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return FROZEN


def patch_clock() -> None:
    """Congela el reloj en TODOS los módulos que llaman datetime.now()."""
    import cortex.ide.base as base_mod
    import cortex.ide.adapters.antigravity as anti_mod
    import cortex.ide.adapters.windsurf as wind_mod

    base_mod.datetime = FrozenDateTime  # type: ignore[attr-defined]
    anti_mod.datetime = FrozenDateTime  # type: ignore[attr-defined]
    wind_mod.datetime = FrozenDateTime  # type: ignore[attr-defined]


def build_fixture_project(root: Path) -> None:
    (root / "vault").mkdir(parents=True, exist_ok=True)
    (root / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\nretrieval:\n  top_k: 5\n",
        encoding="utf-8",
    )
    (root / "vault" / "nota-a.md").write_text(
        "# Nota A\n\nContenido determinista del fixture.\n", encoding="utf-8"
    )
    for name, content in SKILLS.items():
        p = root / ".cortex" / "skills" / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    for name, content in SUBAGENTS.items():
        p = root / ".cortex" / "subagents" / f"{name}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def preseed(root: Path, home: Path) -> None:
    for rel, content in PRESEED_PROJECT.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    for rel, content in PRESEED_HOME.items():
        p = home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def normalize(text: str, root: Path, home: Path) -> str:
    return text.replace(str(root), "{{ROOT}}").replace(str(home), "{{HOME}}")


def snapshot(base: Path, scope: str, root: Path, home: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames.sort()
        for f in sorted(filenames):
            full = Path(dirpath) / f
            rel = full.relative_to(base).as_posix()
            content = full.read_text(encoding="utf-8")
            files[f"{scope}:{rel}"] = normalize(content, root, home)
    return files


def run_scenario(ide_name: str, scenario: str, workbase: Path) -> dict:
    from cortex.ide.registry import get_adapter

    project = workbase / "project"
    home = workbase / "home"
    home.mkdir(parents=True, exist_ok=True)
    build_fixture_project(project)

    if scenario in ("existing", "uninstall"):
        preseed(project, home)

    # Redirección de home (expanduser lee HOME en POSIX) y de CODEX_HOME.
    old_home = os.environ.get("HOME")
    old_codex_home = os.environ.get("CODEX_HOME")
    os.environ["HOME"] = str(home)
    os.environ["CODEX_HOME"] = str(home / ".codex")

    try:
        adapter = get_adapter(ide_name)
        reports: list[str] = []

        if scenario == "uninstall":
            adapter.inject_profiles(project, {})
            adapter.inject_mcp(project)
            removed = adapter.uninstall(project)
            reports.extend(removed)
        else:
            from cortex.ide.prompts import build_all_prompts

            prompts = build_all_prompts(project)
            reports.extend(adapter.inject_profiles(project, prompts))
            reports.extend(adapter.inject_mcp(project))

        files: dict[str, str] = {}
        files.update(snapshot(project, "project", project, home))
        files.update(snapshot(home, "home", project, home))
        normalized_reports = sorted(normalize(r, project, home) for r in reports)

        return {
            "ide": ide_name,
            "scenario": scenario,
            "reports": normalized_reports,
            "files": files,
        }
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        if old_codex_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = old_codex_home


def generate_all(basedir: Path) -> None:
    import tempfile

    patch_clock()
    if basedir.exists():
        shutil.rmtree(basedir)
    basedir.mkdir(parents=True)

    for ide_name in IDES:
        for scenario in SCENARIOS:
            with tempfile.TemporaryDirectory(prefix="p8-ide-") as tmp:
                manifest = run_scenario(ide_name, scenario, Path(tmp))
            out_dir = basedir / f"{ide_name}__{scenario}"
            out_dir.mkdir(parents=True)
            payload = json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True)
            (out_dir / "manifest.json").write_text(payload, encoding="utf-8")


def verify_all() -> int:
    import tempfile

    patch_clock()
    failures: list[str] = []
    for ide_name in IDES:
        for scenario in SCENARIOS:
            golden = OUT / f"{ide_name}__{scenario}" / "manifest.json"
            with tempfile.TemporaryDirectory(prefix="p8-ide-verify-") as tmp:
                manifest = run_scenario(ide_name, scenario, Path(tmp))
            regenerated = json.dumps(
                manifest, ensure_ascii=True, indent=2, sort_keys=True
            )
            committed = golden.read_text(encoding="utf-8")
            if regenerated != committed:
                failures.append(f"{ide_name}__{scenario}")
    if failures:
        print("VERIFY FAIL:", ", ".join(failures))
        return 1
    print(f"VERIFY OK: {len(IDES) * len(SCENARIOS)} manifiestos reproducibles")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="regenera en temp y compara contra los goldens commiteados",
    )
    args = parser.parse_args()
    if args.verify:
        return verify_all()
    generate_all(OUT)
    total = len(IDES) * len(SCENARIOS)
    print(f"OK: {total} manifiestos en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
