#!/usr/bin/env python3
"""Golden MITAD B — BAJA DEFINITIVA RUTA 2 (webgraph serve/doctor + hu import).

Compara el binario nativo `cortex-cli` contra el CLI Python REAL (console
script `.venv/bin/cortex`, igual que cierre_leaves_b de RUTA 1) sobre
fixtures deterministas en tmp, con las normalizaciones PACTADAS:

- {{ROOT}}   : tmp del fixture
- {{TS}}     : timestamps ISO (drift de reloj; notas del import)
- {{ELAPSED}}/{{RUN}}/{{MEMID}}: no producidas por esta familia (reservadas)
- {{SHA}}    : SHAs git de 40 hex (fixtures gitless ⇒ rara vez)
- scores a 4 decimales (no producidos acá; reservado)

Casos byte-parity (terminales):
- `webgraph doctor` sobre fixture COMPLETA (workspace + vault + memory/
  chroma ⇒ 5 checks OK, "WebGraph doctor passed.") y sobre fixture
  DEGRADADA (sin vault ⇒ FAIL en vault_dir/episodic_store, rc 1).
- `webgraph doctor --project-root` explícito desde otro cwd.
- `hu import PROJ-1` éxito (jira enabled con base_url file:// fake en tmp
  + env JIRA_EMAIL/JIRA_API_TOKEN ⇒ "Tracked item imported -> {{ROOT}}...").
- `hu import --no-remember` (variante del éxito; rc 0 y misma salida).

Caso especial NO-terminal (documentado, patrón P12B-2):
- `webgraph serve` — smoke acotado: arranca en puerto efímero con
  --no-open, poll GET / hasta 200, se mata el proceso. El bloque del gate
  registra SÓLO el resultado del smoke (status + kill), no los logs de
  arranque (Flask imprime banner/timestamps/ANSI no-portables por diseño).
  Se documenta como "caso especial no-terminal", no como caso normal.

Casos de equivalencia (SIN paridad byte-a-byte, pactado en el brief — S19
de RUTA 1 ya documentó que el oráculo de `hu import` emite traceback rich
no-portable ante errores de provider):
- `hu import --provider nope` — oráculo: KeyError → traceback rc 1;
  nativo: mensaje limpio "Unknown work item provider: nope" rc 1.
  Se comparan rc + mensaje núcleo en vivo.
- `hu import` con jira enabled PERO sin credenciales (env ausente) —
  oráculo: RuntimeError → traceback rc 1; nativo: "Provider 'jira' is
  not configured." rc 1. Equivalencia rc + mensaje núcleo.

Modos:
  build  → congela la salida NORMALIZADA del CLI Python en
           goldens_leaves2_b.txt (+ informes de equivalencias y smoke)
  verify → corre ambos lados y compara normalizados + re-verifica
           equivalencia y smoke en vivo
  bench  → cold start N=20 de doctor + hu import + motivo de arranque
           de serve (tiempo hasta primera respuesta 200)
"""

from __future__ import annotations

import argparse
import http.client
import os
import re
import socket
import subprocess
import sys
import shutil
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("PYTHONHASHSEED", "0")

REPO = Path(__file__).resolve().parents[2]
PY = str(REPO / ".venv" / "bin" / "cortex")
RS_DEBUG = REPO / "rust" / "target" / "debug" / "cortex-cli"
RS_RELEASE = REPO / "rust" / "target" / "release" / "cortex-cli"

ROOT_MARK = "{{ROOT}}"
JIRA_ENV = {"JIRA_EMAIL": "a@b.c", "JIRA_API_TOKEN": "tok"}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ISSUE_BODY = (
    '{"key":"PROJ-1","fields":{"summary":"Hacer login","issuetype":{"name":"Story"},'
    '"description":{"type":"doc","content":[{"type":"paragraph","content":'
    '[{"type":"text","text":"Bueno"}]}],"version":1},"labels":["auth"],'
    '"assignee":{"displayName":"Ana"},"status":{"name":"In Progress"},'
    '"priority":{"name":"High"}}}'
)


