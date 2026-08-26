#!/usr/bin/env python3
"""Golden CIERRE T3-PAR — autopilot service + cli + tools MCP ×5.

Tres partes, un solo reporte:

[A] SERVICE end-to-end: ``cortex.autopilot.service.AutopilotService`` REAL
    sobre SessionService REAL con sesiones fixture en tmp (patrón T5
    `autopilot_session`), policies/detectors/lifecycle completos.
[B] MCP ×5 byte-a-byte: los 5 tools autopilot vía el DISPATCHER REAL
    (`_dispatch_tool_sync`) con `AutopilotMCPTools` sobre el servicio real.
[C] CLI dual: cada caso corre en fixtures gemelos contra el CLI Python y
    el binario nativo `rust/target/debug/cortex-cli`; los blobs deben ser
    idénticos tras normalizar (patrón P12B-8).

El checker Rust (`cargo run -p cortex-autopilot --example
cierre_autopilot_check`) reproduce [A]+[B] byte-a-byte; [C] ya compara
ambos lados internamente.

Normalización: {{ROOT}}, {{TS}} (ISO timestamps), {{MIN}} (minutos del
warning de checkpoint espaciado). Determinista: commits gitless (40
ceros), ids fixture fijos, sin git en tmp.

Uso:
    .venv/bin/python bench/parity/cierre_autopilot_golden.py build --out DIR
    .venv/bin/python bench/parity/cierre_autopilot_golden.py verify --out DIR
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("PYTHONHASHSEED", "0")

from cortex.autopilot.errors import NoActiveSessionError  # noqa: E402
from cortex.autopilot.lifecycle import (  # noqa: E402
    AutopilotCheckpointRequest,
    AutopilotFinishRequest,
    AutopilotPreflightRequest,
    AutopilotStartRequest,
)
from cortex.autopilot.mcp_tools import AutopilotMCPTools  # noqa: E402
from cortex.autopilot.policies import AutopilotMode, AutopilotPolicy  # noqa: E402
from cortex.autopilot.service import AutopilotService  # noqa: E402
from cortex.mcp.server import CortexMCPServer  # noqa: E402
from cortex.session.service import SessionService  # noqa: E402
from cortex.session.storage import SessionStorage  # noqa: E402
from cortex.workspace.layout import WorkspaceLayout  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RS_BIN = REPO / "rust" / "target" / "debug" / "cortex-cli"
PY_BIN = REPO / ".venv" / "bin" / "cortex"

SPEC_ID = "2026-05-16_demo"
GITLESS = "0" * 40
CLI_MARKER = "[[CLI-PART]]"

ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)")
MIN_RE = re.compile(r"\b\d+ minutes since")


def norm(text: str, *roots: Path) -> str:
    for r in roots:
        text = text.replace(str(r), "{{ROOT}}")
    text = ISO_RE.sub("{{TS}}", text)
    return MIN_RE.sub("{{MIN}} minutes since", text)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def seed_session(root: Path, summary="Demo summary") -> str:
    """Abrir una sesión REAL vía SessionService (el spec es quien crea)."""
    layout = WorkspaceLayout.discover(root)
    storage = SessionStorage(layout.repo_root / ".cortex" / "sessions")
    svc = SessionService(storage, layout.repo_root)
    rec = svc.open(
        spec_id=SPEC_ID,
        spec_path=Path(f"vault/specs/{SPEC_ID}.md"),
        spec_summary=summary,
    )
    return rec.session_id


def write_autopilot_yaml(root: Path, body: str) -> None:
    # Bootstrap ⇒ layout nuevo: {repo}/.cortex/autopilot.yaml.
    (root / ".cortex").mkdir(parents=True, exist_ok=True)
    (root / ".cortex" / "autopilot.yaml").write_text(body, encoding="utf-8")


def backdate_last_checkpoint(root: Path, minutes: int) -> None:
    """Editar el YAML de sesión: timestamp del último checkpoint → -N min."""
    path = root / ".cortex" / "sessions" / f"{SPEC_ID}.yaml"
    text = path.read_text(encoding="utf-8")
    idx = text.index("checkpoints:")
    m = ISO_RE.search(text, idx)
    assert m, "sin timestamp de checkpoint"
    new_ts = (
        datetime.now(timezone.utc) - timedelta(minutes=minutes)
    ).isoformat()
    path.write_text(text[: m.start()] + new_ts + text[m.end():], encoding="utf-8")


def service_at(root: Path) -> AutopilotService:
    return AutopilotService.from_project_root(root)


# ---------------------------------------------------------------------------
# Proyecciones deterministas
# ---------------------------------------------------------------------------


def p_warnings(warnings: list[str]) -> str:
    return repr(warnings)


def proj_start(res) -> str:
    return (
        f"session={res.session.session_id}\n"
        f"status={res.session.status.value}\n"
        f"mode={res.policy.mode.value}\n"
        f"warnings={p_warnings(res.warnings)}"
    )


def proj_checkpoint(res) -> str:
    return (
        f"count={len(res.session.checkpoints)}\n"
        f"status={res.session.status.value}\n"
        f"warnings={p_warnings(res.warnings)}"
    )


def proj_finish(res) -> str:
    note = res.session_note_path if res.session_note_path else ""
    return (
        f"status={res.session.status.value}\n"
        f"documented={res.documented}\n"
        f"blocked={res.blocked}\n"
        f"blocked_reason={res.blocked_reason}\n"
        f"note={note}\n"
        f"summary={res.summary}\n"
        f"warnings={p_warnings(res.warnings)}"
    )


def proj_status(res) -> str:
    if not res.active or res.session is None:
        mode = res.policy.mode.value if res.policy else "unknown"
        return f"active=False\nmode={mode}"
    s = res.session
    return (
        f"active=True\nsession={s.session_id}\nstatus={s.status.value}\n"
        f"mode={res.policy.mode.value}\ninferred={res.inferred_mode}\n"
        f"count={res.checkpoint_count}"
    )


def proj_detection(d) -> str:
    return (
        f"task_type={d.task_type}\n"
        f"confidence={float(d.confidence)!r}\n"
        f"reason={d.reason}\n"
        f"suggested_complexity={d.suggested_complexity}"
    )


# ---------------------------------------------------------------------------
# Parte A — SERVICE end-to-end (servicio real, sesiones reales)
# ---------------------------------------------------------------------------


def build_service_scenarios(base: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def emit(name: str, fn):
        try:
            out.append((name, fn()))
        except Exception as exc:  # noqa: BLE001
            out.append((name, f"Exception: {type(exc).__name__}: {exc}"))

    def A01():
        root = base / "a01"
        root.mkdir(parents=True)
        try:
            service_at(root).start(AutopilotStartRequest())
        except NoActiveSessionError as exc:
            return f"NoActiveSessionError: {exc}"

    def A02():
        root = base / "a02"
        root.mkdir(parents=True)
        seed_session(root)
        return proj_start(service_at(root).start(AutopilotStartRequest()))

    def A03():
        root = base / "a03"
        root.mkdir(parents=True)
        seed_session(root, summary="Implement password reset flow")
        return proj_start(service_at(root).start(AutopilotStartRequest()))

    def A04():
        root = base / "a04"
        root.mkdir(parents=True)
        res = service_at(root).preflight(
            AutopilotPreflightRequest(user_request="What does this function do?")
        )
        return proj_detection(res.detection)

    def A05():
        root = base / "a05"
        root.mkdir(parents=True)
        seed_session(root)
        res = service_at(root).checkpoint(
            AutopilotCheckpointRequest(
                source="manual",
                verified_claims=["claim uno"],
                note="primer paso",
            )
        )
        return proj_checkpoint(res)

    def A06():
        root = base / "a06"
        root.mkdir(parents=True)
        seed_session(root)
        res = service_at(root).checkpoint(
            AutopilotCheckpointRequest(
                source="manual",
                artifacts_touched=["src/b.py", "src/a.py"],
                files_in_scope=["src/a.py"],
            )
        )
        return proj_checkpoint(res)

    def A07():
        root = base / "a07"
        root.mkdir(parents=True)
        seed_session(root)
        svc = service_at(root)
        svc.checkpoint(
            AutopilotCheckpointRequest(source="manual", artifacts_touched=["f1", "f2", "f3"])
        )
        res = svc.checkpoint(
            AutopilotCheckpointRequest(source="manual", artifacts_touched=["f4", "f5", "f6"])
        )
        return proj_checkpoint(res)

    def A08():
        root = base / "a08"
        root.mkdir(parents=True)
        seed_session(root)
        svc = service_at(root)
        svc.checkpoint(AutopilotCheckpointRequest(source="manual", artifacts_touched=["f1"]))
        backdate_last_checkpoint(root, 20)
        res = svc.checkpoint(AutopilotCheckpointRequest(source="manual", artifacts_touched=["f2"]))
        return proj_checkpoint(res)

    def A09():
        root = base / "a09"
        root.mkdir(parents=True)
        seed_session(root)
        svc = service_at(root)
        first = proj_finish(
            svc.finish(AutopilotFinishRequest(auto=False, intent="closed"))
        )
        # Segundo finish con id explícito: ya terminal ⇒ no-op sin puntero.
        again = proj_finish(
            svc.finish(
                AutopilotFinishRequest(session_id=SPEC_ID, auto=False, intent="closed")
            )
        )
        return first + "\n---second---\n" + again

    def A10():
        root = base / "a10"
        root.mkdir(parents=True)
        seed_session(root)
        return proj_finish(
            service_at(root).finish(AutopilotFinishRequest(auto=False, intent="handoff"))
        )

    def A11():
        root = base / "a11"
        root.mkdir(parents=True)
        write_autopilot_yaml(root, "mode: autopilot\n")
        seed_session(root)
        return proj_finish(
            service_at(root).finish(AutopilotFinishRequest(auto=False))
        )

    def A12():
        root = base / "a12"
        root.mkdir(parents=True)
        seed_session(root)
        svc = service_at(root)
        active = proj_status(svc.status(None))
        named = proj_status(svc.status(SPEC_ID))
        missing = proj_status(svc.status("2026-01-01_missing"))
        return active + "\n---named---\n" + named + "\n---missing---\n" + missing

    def A13():
        root = base / "a13"
        root.mkdir(parents=True)
        seed_session(root)
        try:
            service_at(root).checkpoint(AutopilotCheckpointRequest(source="nope"))
        except Exception as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"

    def A14():
        root = base / "a14"
        root.mkdir(parents=True)
        seed_session(root)
        layout = WorkspaceLayout.discover(root)
        storage = SessionStorage(layout.repo_root / ".cortex" / "sessions")
        svc = AutopilotService(
            session_service=SessionService(storage, layout.repo_root),
            policy=AutopilotPolicy(),
            repo_root=layout.repo_root,
            memory_factory=None,
        )
        return proj_finish(svc.finish(AutopilotFinishRequest(auto=True)))

    def A15():
        root = base / "a15"
        root.mkdir(parents=True)
        seed_session(root)
        svc = service_at(root)
        started = proj_start(svc.start(AutopilotStartRequest(mode=AutopilotMode.OBSERVE)))
        res = svc.checkpoint(
            AutopilotCheckpointRequest(
                source="manual",
                artifacts_touched=["src/out.py"],
                files_in_scope=["src/in.py"],
            )
        )
        return started + "\n---after-drift---\n" + proj_checkpoint(res)

    for name, fn in [
        ("A01 start sin activa", A01),
        ("A02 start adopta assist", A02),
        ("A03 start warning seguridad", A03),
        ("A04 preflight question-only", A04),
        ("A05 checkpoint manual ok", A05),
        ("A06 checkpoint drift fuera de scope", A06),
        ("A07 threshold archivos sin verificar", A07),
        ("A08 checkpoint espaciado minutos", A08),
        ("A09 finish manual closed + no-op", A09),
        ("A10 finish handoff", A10),
        ("A11 blocked autopilot sin verificación", A11),
        ("A12 status activa/nombrada/faltante", A12),
        ("A13 checkpoint fuente desconocida", A13),
        ("A14 finish auto sin memory_factory", A14),
        ("A15 override a observe apaga warnings", A15),
    ]:
        emit(name, fn)
    return out


# ---------------------------------------------------------------------------
# Parte B — MCP ×5 byte-a-byte vía dispatcher real
# ---------------------------------------------------------------------------


def make_server(root: Path):
    srv = CortexMCPServer.__new__(CortexMCPServer)
    srv.memory = None  # type: ignore[assignment]
    srv._called_tools = set()
    srv._tool_call_history = []
    srv._last_proposal_emitted_at = None
    srv.project_root = root
    srv._autopilot_tools = AutopilotMCPTools(service_at(root))
    return srv


def build_mcp_scenarios(base: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []

    def call(srv, name, args=None):
        srv._called_tools.add(name)
        try:
            return srv._dispatch_tool_sync(name, dict(args or {}))
        except Exception as exc:  # noqa: BLE001
            return f"Error ejecutando {name}: {exc}"

    def emit(name: str, fn):
        try:
            out.append((name, fn()))
        except Exception as exc:  # noqa: BLE001
            out.append((name, f"Exception: {type(exc).__name__}: {exc}"))

    def B01():
        root = base / "b01"
        root.mkdir(parents=True)
        seed_session(root)
        return call(make_server(root), "cortex_autopilot_start", {})

    def B02():
        root = base / "b02"
        root.mkdir(parents=True)
        return call(make_server(root), "cortex_autopilot_start", {})

    def B03():
        root = base / "b03"
        root.mkdir(parents=True)
        return call(
            make_server(root), "cortex_autopilot_start", {"mode": "turbo"}
        )

    def B04():
        root = base / "b04"
        root.mkdir(parents=True)
        return call(
            make_server(root),
            "cortex_autopilot_preflight",
            {"user_request": "What does this function do?"},
        )

    def B05():
        root = base / "b05"
        root.mkdir(parents=True)
        seed_session(root)
        return call(
            make_server(root),
            "cortex_autopilot_checkpoint",
            {
                "source": "manual",
                "verified_claims": ["claim uno"],
                "unverified_claims": [],
                "artifacts_touched": ["src/b.py", "src/a.py"],
                "files_in_scope": ["src/a.py"],
            },
        )

    def B06():
        root = base / "b06"
        root.mkdir(parents=True)
        seed_session(root)
        return call(
            make_server(root),
            "cortex_autopilot_checkpoint",
            {"source": "nope"},
        )

    def B07():
        root = base / "b07"
        root.mkdir(parents=True)
        seed_session(root)
        srv = make_server(root)
        finish_out = call(
            srv, "cortex_autopilot_finish", {"auto": False}
        )
        status_out = call(srv, "cortex_autopilot_status", {})
        return finish_out + "\n---status---\n" + status_out

    def B08():
        root = base / "b08"
        root.mkdir(parents=True)
        write_autopilot_yaml(root, "mode: autopilot\n")
        seed_session(root)
        return call(make_server(root), "cortex_autopilot_finish", {})

    def B09():
        root = base / "b09"
        root.mkdir(parents=True)
        seed_session(root)
        srv = make_server(root)
        call(srv, "cortex_autopilot_finish", {"auto": False})
        return call(
            srv,
            "cortex_autopilot_finish",
            {"session_id": SPEC_ID},
        )

    def B10():
        root = base / "b10"
        root.mkdir(parents=True)
        seed_session(root)
        return call(make_server(root), "cortex_autopilot_status", {})

    def B11():
        root = base / "b11"
        root.mkdir(parents=True)
        return call(make_server(root), "cortex_autopilot_status", {})

    def B12():
        root = base / "b12"
        root.mkdir(parents=True)
        seed_session(root)
        return call(
            make_server(root),
            "cortex_autopilot_finish",
            {"session_id": "2026-01-01_x"},
        )

    def B13():
        root = base / "b13"
        root.mkdir(parents=True)
        seed_session(root)
        return call(
            make_server(root), "cortex_autopilot_start", {"mode": "observe"}
        )

    def B14():
        root = base / "b14"
        root.mkdir(parents=True)
        seed_session(root)
        # Coerción contractual de _str_list/_opt: no-lista ⇒ [], null ⇒ None.
        return call(
            make_server(root),
            "cortex_autopilot_preflight",
            {"changed_files": "no-es-lista", "user_request": None},
        )

    for name, fn in [
        ("B01 mcp start ok", B01),
        ("B02 mcp start sin activa", B02),
        ("B03 mcp start modo inválido", B03),
        ("B04 mcp preflight formato", B04),
        ("B05 mcp checkpoint drift warnings", B05),
        ("B06 mcp checkpoint fuente inválida", B06),
        ("B07 mcp finish manual + status", B07),
        ("B08 mcp finish bloqueado", B08),
        ("B09 mcp finish doble no-op", B09),
        ("B10 mcp status activa", B10),
        ("B11 mcp status inactiva", B11),
        ("B12 mcp finish id inexistente", B12),
        ("B13 mcp start override observe", B13),
        ("B14 mcp preflight coerción de tipos", B14),
    ]:
        emit(name, fn)
    return out


# ---------------------------------------------------------------------------
# Parte C — CLI dual (Python vs binario nativo, fixtures gemelos)
# ---------------------------------------------------------------------------


def mk_cli_fixture(workdir: Path, tag: str, *, seed: bool, ap_yaml: str | None) -> Path:
    root = workdir / tag / "proj"
    root.mkdir(parents=True)
    if ap_yaml:
        write_autopilot_yaml(root, ap_yaml)
    if seed:
        seed_session(root)
    return root


def run_cli(bin_path: Path, root: Path, args: list[str]) -> tuple[str, int]:
    env = dict(os.environ)
    env.setdefault("CORTEX_BIN", str(PY_BIN))
    proc = subprocess.run(
        [str(bin_path)] + args, cwd=root, env=env, capture_output=True, timeout=120
    )
    blob = norm(proc.stdout.decode(), root)
    if proc.stderr:
        blob += "---STDERR---\n" + norm(proc.stderr.decode(), root)
    blob += f"rc={proc.returncode}"
    return blob, proc.returncode


CLI_CASES: list[tuple[str, bool, str | None, list[str]]] = [
    ("C01 status json inactiva", False, None, ["autopilot", "status", "--json"]),
    ("C02 status texto inactiva", False, None, ["autopilot", "status"]),
    ("C03 start sin activa json", False, None, ["autopilot", "start", "--json"]),
    ("C04 status json activa", True, None, ["autopilot", "status", "--json"]),
    (
        "C05 checkpoint json",
        True,
        None,
        [
            "autopilot",
            "checkpoint",
            "--source",
            "manual",
            "--verified-claim",
            "claim uno",
            "--artifact",
            "src/a.py",
            "--note",
            "nota",
            "--json",
        ],
    ),
    (
        "C06 checkpoint fuente inválida",
        True,
        None,
        ["autopilot", "checkpoint", "--source", "nope"],
    ),
    (
        "C07 preflight json",
        False,
        None,
        [
            "autopilot",
            "preflight",
            "--request",
            "What does this function do?",
            "--json",
        ],
    ),
    (
        "C08 finish handoff json",
        True,
        None,
        ["autopilot", "finish", "--handoff", "--json"],
    ),
    (
        "C09 finish bloqueado json",
        True,
        "mode: autopilot\n",
        ["autopilot", "finish", "--json"],
    ),
    (
        "C10 start observe json",
        True,
        None,
        ["autopilot", "start", "--mode", "observe", "--json"],
    ),
]


def build_cli_section(workdir: Path) -> tuple[list[str], list[str]]:
    """Corre cada caso en fixtures gemelos; devuelve (blobs, fallos)."""
    if not RS_BIN.exists():
        return [], [f"binario nativo ausente: {RS_BIN} (cargo build -p cortex-cli)"]
    blobs: list[str] = []
    failures: list[str] = []
    for i, (name, seed, ap_yaml, args) in enumerate(CLI_CASES):
        py_root = mk_cli_fixture(workdir, f"c{i:02d}_py", seed=seed, ap_yaml=ap_yaml)
        rs_root = mk_cli_fixture(workdir, f"c{i:02d}_rs", seed=seed, ap_yaml=ap_yaml)
        py_blob, _ = run_cli(PY_BIN, py_root, args)
        rs_blob, _ = run_cli(RS_BIN, rs_root, args)
        if py_blob != rs_blob:
            failures.append(name)
            blobs.append(f"### {name}\n[PAY-DIVERGENCE]\n---py---\n{py_blob}\n---rs---\n{rs_blob}")
        else:
            blobs.append(f"### {name}\n{py_blob}")
    return blobs, failures


# ---------------------------------------------------------------------------
# Reporte + main
# ---------------------------------------------------------------------------


def render(blocks: list[tuple[str, str]], roots: list[Path]) -> str:
    parts = []
    for name, body in blocks:
        parts.append(f"### {name}\nrc=0\n{norm(body, *roots)}")
    return "\n".join(parts) + "\n"


def build_report(workdir: Path) -> str:
    ab_roots: list[Path] = []
    sections: list[str] = []

    for label, builder in (("A", build_service_scenarios), ("B", build_mcp_scenarios)):
        sub = workdir / label.lower()
        sub.mkdir()
        blocks = builder(sub)
        ab_roots.append(sub.resolve())
        sections.append(render(blocks, [sub.resolve()]))

    prefix = f"[SERVICE]\n{sections[0]}[MCP]\n{sections[1]}{CLI_MARKER}\n"

    cli_blobs, failures = build_cli_section(workdir)
    if failures:
        print("[FAIL] casos CLI divergentes py-vs-rs:", ", ".join(failures))
        raise SystemExit(1)
    cli_body = "".join(blob if blob.endswith("\n") else blob + "\n" for blob in cli_blobs)
    return prefix + "[CLI]\n" + cli_body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=("build", "verify"))
    ap.add_argument("--out", default="bench/parity/.p12-cierre-autopilot")
    ns = ap.parse_args()

    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden_path = out_dir / "golden_cierre_autopilot.txt"

    workdir = Path(tempfile.mkdtemp(prefix="cierre_ap_"))
    try:
        report = build_report(workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    if ns.cmd == "build":
        golden_path.write_text(report, encoding="utf-8")
        print(f"[BUILD] {golden_path} ({len(report.splitlines())} líneas)")
        return 0

    expected = golden_path.read_text(encoding="utf-8")
    if report != expected:
        exp_lines = expected.splitlines()
        got_lines = report.splitlines()
        for i, (a, b) in enumerate(zip(exp_lines, got_lines)):
            if a != b:
                print(f"[FAIL] primera divergencia en línea {i + 1}:")
                print(f"  esperado: {a!r}")
                print(f"  obtenido: {b!r}")
                break
        else:
            print(f"[FAIL] longitud difiere: {len(exp_lines)} vs {len(got_lines)}")
        return 1
    print(
        f"[PASS] golden_cierre_autopilot.txt ({len(expected.splitlines())} líneas)"
    )
    print("[PASS] CLI dual py-vs-rs idéntico en los 10 casos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
