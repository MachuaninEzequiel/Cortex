#!/usr/bin/env python3
"""Gate de paridad P12B-4 (doctor).

Genera `golden_doctor.txt`: un bloque por escenario con una línea JSON por
check (`{"name","ok","severity","detail"}` compacto) + línea final
`SUMMARY has_failures=… has_warnings=…`.

Los checks con backend Python sin porteño se NORMALIZAN vía STUB_TABLE a los
valores contractuales que emite el crate nativo (patrón P6/P9).

Uso:
    python bench/parity/doctor_golden_p12b.py build --out DIR
    python bench/parity/doctor_golden_p12b.py verify --out DIR
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from cortex.doctor import run_doctor

# Checks cuyo detalle depende de backends no porteados: el contrato nativo es
# (ok=False, severity=<tabla>, detail=f"backend no nativo aún ({module})").
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


def normalize_checks(report) -> str:
    lines = []
    for c in report.checks:
        if c.name in STUB_TABLE:
            severity, module = STUB_TABLE[c.name]
            payload = {
                "name": c.name,
                "ok": False,
                "severity": severity,
                "detail": f"backend no nativo aún ({module})",
            }
        else:
            payload = {"name": c.name, "ok": c.ok, "severity": c.severity, "detail": c.detail}
        lines.append(json.dumps(payload, ensure_ascii=True))
    lines.append(
        f"SUMMARY has_failures={report.has_failures} has_warnings={report.has_warnings}"
    )
    return "\n".join(lines) + "\n"


def make_legacy(base: Path, tag: str, *, with_org: bool, with_sessions: bool) -> Path:
    root = base / tag / "acme-api"
    (root / "vault" / "specs").mkdir(parents=True)
    (root / "config.yaml").write_text("semantic:\n  vault_path: vault\n", encoding="utf-8")
    (root / "vault" / "specs" / "spec.md").write_text(
        "---\ntitle: Spec\ntags: [spec]\n---\n\n# Spec\n\nHello\n", encoding="utf-8"
    )
    if with_org:
        from cortex.enterprise.config import (
            build_enterprise_org_config,
            write_enterprise_config,
        )

        cfg = build_enterprise_org_config(project_name="Acme Org")
        write_enterprise_config(root, cfg)
        (root / "vault-enterprise").mkdir()
    if with_sessions:
        (root / ".cortex" / "sessions").mkdir(parents=True)
    return root


def make_new_layout(base: Path, tag: str) -> Path:
    root = base / tag / "acme-api"
    (root / ".cortex" / "vault" / "specs").mkdir(parents=True)
    (root / ".cortex" / "memory" / "chroma").mkdir(parents=True)
    (root / "config.yaml").write_text("semantic:\n  vault_path: vault\n", encoding="utf-8")
    (root / ".cortex/workspace.yaml").write_text(
        "layout_version: 2\nprojects: []\n", encoding="utf-8"
    )
    (root / ".cortex/vault/specs/spec.md").write_text(
        "---\ntitle: Spec\ntags: [spec]\n---\n\n# Spec\n\nHello\n", encoding="utf-8"
    )
    return root


def build(out_dir: Path) -> int:
    workdir = out_dir / ".work"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)

    sections: list[str] = []

    # 1. legacy project scope.
    root = make_legacy(workdir, "legacy", with_org=False, with_sessions=False)
    sections.append(normalize_checks(run_doctor(root)))

    # 2. legacy + org.yaml → scope ALL.
    root = make_legacy(workdir, "legacy_all", with_org=True, with_sessions=False)
    sections.append(normalize_checks(run_doctor(root, scope="all")))

    # 3. enterprise requerido SIN org.yaml (early-return del bloque).
    root = make_legacy(workdir, "ent_missing", with_org=False, with_sessions=False)
    report = run_doctor(root, scope="enterprise")
    tail = [c for c in report.checks if c.name == "enterprise_config"]
    sections.append(normalize_checks(type(report)(project_root=report.project_root, checks=tail)))

    # 4. new layout v2 con memory store presente.
    root = make_new_layout(workdir, "newlayout")
    sections.append(normalize_checks(run_doctor(root)))

    # 5. legacy con .cortex/sessions presente (stub profundos activos).
    root = make_legacy(workdir, "with_sessions", with_org=False, with_sessions=True)
    sections.append(normalize_checks(run_doctor(root)))

    # 6. autopilot.yaml con typo de modo → autopilot_mode_typo warn.
    root = make_legacy(workdir, "ap_typo", with_org=False, with_sessions=False)
    # Legacy ⇒ workspace_root == root.
    (root / "autopilot.yaml").write_text("mode: auto\n", encoding="utf-8")
    sections.append(normalize_checks(run_doctor(root)))

    body = "".join(
        f"### {name}\n{section}"
        for name, section in zip(
            [
                "legacy_project",
                "legacy_all",
                "enterprise_missing_org",
                "new_layout",
                "legacy_with_sessions",
                "autopilot_typo",
            ],
            sections,
        )
    )
    golden = out_dir / "golden_doctor.txt"
    golden.write_text(body, encoding="utf-8")
    shutil.rmtree(workdir, ignore_errors=True)
    print(f"[OK] golden generado: {golden}")
    return 0


def verify(out_dir: Path) -> int:
    golden = out_dir / "golden_doctor.txt"
    if not golden.exists():
        print("[FAIL] no existe el golden; corré build primero")
        return 1
    expected = golden.read_text(encoding="utf-8")
    rc = build(out_dir)
    actual = (out_dir / "golden_doctor.txt").read_text(encoding="utf-8")
    if actual == expected:
        print("[PASS] golden_doctor.txt determinista")
        return 0
    print("[FAIL] golden difiere entre build y verify")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify"])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    return build(out_dir) if ns.cmd == "build" else verify(out_dir)


if __name__ == "__main__":
    sys.exit(main())
