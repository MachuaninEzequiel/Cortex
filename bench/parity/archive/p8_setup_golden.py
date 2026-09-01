#!/usr/bin/env python3
"""Oráculo P8c: renderers de setup/templates byte-a-byte.

Genera mini-proyectos sintéticos (marcadores por lenguaje), corre el
ProjectDetector REAL y captura la salida de cada renderer de
cortex/setup/templates.py en dos modos de layout (legacy y nuevo).

Salida:
    bench/parity/golden_setup/setup/inputs.json
    bench/parity/golden_setup/setup/<case>/<renderer>.out

El test Rust (cortex-setup/tests/setup_parity.rs) reconstruye el mismo
mini-proyecto, detecta y renderiza, y compara byte-a-byte.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

OUT = REPO / "bench/parity/golden_setup/setup"

RENDERERS = [
    "config_yaml",
    "enterprise_vault_readme",
    "ci_pull_request",
    "ci_enterprise_governance",
    "ci_feature",
    "cd_deploy",
    "architecture_md",
    "decisions_md",
    "context_md",
    "runbooks_md",
    "enterprise_runbook_md",
    "git_vault_policy_md",
    "workspace_yaml",
]


def make_project(base: Path, name: str, markers: dict[str, str], new_layout: bool) -> Path:
    root = base / name
    root.mkdir(parents=True)
    for rel, content in markers.items():
        p = root / rel
        if rel.endswith("/"):
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    if new_layout:
        ws = root / ".cortex" / "workspace.yaml"
        ws.parent.mkdir(parents=True, exist_ok=True)
        ws.write_text("layout_version: 2\n", encoding="utf-8")
    return root


def main() -> int:
    import cortex.setup.templates as T
    from cortex.setup.detector import ProjectDetector

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    CASES = [
        ("python_legacy", {
            "pyproject.toml": '[project]\nname = "demo-api"\n',
            "tests/": "",
        }, False),
        ("python_new_layout", {
            "pyproject.toml": '[project]\nname = "demo-api"\n',
            "tests/": "",
        }, True),
        ("node_npm", {
            "package.json": json.dumps({
                "name": "web-app",
                "scripts": {
                    "test": "vitest run",
                    "lint": "eslint .",
                    "build": "vite build",
                },
                "dependencies": {"react": "^18"},
                "devDependencies": {"vite": "^5", "typescript": "^5"},
            }, indent=1),
        }, False),
        ("go_mod", {"go.mod": "module ejemplo/api\n\ngo 1.22\n"}, False),
        ("rust_cargo", {"Cargo.toml": "[package]\nname = \"ejemplo-core\"\n"}, False),
        ("java_maven", {"pom.xml": "<project/>"}, False),
        ("ruby_gemfile", {"Gemfile": "gem 'rails'\ngem 'rspec'\n", "spec/": ""}, False),
    ]

    inputs = []
    tmp = REPO / ".tmp_p8_fixture"
    if tmp.exists():
        shutil.rmtree(tmp)

    # Control explícito del entorno que lee _detect_env.
    old_openai = os.environ.pop("OPENAI_API_KEY", None)

    try:
        for name, markers, new_layout in CASES:
            root = make_project(tmp, name.replace("_new_layout", ""), markers, False)
            # El caso *_new_layout agrega workspace.yaml v2.
            if new_layout:
                ws = root / ".cortex" / "workspace.yaml"
                ws.parent.mkdir(parents=True, exist_ok=True)
                ws.write_text("layout_version: 2\n", encoding="utf-8")

            ctx = ProjectDetector(root).detect()

            def call(rname):
                layout = ctx.layout
                if rname == "config_yaml":
                    return T.render_config_yaml(ctx, layout=layout)
                if rname == "enterprise_vault_readme":
                    return T.render_enterprise_vault_readme(ctx)
                if rname == "ci_pull_request":
                    return T.render_ci_pull_request(ctx, layout=layout)
                if rname == "ci_enterprise_governance":
                    return T.render_ci_enterprise_governance(ctx)
                if rname == "ci_feature":
                    return T.render_ci_feature(ctx, layout=layout)
                if rname == "cd_deploy":
                    return T.render_cd_deploy(ctx, layout=layout)
                if rname == "architecture_md":
                    return T.render_architecture_md(ctx)
                if rname == "decisions_md":
                    return T.render_decisions_md(ctx)
                if rname == "context_md":
                    return T.render_context_md(ctx)
                if rname == "runbooks_md":
                    return T.render_runbooks_md(ctx)
                if rname == "enterprise_runbook_md":
                    return T.render_enterprise_runbook_md(ctx)
                if rname == "git_vault_policy_md":
                    return T.render_git_vault_policy_md(ctx)
                if rname == "workspace_yaml":
                    return T.render_workspace_yaml()
                raise KeyError(rname)

            case_dir = OUT / name
            case_dir.mkdir(parents=True)
            for rname in RENDERERS:
                out_text = call(rname)
                (case_dir / f"{rname}.out").write_text(out_text, encoding="utf-8")

            inputs.append({
                "case": name,
                "root_name": root.name,
                "markers": list(markers.keys()),
                "new_layout": new_layout,
                "expected": {r: f"{r}.out" for r in RENDERERS},
            })
        shutil.rmtree(tmp)

        # org.yaml: matriz de perfiles × flags.
        org_cases = []
        for profile in ("small-company", "multi-project-team",
                        "regulated-organization", "custom"):
            for gh in (True, False):
                for br in (True, False):
                    org_cases.append({
                        "profile": profile,
                        "github_actions_enabled": gh,
                        "branch_isolation_enabled": br,
                    })
        org_dir = OUT / "_org"
        org_dir.mkdir()
        for i, oc in enumerate(org_cases):

            class Ctx:
                pass

            c = Ctx()
            c.stack = type("Stack", (), {})()
            c.stack.project_name = "AppFútbol Org"
            c.root = Path("/tmp/appfutbol-org")
            c.ci = type("CI", (), {})()
            c.ci.has_github_actions = oc["github_actions_enabled"]
            text = T.render_org_yaml(c, profile=oc["profile"])  # branch isolation solo regulated
            (org_dir / f"org_{i}.yaml").write_text(text, encoding="utf-8")
        (OUT / "org_inputs.json").write_text(
            json.dumps({
                "project_name": "AppFútbol Org",
                "cases": [
                    {
                        **oc,
                        "file": f"org_{i}.yaml",
                    }
                    for i, oc in enumerate(org_cases)
                ],
            }, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    finally:
        if old_openai is not None:
            os.environ["OPENAI_API_KEY"] = old_openai

    (OUT / "inputs.json").write_text(
        json.dumps({"renderers": RENDERERS, "cases": inputs}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{len(inputs)} casos setup + {len(org_cases)} org capturados en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
