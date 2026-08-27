#!/usr/bin/env python3
"""Oráculo P8e: installer/uninstaller de session hooks byte-a-byte.

Corre los 4 adapters de cortex/session/hooks/ sobre fixtures target_dir
deterministas y captura resultados + árboles de archivos por paso:

    <adapter>__install_fresh           target vacío (cursor: con .git/)
    <adapter>__install_idempotent      segundo install (mensaje already)
    <adapter>__install_existing        contenido previo del usuario
    <adapter>__uninstall_installed     install → uninstall (árbol final)
    <adapter>__uninstall_missing       sin archivo → mensaje "does not exist"
    <adapter>__uninstall_nomarker      archivo sin bloque Cortex
    <adapter>__status_*                missing / installed / uninstalled

Extras por adapter: cursor__install_error_nogit (ValueError espejado),
cursor__install_existing_noshebang (rama prepend shebang).

Salida: bench/parity/golden_setup/hooks/<paso>/manifest.json con
{"ide", "step", "result", "files"} — result normalizado con {{TARGET}}
(los mensajes embeben rutas absolutas); los pasos son deterministas
(sin globs), así que el orden del arreglo ES parte del contrato.

El test Rust (cortex-setup/tests/hooks_parity.rs) reconstruye cada fixture
y compara estructuralmente. Modo verify:

    .venv/bin/python bench/parity/p8_hooks_golden.py --verify
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

OUT = REPO / "bench/parity/golden_setup/hooks"

from cortex.session.hooks.adapters.claude_code import ClaudeCodeHookAdapter
from cortex.session.hooks.adapters.cursor import CursorGitHookAdapter
from cortex.session.hooks.adapters.opencode import OpencodeHookAdapter
from cortex.session.hooks.adapters.pi import PiHookAdapter

ADAPTERS = {
    "claude-code": ClaudeCodeHookAdapter(),
    "cursor": CursorGitHookAdapter(),
    "opencode": OpencodeHookAdapter(),
    "pi": PiHookAdapter(),
}

PRESEED_EXISTING = {
    # claude_code: settings ajeno con hooks propios del usuario.
    "claude-code": (
        ".claude/settings.json",
        json.dumps(
            {
                "permissions": {"allow": ["Bash"]},
                "hooks": {
                    "PostToolUse": [
                        {"matcher": "WebSearch", "hooks": [{"type": "command", "command": "echo usuario"}]}
                    ]
                },
            },
            indent=2,
        )
        + "\n",
    ),
    # cursor: post-commit del usuario CON shebang.
    "cursor": (
        ".git/hooks/post-commit",
        "#!/bin/sh\n# Mi propio hook.\necho 'post commit propio'\n",
    ),
    # opencode: markdown del usuario.
    "opencode": (
        ".opencode/hooks.md",
        "# Mis hooks\n\nContenido propio del usuario.\n",
    ),
    # pi: justfile del usuario.
    "pi": ("justfile", "saludar:\n    echo hola\n"),
}

PRESEED_NOMARKER = {
    "claude-code": (".claude/settings.json", json.dumps({"theme": "dark"}, indent=2) + "\n"),
    "cursor": (".git/hooks/post-commit", "#!/bin/sh\necho solo usuario\n"),
    "opencode": (".opencode/hooks.md", "# Solo usuario\n"),
    "pi": ("justfile", "otra:\n    echo otra\n"),
}

CURSOR_NOSHEBANG_PRESEED = (".git/hooks/post-commit", "echo sin shebang\n")


def seed(target: Path, rel: str, content: str) -> None:
    p = target / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def normalize(text: str, target: Path) -> str:
    return text.replace(str(target), "{{TARGET}}")


def snapshot(target: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames.sort()
        for f in sorted(filenames):
            full = Path(dirpath) / f
            rel = full.relative_to(target).as_posix()
            files[rel] = normalize(full.read_text(encoding="utf-8"), target)
    return files


def result_payload(result, target: Path) -> dict:
    d = asdict(result)
    d["modified_paths"] = [normalize(str(p), target) for p in d.get("modified_paths", [])]
    d["removed_paths"] = [normalize(str(p), target) for p in d.get("removed_paths", [])]
    d["message"] = normalize(d["message"], target)
    return d


def status_payload(status, target: Path) -> dict:
    d = asdict(status)
    d["detail"] = normalize(d["detail"], target)
    return d


def run_step(adapter, step: str, target: Path) -> dict:
    """Ejecuta un paso y devuelve {step, kind, payload, files}."""
    if step.startswith("install"):
        payload = result_payload(adapter.install(target), target)
        kind = "result"
    elif step.startswith("uninstall"):
        payload = result_payload(adapter.uninstall(target), target)
        kind = "result"
    else:  # status_*
        payload = status_payload(adapter.status(target), target)
        kind = "status"
    return {"step": step, "kind": kind, "payload": payload, "files": snapshot(target)}


def capture_all(basedir: Path) -> None:
    if basedir.exists():
        shutil.rmtree(basedir)
    basedir.mkdir(parents=True)

    for ide, adapter in ADAPTERS.items():
        with_git = ide == "cursor"
        preseed_rel, preseed_content = PRESEED_EXISTING[ide]
        nomarker_rel, nomarker_content = PRESEED_NOMARKER[ide]

        def run_case(case: str) -> dict:
            def new_target() -> Path:
                t = basedir.parent / f"_tmp_{ide}_{case}"
                if t.exists():
                    shutil.rmtree(t)
                t.mkdir(parents=True)
                target = t / "target"
                target.mkdir()
                # El caso de error exige que NO exista .git (ValueError).
                if with_git and case != "install_error_nogit":
                    (target / ".git").mkdir()
                return target

            if case == "install_fresh":
                target = new_target()
                return run_step(adapter, "install_fresh", target)

            if case == "install_idempotent":
                target = new_target()
                adapter.install(target)
                return run_step(adapter, "install_idempotent", target)

            if case == "install_existing":
                target = new_target()
                seed(target, preseed_rel, preseed_content)
                return run_step(adapter, "install_existing", target)

            if case == "install_existing_noshebang":
                target = new_target()
                seed(target, CURSOR_NOSHEBANG_PRESEED[0], CURSOR_NOSHEBANG_PRESEED[1])
                return run_step(adapter, "install_existing_noshebang", target)

            if case == "install_error_nogit":
                target = new_target()
                try:
                    res = adapter.install(target)
                    payload = result_payload(res, target)
                except ValueError as exc:
                    payload = {"error": normalize(str(exc), target)}
                return {
                    "step": "install_error_nogit",
                    "kind": "error-or-result",
                    "payload": payload,
                    "files": snapshot(target),
                }

            if case == "uninstall_installed":
                target = new_target()
                adapter.install(target)
                return run_step(adapter, "uninstall_installed", target)

            if case == "uninstall_missing":
                target = new_target()
                return run_step(adapter, "uninstall_missing", target)

            if case == "uninstall_nomarker":
                target = new_target()
                seed(target, nomarker_rel, nomarker_content)
                return run_step(adapter, "uninstall_nomarker", target)

            if case == "status_missing":
                target = new_target()
                return run_step(adapter, "status_missing", target)

            if case == "status_installed":
                target = new_target()
                adapter.install(target)
                return run_step(adapter, "status_installed", target)

            if case == "status_uninstalled":
                target = new_target()
                adapter.install(target)
                adapter.uninstall(target)
                return run_step(adapter, "status_uninstalled", target)

            raise AssertionError(f"caso desconocido: {case}")

        cases = ["install_fresh", "install_idempotent", "install_existing"]
        if ide == "cursor":
            cases += ["install_existing_noshebang", "install_error_nogit"]
        cases += [
            "uninstall_installed",
            "uninstall_missing",
            "uninstall_nomarker",
            "status_missing",
            "status_installed",
            "status_uninstalled",
        ]

        for case in cases:
            manifest = run_case(case)
            manifest["ide"] = ide
            out_dir = basedir / f"{ide}__{case}"
            out_dir.mkdir(parents=True)
            payload = json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True)
            (out_dir / "manifest.json").write_text(payload, encoding="utf-8")
            # limpieza del tmp del caso
            tmp_dir = basedir.parent / f"_tmp_{ide}_{case}"
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)


def verify_all() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="p8-hooks-verify-") as tmp:
        tmp_out = Path(tmp) / "out"
        capture_all(tmp_out)
        for manifest_path in sorted(tmp_out.glob("*/manifest.json")):
            rel = manifest_path.relative_to(tmp_out)
            committed = OUT / rel
            if not committed.exists():
                failures.append(f"{rel}: falta golden commiteado")
                continue
            if manifest_path.read_text(encoding="utf-8") != committed.read_text(
                encoding="utf-8"
            ):
                failures.append(str(rel))
    if failures:
        print("VERIFY FAIL:", ", ".join(failures))
        return 1
    print("VERIFY OK: hooks reproducible")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify_all()
    capture_all(OUT)
    print(f"OK: goldens en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