def _cortex_base(root: Path, jira: bool) -> None:
    cortex = root / ".cortex"
    cortex.mkdir(parents=True)
    (cortex / "workspace.yaml").write_text("layout_version: 2\n", encoding="utf-8")
    if jira:
        (cortex / "config.yaml").write_text(
            "semantic:\n  vault_path: vault\n"
            f"integrations:\n  jira:\n    enabled: true\n"
            f'    base_url: "file://{root}/jira/"\n',
            encoding="utf-8",
        )
        issue = root / "jira" / "rest" / "api" / "3" / "issue"
        issue.mkdir(parents=True)
        (issue / "PROJ-1").write_text(ISSUE_BODY, encoding="utf-8")
    else:
        (cortex / "config.yaml").write_text(
            "semantic:\n  vault_path: vault\n", encoding="utf-8"
        )


def construir_fixture_completa(root: Path) -> None:
    """workspace + config + vault + memory/chroma ⇒ doctor 5 OK."""
    _cortex_base(root, jira=True)
    (root / ".cortex" / "vault").mkdir(exist_ok=True)
    (root / ".cortex" / "memory" / "chroma").mkdir(parents=True, exist_ok=True)


def construir_fixture_degradada(root: Path) -> None:
    """workspace + config, SIN vault ni memory ⇒ FAIL vault/episodic."""
    _cortex_base(root, jira=False)


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------


def _run(
    binary: list[str],
    args: list[str],
    cwd: Path,
    extra_env=None,
    clean: tuple[str, ...] = (),
) -> tuple[int, str, str]:
    env = {**os.environ, "OMP_NUM_THREADS": "2"}
    if extra_env:
        env.update(extra_env)
    for k in clean:
        env.pop(k, None)
    proc = subprocess.run(
        binary + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def normalize(text: str, root: Path) -> str:
    text = text.replace(str(root), ROOT_MARK)
    text = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)?",
        "{{TS}}",
        text,
    )
    text = re.sub(r"\b[0-9a-f]{40}\b", "{{SHA}}", text)
    return text


def casos(root: Path, degraded: Path, hu_b4: Path, hu_b5: Path) -> list[tuple[str, list[str], Path, Path]]:
    r = str(root)
    d = str(degraded)
    return [
        ("B01 webgraph doctor completa", ["webgraph", "doctor", "--project-root", r], root, root),
        ("B02 webgraph doctor degradada", ["webgraph", "doctor", "--project-root", d], degraded, degraded),
        ("B03 webgraph doctor --project-root desde otro cwd", ["webgraph", "doctor", "--project-root", r], degraded, r),
        ("B04 hu import exito", ["hu", "import", "PROJ-1"], hu_b4, hu_b4),
        ("B05 hu import --no-remember", ["hu", "import", "PROJ-1", "--no-remember"], hu_b5, hu_b5),
    ]


def recolectar(binary: list[str], root: Path, degraded: Path, hb4: Path, hb5: Path) -> str:
    blocks: list[str] = []
    for name, argv, cwd, norm_root in casos(root, degraded, hb4, hb5):
        rc, out, err = _run(binary, argv, cwd, extra_env=JIRA_ENV)
        norm = normalize(out + (f"\n--stderr--\n{err}" if err.strip() else ""), norm_root)
        blocks.append(f"### {name}\nrc={rc}\n{norm}")
    return "\n".join(blocks) + "\n"


