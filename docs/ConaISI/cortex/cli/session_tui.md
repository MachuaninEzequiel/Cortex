# cortex/cli/session_tui.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/session_tui.py` (735 líneas).
- **Módulo Python:** `cortex.cli.session_tui`.
- **Docstring del módulo:** ``cortex session watch`` — live TUI for the Session primitive.
- **Clases definidas:**
  - `SessionTuiState`
    - Immutable snapshot the renderer consumes.
- **Funciones de módulo:**
  - `_format_relative(then)` — Return a short relative-time string for ``then``.
  - `_format_duration_ms(ms)` — Format a duration in ms as ``"824ms"``, ``"5.2s"`` or ``"2m 4s"``.
  - `_safe_mtime(path)` — Return ``path.stat().st_mtime`` or None when the path is missing.
  - `_truncate(text, length)` — Truncate to ``length`` characters, append an ellipsis when cut.
  - `_verification_status_label(result)` — Return ``"✓ name (5.2s)"`` style label for a verification result.
  - `_render_header(state)` — One-line top banner: project · branch · mode · counts · refreshed.
  - `_render_footer(state)` — One-line bottom hint: refresh interval + how to quit.
  - `_render_no_active_session_panel(state)` — Placeholder when there is no active Session yet.
  - `_render_active_session_panel(state)` — Identity + opened_at + verification status block for the active session.
  - `_checkpoint_row(cp)` — Build one row for the checkpoints table.
  - `_render_checkpoints_panel(state)` — Table of the most recent checkpoints (newest first).
  - `_render_diff_panel(state)` — Truncated diff preview (first N lines + "more" footer).
  - `_render_recent_sessions_panel(state)` — Sidebar with the last few sessions, active row highlighted.
  - `render_layout(state)` — Build the full ``rich.Layout`` for the given state.
  - `_build_state(service)` — Snapshot everything the renderer needs at this tick.
  - `_snapshot_session_mtimes(service)` — Map session_id → mtime of its YAML file.
  - `_detect_changes(service)` — Return ``(changed, new_active_mtime, new_session_mtimes)``.
  - `_resolve_documenter_mode(project_root)` — Best-effort lookup of ``documenter.default_mode`` in the project config.
  - `run_tui(service)` — Run the live TUI loop until the user presses Ctrl+C.
- **Constantes / símbolos de módulo:** `_DIFF_PREVIEW_MAX_LINES`, `_CHECKPOINTS_VISIBLE`, `_RECENT_SIDEBAR_VISIBLE`, `_SIDEBAR_REFRESH_EVERY`, `_NOTE_PREVIEW_CHARS`, `_BREAKPOINT_FULL`, `_BREAKPOINT_MEDIUM`, `__all__`

## Para qué sirve

``cortex session watch`` — live TUI for the Session primitive.

Phase 06 of the Pluggable Middle architecture. The TUI is **read-only**:
it polls ``.cortex/sessions/`` every ``refresh_interval`` seconds and
re-renders a ``rich.Layout`` with the active session, recent
checkpoints, a truncated diff preview, the verification summary, and a
sidebar with recent sessions. ``Ctrl+C`` exits cleanly.

Design:
    * :class:`SessionTuiState` is a frozen snapshot. The renderer is a
      **pure function** ``state → rich.Layout`` so it can be unit-tested
      against ``Console(file=StringIO(), force_terminal=True, …)``
      without spinning up a TTY.
    * :func:`run_tui` is the live loop. It is **not** unit-tested —
      ``tests/e2e/test_session_tui_smoke.py`` covers the subprocess
      behaviour end-to-end.
    * No threads. Single-threaded polling at 1.5s by default. No mouse,
      no keyboard input. Out of scope for v1 (see the phase plan §2).
    * Layout breakpoints: ≥ 100 cols full 3-column layout; ≥ 70 cols
      2-column (sidebar dropped); else vertical stack.
    * Glyphs route through :mod:`cortex.cli._unicode_fallback` so the
      TUI degrades gracefully on legacy Windows consoles.

## Relaciones

### Recibe de

- `cortex.cli._unicode_fallback` (glyph)
- `cortex.session` (git)
- `cortex.session.models` (SessionMode, SessionRecord, SessionStatus, VerificationHookResult)
- `cortex.session.service` (SessionService)
- Dependencias externas/stdlib: `logging`, `time`, `typer`, `__future__`, `dataclasses`, `datetime`, `pathlib`, `typing`, `rich.console`, `rich.layout`, `rich.live`, `rich.panel`, `rich.table`, `rich.text`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 735.
Docstrings de símbolos públicos:
- `render_layout`: Build the full ``rich.Layout`` for the given state.
- `run_tui`: Run the live TUI loop until the user presses Ctrl+C.

---
Fuente: código de `cortex/cli/session_tui.py` (AST + grafo de imports internos). No se usó documentación previa.
