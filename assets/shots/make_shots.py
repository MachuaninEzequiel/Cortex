#!/usr/bin/env python3
"""Regenera las capturas del README (assets/shots/*.png) con el diseño vigente.

Pipeline determinista, sin terminal real:
  1. fixture Cortex en tmp (config.yaml + vault + sesiones reales);
  2. `cargo run -p cortex-tui --example capture` vuelca el ANSI truecolor
     EXACTO del render de cada pantalla (TestBackend);
  3. rasterizador PIL: cada celda es un rectángulo con fuente mono sobre el
     fondo de las capturas históricas (#0D1117).

Uso:  python3 assets/shots/make_shots.py [--no-build]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
SHOTS = ROOT / "assets" / "shots"
BG = (0x0D, 0x11, 0x17)  # fondo histórico de las capturas (GitHub Dark)

FONT_CANDIDATES = [
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-Regular.ttf",
    "/usr/share/fonts/TTF/JetBrainsMonoNLNerdFont-Bold.ttf",
    "/usr/share/fonts/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]

SESSIONS = [
    dict(
        session_id="2026-08-24_migracion-rust",
        spec_path="vault/specs/2026-08-24_migracion-rust.md",
        spec_summary="Portar la TUI rica a ratatui con paridad de datos.",
        start_commit="a" * 40,
        start_branch="feature/transformacion-2026-08",
        opened_at="2026-08-24T09:12:00+00:00",
        status="open",
        mode="unknown",
        checkpoints=[
            dict(
                timestamp="2026-08-24T10:30:00+00:00",
                source="manual",
                note="pantalla sesiones con tema semántico",
            ),
            dict(
                timestamp="2026-08-24T12:05:00+00:00",
                source="ide-hook",
                note="snapshots deterministas con reloj inyectado",
            ),
            dict(
                timestamp="2026-08-24T14:22:00+00:00",
                source="cortex-SDDwork",
                note="overlay de revisión previa para acciones",
            ),
        ],
    ),
    dict(
        session_id="2026-08-23_actionengine",
        spec_path="vault/specs/2026-08-23_actionengine.md",
        spec_summary="Ciclo observar-proponer-aprobar-ejecutar-aprender.",
        start_commit="b" * 40,
        start_branch="feature/action-engine",
        opened_at="2026-08-23T08:00:00+00:00",
        status="closed",
        mode="managed",
        closed_at="2026-08-23T18:40:00+00:00",
        end_commit="b" * 40,
        documenter_decision="closed",
        checkpoints=[
            dict(
                timestamp="2026-08-23T11:00:00+00:00",
                source="cortex-sync",
                note="scheduler con score impacto×frescura−costo",
            ),
        ],
    ),
    dict(
        session_id="2026-08-21_ci-review",
        spec_path="vault/specs/2026-08-21_ci-review.md",
        spec_summary="Gate de CI con revisión en dos etapas.",
        start_commit="c" * 40,
        start_branch="feature/ci-gates",
        opened_at="2026-08-21T15:30:00+00:00",
        status="handoff",
        mode="ci-review",
        closed_at="2026-08-21T19:10:00+00:00",
        end_commit="c" * 40,
        documenter_decision="handoff",
        checkpoints=[
            dict(
                timestamp="2026-08-21T16:00:00+00:00",
                source="ci-bot",
                note="verificación: 42 tests, 0 fallos",
            ),
        ],
    ),
]


def session_yaml(s: dict) -> str:
    lines = []
    for k in ("session_id", "spec_path", "spec_summary", "start_commit", "start_branch", "opened_at"):
        lines.append(f"{k}: {s[k]!r}" if k in ("session_id", "spec_path", "spec_summary", "start_branch", "opened_at") else f"{k}: {s[k]!r}")
    lines.append(f"status: {s['status']!r}")
    lines.append(f"mode: {s['mode']!r}")
    lines.append("checkpoints:")
    for cp in s.get("checkpoints", []):
        lines.append("- timestamp: %r" % cp["timestamp"])
        lines.append("  source: %r" % cp["source"])
        lines.append("  verified_claims: []")
        lines.append("  unverified_claims: []")
        lines.append("  artifacts_touched: []")
        lines.append("  note: %r" % cp["note"])
    lines.append("verification_results: []")
    lines.append("tasks: []")
    lines.append("adrs_created: []")
    for k in ("closed_at", "end_commit", "documenter_decision", "session_note_path"):
        v = s.get(k)
        if v is None:
            lines.append(f"{k}: null")
        else:
            lines.append(f"{k}: {v!r}")
    return "\n".join(lines) + "\n"


def make_fixture() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="cortex-shots-"))
    dot = tmp / ".cortex"
    (dot / "sessions").mkdir(parents=True)
    (dot / "vault" / "decisions").mkdir(parents=True)
    (dot / "actions").mkdir(parents=True)
    (dot / "config.yaml").write_text(
        "episodic:\n  persist_dir: .memory/chroma\n  collection_name: cortex_episodic\n"
        "  embedding_model: all-MiniLM-L6-v2\n  embedding_backend: onnx\n"
        "semantic:\n  vault_path: vault\n",
        encoding="utf-8",
    )
    for i in range(1, 6):
        (dot / "vault" / "decisions" / f"ADR-{i:03d}.md").write_text(
            f"---\ntitle: ADR {i}\ndoc_type: adr\nstatus: accepted\n---\n\n#c\n",
            encoding="utf-8",
        )
    for s in SESSIONS:
        (dot / "sessions" / f"{s['session_id']}.yaml").write_text(
            session_yaml(s), encoding="utf-8"
        )
    (dot / "sessions" / "active.txt").write_text(SESSIONS[0]["session_id"] + "\n", encoding="utf-8")
    return tmp


def capture(screen: str, fixture: Path, extra: list[str] | None = None) -> str:
    cmd = [
        "cargo", "run", "-q", "-p", "cortex-tui", "--example", "capture", "--",
        screen, "--project-root", str(fixture),
    ] + (extra or [])
    out = subprocess.run(cmd, cwd=ROOT / "rust", capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stderr, file=sys.stderr)
        raise SystemExit(f"capture {screen} falló (rc {out.returncode})")
    return out.stdout


# ── rasterizador ANSI → PNG ─────────────────────────────────────────────────

SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")


def parse_ansi(text: str) -> list[list[tuple[str, tuple, tuple, bool]]]:
    """texto → grilla de celdas (char, fg, bg, bold)."""
    grid: list[list[tuple[str, tuple, tuple, bool]]] = []
    fg, bg, bold = None, None, False
    for line in text.splitlines():
        row: list[tuple[str, tuple, tuple, bool]] = []
        pos = 0
        for m in SGR_RE.finditer(line):
            if m.start() > pos:
                for ch in line[pos:m.start()]:
                    row.append((ch, fg, bg, bold))
            pos = m.end()
            code = m.group(1)
            if code in ("", "0"):
                fg, bg, bold = None, None, False
            else:
                parts = [int(x) for x in code.split(";")]
                if parts[0] == 1:
                    bold = True
                elif parts[0] == 38 and len(parts) >= 5:
                    fg = tuple(parts[2:5])
                elif parts[0] == 48 and len(parts) >= 5:
                    bg = tuple(parts[2:5])
        if pos < len(line):
            for ch in line[pos:]:
                row.append((ch, fg, bg, bold))
        grid.append(row)
    return grid


def find_font(bold: bool) -> str:
    for cand in FONT_CANDIDATES:
        is_bold = "Bold" in cand
        if is_bold == bold and os.path.exists(cand):
            return cand
    raise SystemExit("no se encontró una fuente mono (DejaVu/Liberation)")


def rasterize(ansi: str, out_png: Path, font_size: int = 13, pad: int = 12) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    grid = parse_ansi(ansi)
    rows = len(grid)
    cols = max(len(r) for r in grid) if grid else 0
    font = ImageFont.truetype(find_font(False), font_size)
    bold_font = ImageFont.truetype(find_font(True), font_size)
    # celda: ancho del 'M' + 1px de aire, alto del font.
    cw = int(font.getlength("M")) + 1
    ch = font.getmetrics()[0] + font.getmetrics()[1] + 2
    img = Image.new("RGB", (cols * cw + 2 * pad, rows * ch + 2 * pad), BG)
    d = ImageDraw.Draw(img)
    for y, row in enumerate(grid):
        for x, (sym, fg, bg, bold) in enumerate(row):
            px = pad + x * cw
            py = pad + y * ch
            if bg and bg != (0, 0, 0):
                d.rectangle([px, py, px + cw - 1, py + ch - 1], fill=bg)
            if sym == " ":
                continue
            f = bold_font if bold else font
            d.text((px, py - 2), sym, font=f, fill=fg or (0xD8, 0xDE, 0xE9))
    img.save(out_png)
    print(f"  {out_png.relative_to(ROOT)}  {img.size[0]}x{img.size[1]}")
    return out_png


# ── recetas de capturas ─────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--font-size", type=int, default=13)
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()

    if not args.no_build:
        subprocess.run(["cargo", "build", "-p", "cortex-tui", "--examples"],
                       cwd=ROOT / "rust", check=True, capture_output=True)

    fixture = make_fixture()
    print(f"fixture: {fixture}")
    try:
        # Splash: isotipo full + wordmark + tagline (100×30, truecolor).
        splash = subprocess.run(
            ["cargo", "run", "-q", "-p", "cortex-tui", "--example", "capture", "--",
             "splash", "--width", "100", "--height", "30"],
            cwd=ROOT / "rust", capture_output=True, text=True, check=True,
        ).stdout
        rasterize(splash, SHOTS / "splash-full.png", args.font_size)

        # Home REAL (snapshot del proyecto del fixture: sesión, acciones,
        # vault, salud — 80×24).
        home = subprocess.run(
            ["cargo", "run", "-q", "-p", "cortex-tui", "--example", "capture", "--",
             "home", "--width", "80", "--height", "24", "--project-root", str(fixture)],
            cwd=ROOT / "rust", capture_output=True, text=True, check=True,
        ).stdout
        rasterize(home, SHOTS / "home-es.png", args.font_size)

        # Sesiones con datos reales del fixture (100×14, selección en la segunda).
        sessions = subprocess.run(
            ["cargo", "run", "-q", "-p", "cortex-tui", "--example", "capture", "--",
             "sessions", "--width", "100", "--height", "14", "--project-root", str(fixture),
             "--select", "1"],
            cwd=ROOT / "rust", capture_output=True, text=True, check=True,
        ).stdout
        rasterize(sessions, SHOTS / "sessions-real.png", args.font_size)

        # Acciones: propuestas reales del motor + modal de revisión abierto.
        actions = capture("actions", fixture, ["--width", "100", "--height", "18",
                                                "--confirm", "0"])
        rasterize(actions, SHOTS / "action-engine.png", args.font_size)

        # Tabla del CLI (session list) sobre el mismo fixture.
        if not args.no_build:
            subprocess.run(["cargo", "build", "-q", "-p", "cortex-cli"],
                           cwd=ROOT / "rust", check=True, capture_output=True)
        lst = subprocess.run(
            [str(ROOT / "rust" / "target" / "debug" / "cortex-cli"), "session", "list",
             "--project-root", str(fixture)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
        rasterize(lst, SHOTS / "session-list.png", args.font_size)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


if __name__ == "__main__":
    main()