# ---------------------------------------------------------------------------
# Smoke de serve (caso especial no-terminal, patrón P12B-2)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def smoke_serve(binary: list[str], root: Path) -> str:
    """Arranca el server, poll GET / hasta 200, mata el proceso. Devuelve
    una línea determinista con el resultado del smoke (NO los logs)."""
    port = _free_port()
    env = {**os.environ, "OMP_NUM_THREADS": "2"}
    proc = subprocess.Popen(
        binary
        + [
            "webgraph",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-open",
            "--project-root",
            str(root),
        ],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    status = "TIMEOUT"
    try:
        for _ in range(100):
            if proc.poll() is not None:
                status = "DIED_EARLY"
                break
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                conn.request("GET", "/", headers={"Connection": "close"})
                resp = conn.getresponse()
                got = resp.status
                conn.close()
                if got in (200, 403):
                    status = str(got)
                    break
            except OSError:
                time.sleep(0.05)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    except Exception:  # noqa: BLE001
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        status = "FAIL"
    return f"smoke_serve\nstarted=ok\nGET / status={status}\nkilled=ok\n"


# ---------------------------------------------------------------------------
# Equivalencias hu import (S19: traceback del oráculo no-portable)
# ---------------------------------------------------------------------------

EQ_CASES = [
    (
        "E01 hu import provider desconocido",
        ["hu", "import", "PROJ-1", "--provider", "nope"],
        "Unknown work item provider: nope",
        dict(JIRA_ENV),
    ),
    (
        "E02 hu import jira sin credenciales",
        ["hu", "import", "PROJ-1"],
        "Provider 'jira' is not configured.",
        {},  # sin JIRA_EMAIL/JIRA_API_TOKEN ⇒ registrado pero no configurado
    ),
]


def verificar_equivalencia(native: list[str], oracle: list[str], cwd: Path) -> list[str]:
    """Compara rc y mensaje núcleo entre nativo y oráculo REAL para los
    errores de provider (oráculo: KeyError/RuntimeError → traceback rich
    no-portable; nativo: mensaje limpio — paridad del ORIGEN, no bytes)."""
    lines: list[str] = []
    for name, argv, core, extra_env in EQ_CASES:
        # E02 debe correr SIN credenciales: desinfectamos el entorno.
        n_rc, n_out, n_err = _run(native, argv, cwd, extra_env=extra_env, clean=("JIRA_EMAIL", "JIRA_API_TOKEN"))
        o_rc, o_out, o_err = _run(oracle, argv, cwd, extra_env=extra_env, clean=("JIRA_EMAIL", "JIRA_API_TOKEN"))
        ok = n_rc == o_rc == 1 and core in n_err and core in o_err and n_out == ""
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
    parser.add_argument("--out", default="bench/parity/.p12-cierre-leaves2-b")
    parser.add_argument("--rust-bin", default=str(RS_DEBUG))
    parser.add_argument("--rust-bin-bench", default=str(RS_RELEASE))
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    out_dir = Path(args.out)
    golden_path = out_dir / "goldens_leaves2_b.txt"
    smoke_path = out_dir / "goldens_leaves2_b_smoke.txt"
    eq_path = out_dir / "goldens_leaves2_b_eq.txt"

    with tempfile.TemporaryDirectory(prefix="leaves2_b_") as td:
        base = Path(td).resolve()
        root = base / "proyecto"
        degraded = base / "degradado"
        other = base / "otro-cwd"
        for d in (root, degraded, other):
            d.mkdir(parents=True)
        construir_fixture_completa(root)
        construir_fixture_degradada(degraded)

        # Copias PRISTINAS para cada caso `hu import` (el import escribe la
        # nota; re-importar sobre la misma fixture dispara el duplicate-chek).
        hu_b4 = base / "hu-b4"
        hu_b5 = base / "hu-b5"
        shutil.copytree(root, hu_b4)
        shutil.copytree(root, hu_b5)
        from cortex.workspace.layout import WorkspaceLayout as _WL
        for d in (hu_b4, hu_b5):
            vault = d / ".cortex" / "vault"
            if vault.exists():
                shutil.rmtree(vault)
            memory = d / ".cortex" / "memory"
            if memory.exists():
                shutil.rmtree(memory)
            (d / ".cortex" / "vault").mkdir(parents=True)

        if args.mode == "build":
            out_dir.mkdir(parents=True, exist_ok=True)
            report = recolectar([PY], root, degraded, hu_b4, hu_b5)
            golden_path.write_text(report, encoding="utf-8")
            smoke = smoke_serve([PY], root)
            smoke_path.write_text(smoke, encoding="utf-8")
            eq = verificar_equivalencia([str(RS_DEBUG)], [PY], root)
            eq_path.write_text("\n".join(eq) + "\n", encoding="utf-8")
            print(f"[BUILD] {golden_path} ({len(report.splitlines())} líneas)")
            print(f"[BUILD] {smoke_path} — smoke serve ({len(smoke.splitlines())} líneas)")
            print(f"[BUILD] {eq_path} ({len(eq)} equivalencias)")
            return 0

        if args.mode == "bench":
            binary = [args.rust_bin_bench]
            casos_list = casos(root, degraded, hu_b4, hu_b5)
            # doctor terminal (B01)
            name, argv, cwd, _ = casos_list[0]
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
            print(f"[COLD] {name}: N={args.n} avg={avg:.1f}ms p95={p95:.1f}ms max={max(times):.1f}ms")

            # hu import terminal (B04) — con providers file:// ya construidos.
            name, argv, cwd, _ = casos_list[3]
            times = []
            import shutil as _sh
            hb = base / "hu-bench"
            for _ in range(args.n):
                _sh.rmtree(hb, ignore_errors=True)
                _sh.copytree(root, hb)
                (hb / ".cortex" / "vault").mkdir(parents=True, exist_ok=True)
                t0 = time.perf_counter()
                subprocess.run(
                    binary + argv, cwd=str(hb), capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=300,
                    env={**os.environ, "OMP_NUM_THREADS": "2", **JIRA_ENV},
                )
                times.append((time.perf_counter() - t0) * 1000)
            avg = sum(times) / len(times)
            p95 = sorted(times)[int(len(times) * 0.95) - 1]
            print(f"[COLD] {name}: N={args.n} avg={avg:.1f}ms p95={p95:.1f}ms max={max(times):.1f}ms")

            # serve: arranque hasta primera respuesta 200 (smoke timing).
            port = _free_port()
            t0 = time.perf_counter()
            proc = subprocess.Popen(
                binary + ["webgraph", "serve", "--host", "127.0.0.1", "--port", str(port),
                          "--no-open", "--project-root", str(root)],
                cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env={**os.environ, "OMP_NUM_THREADS": "2"},
            )
            started = None
            try:
                for _ in range(200):
                    try:
                        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                        conn.request("GET", "/", headers={"Connection": "close"})
                        if conn.getresponse().status == 200:
                            started = (time.perf_counter() - t0) * 1000
                            break
                    except OSError:
                        time.sleep(0.05)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if started is None:
                print("[COLD] webgraph serve: TIMEOUT de arranque")
                return 1
            print(f"[COLD] webgraph serve arranque (hasta 200): {started:.0f}ms")
            return 0

        expected = golden_path.read_text(encoding="utf-8")
        actual = recolectar([args.rust_bin], root, degraded, hu_b4, hu_b5)
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

        smoke_expected = smoke_path.read_text(encoding="utf-8")
        smoke_actual = smoke_serve([args.rust_bin], root)
        if smoke_actual != smoke_expected:
            print("[FAIL] smoke serve diverge:")
            print(f"  esperado: {smoke_expected!r}")
            print(f"  obtenido: {smoke_actual!r}")
            return 1

        eq_expected = eq_path.read_text(encoding="utf-8")
        eq_actual = verificar_equivalencia([args.rust_bin], [PY], root)
        eq_actual_text = "\n".join(eq_actual) + "\n"
        if eq_actual_text != eq_expected or not all("equivalente=PASS" in l for l in eq_actual):
            print("[FAIL] equivalencias hu import:")
            for l in eq_actual:
                print(f"  {l}")
            return 1

        print(
            f"[PASS] cierre_leaves2_b byte-parity post-normalización "
            f"({len(expected.splitlines())} líneas) + smoke serve + equivalencias"
        )
        print("✅ PARIDAD MITAD B — BAJA DEFINITIVA RUTA 2")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())