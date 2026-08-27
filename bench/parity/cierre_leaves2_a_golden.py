#!/usr/bin/env python3
"""Golden MITAD A — BAJA DEFINITIVA RUTA 2 (autopilot doctor + Fase 04).

Compara el binario nativo `cortex-cli` contra el CLI Python REAL
(`python -m cortex.cli.main`) sobre fixtures deterministas, con las
normalizaciones PACTADAS del package (ver PROMPT-BAJA-DEFINITIVA-RUTA2.md):

- {{ROOT}}   : tmp del fixture
- {{TS}}     : timestamps ISO (drift de reloj entre corridas)
- {{ELAPSED}}/{{RUN}}/{{MEMID}}: no producidas por esta familia (reservadas)
- {{SHA}}    : SHAs git de 40 hex (fixtures gitless ⇒ el placeholder
  `0000...0` del SessionRecord se normaliza igual en ambos lados)
- scores a 4 decimales (no producidos acá; reservado)

Casos byte-parity:
- `autopilot doctor` texto + `--json` sobre fixture COMPLETA (workspace +
  sesión abierta + hook claude-code ⇒ 6 checks OK).
- `autopilot doctor` texto + `--json` sobre fixture DEGRADADA (sin sesiones
  ni hooks ⇒ check hooks FAIL, `ok: False`; rc 0 como el oráculo — el
  doctor de Fase 04 NO sale 1 ante checks fallidos y el check
  `sessions_dir` se auto-repara con `mkdir`, igual que el oráculo).
- `autopilot doctor` texto con `--project-root` EXPLÍCITO desde otro cwd.

Casos de equivalencia (SIN paridad byte-a-byte, pactado en el brief):
- `autopilot install` / `autopilot uninstall` — el oráculo los ELIMINÓ en
  Fase 04 (`cortex/autopilot/cli.py`); el nativo los rechaza con la misma
  semántica (comando desconocido, rc=2, core msg `No such command ...`)
  y NUNCA ejecuta Python. Se comparan rc y mensaje núcleo en vivo.

Modos:
  build  → congela la salida NORMALIZADA del CLI Python en
           goldens_leaves2_a.txt (+ informe de equivalencias en
           goldens_leaves2_a_eq.txt)
  verify → corre ambos lados y compara normalizados (byte-a-byte
           post-normalización) + re-verifica la equivalencia en vivo
  bench  → cold start N=20 de `autopilot doctor` (binario release)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("PYTHONHASHSEED", "0")

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv" / "bin" / "python")
RS_DEBUG = REPO / "rust" / "target" / "debug" / "cortex-cli"
RS_RELEASE = REPO / "rust" / "target" / "release" / "cortex-cli"

ROOT_MARK = "{{ROOT}}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _cortex_base(root: Path) -> None:
    cortex = root / ".cortex"
    cortex.mkdir(parents=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    (cortex / "config.yaml").write_text(
        "semantic:\n  vault_path: vault\n",
        encoding="utf-8",
    )


def construir_fixture_completa(root: Path) -> None:
    """Workspace nuevo + sesión abierta (canónica, vía SessionService) +
    hook claude-code instalado ⇒ los 6 checks del doctor en OK."""
    _cortex_base(root)
    claude = root / ".claude"
    claude.mkdir(parents=True)
    (claude / "settings.json").write_text(
        '{"hooks": {"PostToolUse": [{"type": "command", "command":'
        ' "cortex session checkpoint --source ide-hook",'
        ' "_cortex_managed": true}]}}',
        encoding="utf-8",
    )
    from cortex.session.service import SessionService
    from cortex.session.storage import SessionStorage
    from cortex.workspace import WorkspaceLayout

    layout = WorkspaceLayout.discover(root)
    svc = SessionService(SessionStorage(layout.sessions_dir), repo_root=layout.repo_root)
    spec = root / ".cortex" / "vault" / "specs" / "2026-08-25_demo.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("---\ntitle: Demo\ndoc_type: spec\n---\ncuerpo\n", encoding="utf-8")
    svc.open(spec_id="2026-08-25_demo", spec_path=spec, spec_summary="demo")


def construir_fixture_degradada(root: Path) -> None:
    """Workspace nuevo SIN sesiones y SIN hooks ⇒ check hooks FAIL
    (`ok: False`); `sessions_dir` se auto-repara con mkdir (oráculo)."""
    _cortex_base(root)


# ---------------------------------------------------------------------------
# Ejecución + normalización (mismas pactadas que cierre_leaves_a_golden.py)
# ---------------------------------------------------------------------------

def _run(binary: list[str], args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        binary + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env={**os.environ, "OMP_NUM_THREADS": "2"},
    )
    return proc.returncode, proc.stdout, proc.stderr


def normalize(text: str, root: Path) -> str:
    text = text.replace(str(root), ROOT_MARK)
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?",
        "{{TS}}",
        text,
    )
    text = re.sub(r'"elapsed_ms": \d+', '"elapsed_ms": {{ELAPSED}}', text)
    text = re.sub(r'"enricher_run_id": "[0-9a-f]{12}"', '"enricher_run_id": "{{RUN}}"', text)
    text = re.sub(r"mem_[0-9a-f]{8}", "{{MEMID}}", text)
    text = re.sub(r"\b[0-9a-f]{40}\b", "{{SHA}}", text)

    def round_float(m: re.Match) -> str:
        return f"{m.group(1)}: {round(float(m.group(2)), 4)}"
    text = re.sub(r"(score[\"']?\s*[:=]\s*)(-?\d+\.\d{5,})", round_float, text)
    text = re.sub(
        r'"(score|enriched_score)": (-?\d+\.\d{5,})',
        lambda m: f'"{m.group(1)}": {round(float(m.group(2)), 4)}',
        text,
    )
    return text


# Casos byte-parity: (nombre, argv, cwd, root_de_normalización — el
# fixture cuyo path aparece en la salida). Los argv A03/A04 apuntan al
# fixture DEGRADADO; A01/A02/A05 al COMPLETO.
def casos(root: Path, degraded: Path, other: Path) -> list[tuple[str, list[str], Path, Path]]:
    r = str(root)
    d = str(degraded)
    return [
        ("A01 doctor texto completo", ["autopilot", "doctor", "--project-root", r], root, root),
        ("A02 doctor --json completo", ["autopilot", "doctor", "--json", "--project-root", r], root, root),
        ("A03 doctor texto degradado", ["autopilot", "doctor", "--project-root", d], degraded, degraded),
        ("A04 doctor --json degradado", ["autopilot", "doctor", "--json", "--project-root", d], degraded, degraded),
        # --project-root EXPLÍCITO desde un cwd ajeno (resolución canónica).
        ("A05 doctor --project-root explícito (cwd ajeno)", ["autopilot", "doctor", "--project-root", r], other, root),
    ]


def recolectar(binary: list[str], root: Path, degraded: Path, other: Path) -> str:
    blocks: list[str] = []
    for name, argv, cwd, norm_root in casos(root, degraded, other):
        rc, out, err = _run(binary, argv, cwd)
        norm = normalize(out + (f"\n--stderr--\n{err}" if err.strip() else ""), norm_root)
        blocks.append(f"### {name}\nrc={rc}\n{norm}")
    return "\n".join(blocks) + "\n"


# ---------------------------------------------------------------------------
# Equivalencias Fase 04 (install/uninstall) — sin paridad byte-a-byte
# ---------------------------------------------------------------------------

EQ_CASES = [
    ("E01 autopilot install (Fase 04)", ["autopilot", "install", "--ide", "pi"], "No such command 'install'."),
    ("E02 autopilot uninstall (Fase 04)", ["autopilot", "uninstall", "--ide", "pi"], "No such command 'uninstall'."),
]


def verificar_equivalencia(native: list[str], oracle: list[str], cwd: Path) -> list[str]:
    """Compara rc y mensaje núcleo entre el nativo y el oráculo REAL.
    Byte-parity NO aplica (formatos clap/typer distintos por diseño):
    el oráculo no expone el subcomando (eliminado Fase 04)."""
    lines: list[str] = []
    for name, argv, core in EQ_CASES:
        n_rc, n_out, n_err = _run(native, argv, cwd)
        o_rc, o_out, o_err = _run(oracle, argv, cwd)
        ok = (
            n_rc == o_rc == 2
            and core in n_err
            and core in o_err
            and n_out == ""
        )
        lines.append(
            f"### {name}\n"
            f"nativo rc={n_rc} core_msg={'yes' if core in n_err else 'NO'}\n"
            f"oraculo rc={o_rc} core_msg={'yes' if core in o_err else 'NO'}\n"
            f"equivalente={'PASS' if ok else 'FAIL'}"
        )
    return lines


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify", "bench"))
    parser.add_argument("--out", default="bench/parity/.p12-cierre-leaves2-a")
    parser.add_argument("--rust-bin", default=str(RS_DEBUG))
    parser.add_argument("--rust-bin-bench", default=str(RS_RELEASE))
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    out_dir = Path(args.out)
    golden_path = out_dir / "goldens_leaves2_a.txt"
    eq_path = out_dir / "goldens_leaves2_a_eq.txt"

    with tempfile.TemporaryDirectory(prefix="leaves2_a_") as td:
        base = Path(td).resolve()
        root = base / "proyecto"
        degraded = base / "degradado"
        other = base / "otro-cwd"
        for d in (root, degraded, other):
            d.mkdir(parents=True)
        construir_fixture_completa(root)
        construir_fixture_degradada(degraded)

        if args.mode == "build":
            report = recolectar([PY, "-m", "cortex.cli.main"], root, degraded, other)
            out_dir.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(report, encoding="utf-8")
            eq = verificar_equivalencia(
                [str(RS_DEBUG)], [PY, "-m", "cortex.cli.main"], other
            )
            eq_path.write_text("\n".join(eq) + "\n", encoding="utf-8")
            print(f"[BUILD] {golden_path} ({len(report.splitlines())} líneas)")
            print(f"[BUILD] {eq_path} ({len(eq)} equivalencias)")
            return 0

        if args.mode == "bench":
            binary = [args.rust_bin_bench]
            name, argv, cwd, _ = casos(root, degraded, other)[0]
            times = []
            for _ in range(args.n):
                t0 = time.perf_counter()
                subprocess.run(
                    binary + argv, cwd=str(cwd), capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=300,
                    env={**os.environ, "OMP_NUM_THREADS": "2"},
                )
                times.append((time.perf_counter() - t0) * 1000)
            avg = sum(times) / len(times)
            p95 = sorted(times)[int(len(times) * 0.95) - 1]
            print(
                f"[COLD] {name}: N={args.n} avg={avg:.1f}ms "
                f"p95={p95:.1f}ms max={max(times):.1f}ms"
            )
            return 0

        expected = golden_path.read_text(encoding="utf-8")
        actual = recolectar([args.rust_bin], root, degraded, other)
        if actual != expected:
            exp_lines = expected.splitlines()
            got_lines = actual.splitlines()
            for i, (a, b) in enumerate(zip(exp_lines, got_lines)):
                if a != b:
                    print(f"[FAIL] primera divergencia en línea {i + 1}:")
                    print(f"  esperado: {a!r}")
                    print(f"  obtenido: {b!r}")
                    break
            else:
                print(f"[FAIL] longitud difiere: {len(exp_lines)} vs {len(got_lines)}")
            print("[DIFF] primeras 20 líneas del lado nativo:")
            for l in got_lines[:20]:
                print(f"  {l!r}")
            return 1

        eq_expected = eq_path.read_text(encoding="utf-8")
        eq_actual = verificar_equivalencia(
            [args.rust_bin], [PY, "-m", "cortex.cli.main"], other
        )
        eq_actual_text = "\n".join(eq_actual) + "\n"
        if eq_actual_text != eq_expected or not all("equivalente=PASS" in l for l in eq_actual):
            print("[FAIL] equivalencias Fase 04 (install/uninstall):")
            for l in eq_actual:
                print(f"  {l}")
            return 1

        print(
            f"[PASS] cierre_leaves2_a byte-parity post-normalización "
            f"({len(expected.splitlines())} líneas) + equivalencias Fase 04"
        )
        print("✅ PARIDAD MITAD A — BAJA DEFINITIVA RUTA 2")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())