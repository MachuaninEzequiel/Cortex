#!/usr/bin/env python3
"""Gate de paridad P12B-7 (tutor). Genera golden_tutor.txt con:

1. TOPICS: una línea JSON de metadatos por topic (orden canónico).
2. HINTS: hint resultante para 3 fixtures (L0 vacío, L1 solo config,
   L7 completo) — icon/title/body/command.

El contenido renderizado de los topics ya vive byte-exacto en
rust/crates/cortex-tutor/content/*.txt (captura rich export_text).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from cortex.tutor.hint import HintEngine, ProjectState
from cortex.tutor.topics import get_all_topics


def seg_topics(lines):
    for t in get_all_topics():
        lines.append(json.dumps({
            "title": t.title,
            "icon": t.icon,
            "slug": t.slug,
            "one_liner": t.one_liner,
            "guide_path": t.guide_path,
        }, ensure_ascii=True) + "\n")


def make_fixture(base: Path, tag: str, kind: str) -> Path:
    # FUERA del repo de desarrollo: discover() camina hacia arriba y
    # heredaría el .cortex/config del propio Cortex si el fixture vive
    # dentro del árbol.
    import tempfile

    del base
    root = Path(tempfile.mkdtemp(prefix=f"tutor_{tag}_"))

    if kind == "l0":
        return root  # vacío
    (root / "config.yaml").write_text("semantic:\n  vault_path: vault\n", encoding="utf-8")
    if kind == "l1":
        return root
    # l7: todo configurado
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
    (org / "org.yaml").write_text(
        "schema_version: 1\n"
        "organization:\n"
        "  name: Acme Org\n"
        "memory:\n"
        "  enterprise_semantic_enabled: true\n"
        "promotion:\n"
        "  enabled: true\n",
        encoding="utf-8",
    )
    (root / "vault-enterprise").mkdir()
    return root


def seg_hints(lines, workdir):
    for tag, kind in [("l0_empty", "l0"), ("l1_config_only", "l1"), ("l7_full", "l7")]:
        root = make_fixture(workdir, tag, kind)
        state = ProjectState.detect(root)
        engine = HintEngine()
        hint = engine.get_hint(state)
        lines.append(json.dumps({
            "fixture": tag,
            "icon": hint.icon,
            "title": hint.title,
            "body": hint.body,
            "command": hint.command,
        }, ensure_ascii=True) + "\n")
    shutil.rmtree(workdir, ignore_errors=True)


def build(out_dir: Path) -> int:
    workdir = out_dir / ".work"
    shutil.rmtree(workdir, ignore_errors=True)
    workdir.mkdir(parents=True)
    lines = ["### TOPICS\n"]
    seg_topics(lines)
    lines.append("### HINTS\n")
    seg_hints(lines, workdir)
    (out_dir / "golden_tutor.txt").write_text("".join(lines), encoding="utf-8")
    print(f"[OK] golden generado: {out_dir / 'golden_tutor.txt'}")
    return 0


def verify(out_dir: Path) -> int:
    golden = out_dir / "golden_tutor.txt"
    if not golden.exists():
        print("[FAIL] no existe el golden")
        return 1
    expected = golden.read_text(encoding="utf-8")
    build(out_dir)
    if (out_dir / "golden_tutor.txt").read_text(encoding="utf-8") == expected:
        print("[PASS] golden_tutor.txt determinista")
        return 0
    print("[FAIL] golden difiere entre build y verify")
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
