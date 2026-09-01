#!/usr/bin/env python3
"""Genera src/setup_templates_gen.rs del crate cortex-setup a partir de los
f-strings REALES de cortex/setup/templates.py (Obra 07 P8c).

Cada f-string se recorre por AST: los tramos Constant salen verbatim (con
llaves ya decodificadas) y cada FormattedValue se reemplaza por el
sentinela \\u{e000}N\\u{e001}. El lado Rust computa los valores en el MISMO
orden y sustituye. Esto elimina errores de transcripción manual: las
plantillas embebidas son derivadas del código fuente Python vigente.

Uso: .venv/bin/python bench/parity/p8_gen_setup_templates.py > rust/crates/cortex-setup/src/setup_templates_gen.rs
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "cortex/setup/templates.py"

SENTINEL_OPEN = "│"
SENTINEL_CLOSE = "│"

MODULE_CONSTS = ["DEVSECDOCSOPS_SCRIPT"]

FUNCTIONS = [
    "render_config_yaml",
    "render_enterprise_vault_readme",
    "render_ci_pull_request",
    "render_ci_enterprise_governance",
    "render_ci_feature",
    "render_cd_deploy",
    "render_architecture_md",
    "render_decisions_md",
    "render_context_md",
    "render_runbooks_md",
    "render_enterprise_runbook_md",
    "render_git_vault_policy_md",
]


def template_of(fn_node: ast.FunctionDef) -> tuple[str, int]:
    """Devuelve el template con sentinelas y la cantidad de interpolaciones."""
    counter = 0

    class V(ast.NodeVisitor):
        def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
            raise SkipVisit(node)

    # Recorremos todos los JoinedStr dentro de la función (cada render tiene
    # exactamente uno grande; si hubiera más, se concatenan en orden).
    parts: list[str] = []

    class Collector(ast.NodeVisitor):
        def __init__(self):
            self.results: list[list] = []
            self.current: list | None = None

        def visit(self, node):
            if isinstance(node, ast.JoinedStr):
                saved = self.current
                self.current = []
                for v in node.values:
                    if isinstance(v, ast.Constant):
                        self.current.append(("lit", v.value))
                    elif isinstance(v, ast.FormattedValue):
                        nonlocal counter  # noqa: F824
                        expr_src = ast.unparse(v.value)
                        self.current.append(("var", counter, expr_src))
                        counter += 1
                self.results.append(self.current)
                self.current = saved
                return
            super().visit(node)

    c = Collector()
    c.visit(fn_node)
    if len(c.results) > 1:
        raise AssertionError(f"{fn_node.name}: m\u00e1s de un f-string")
    if not c.results:
        # String plano (no f-string): tomar el primer Constant del return.
        plain = None
        for n in ast.walk(fn_node):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.strip():
                plain = n.value
                break
        c.results = [[("lit", plain or "")]]
    for kind, *rest in c.results[0]:
        if kind == "lit":
            parts.append(rest[0])
        else:
            parts.append(chr(0xE000) + str(rest[0]) + chr(0xE001))
    return "".join(parts), counter


def rust_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def main() -> int:
    tree = ast.parse(SRC.read_text(encoding="utf-8"))

    out: list[str] = [
        "// GENERADO POR bench/parity/p8_gen_setup_templates.py — NO EDITAR A MANO.",
        "// Derivado del AST de cortex/setup/templates.py (f-strings reales).",
        "// Sentinela de interpolación: U+E000 <n> U+E001.",
        "",
    ]
    for cname in MODULE_CONSTS:
        assign = next(
            n for n in tree.body
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == cname for t in n.targets)
        )
        value = assign.value.value  # Constant r-string
        out.append(f"/// Constante derivada de `{cname}` (texto estático).")
        out.append(f"pub const DEVSECDOCSOPS_SCRIPT: &str = {rust_str(value)};")
        out.append("")
    total_vars = 0
    for name in FUNCTIONS:
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        tpl, nvars = template_of(fn)
        total_vars += nvars
        const_name = "".join(w.upper() if i == 0 else w.capitalize() for i, w in enumerate(name.split("_")))
        out.append(f"/// Plantilla derivada de `{name}` ({nvars} interpolaciones).")
        out.append(f"pub const {const_name}_TPL: &str = {rust_str(tpl)};")
        out.append("")
    out.append(f"// Total interpolaciones: {total_vars}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
