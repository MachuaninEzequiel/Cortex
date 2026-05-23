# Fase 06 — Sessions TUI con `rich` (`cortex session watch`)

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 04 (la primitiva Session debe estar completa) · **Bloquea:** Nada · **Esfuerzo estimado:** ~2 semanas

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 06 |
| Nombre | Sessions TUI con `rich` |
| Versión del plan | 1.0 |
| Dependencias | Fase 04 cerrada (Sessions completas, modos operativos). |
| Output principal | Comando `cortex session watch` con TUI viva de la(s) sesión(es) activa(s); modo `--watch` adicional para `cortex session show`. |
| Breaking changes | Ninguno. Sólo agrega comandos nuevos al subapp `session`. |

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) §5 (la Session primitive) y §9 (sesiones visibles).

### 1.2 Código existente que vas a tocar o necesitas conocer

Leé enteros:

- `cortex/cli/session.py` — el subapp `session` donde se agregan `watch` y `show --watch`.
- `cortex/session/service.py` — la API que la TUI consulta para refresh (`get_active`, `get`, `list`, `compute_diff`).
- `cortex/session/storage.py` — para entender el formato on-disk (la TUI puede pollear file mtimes o re-read directamente).
- `cortex/session/models.py` — `SessionRecord`, `Checkpoint`, `VerificationHookResult`.
- `cortex/documenter/interactive.py` — patrón de uso de `rich` (paneles, tablas, markdown). Re-usar helpers donde aplique.

Leé bajo demanda:

- Tests existentes que ejercitan `rich` en modo mock: `tests/unit/documenter/test_interactive.py` (cómo se construye `Console(file=StringIO(), force_terminal=False)`).

### 1.3 Documentación externa

- `rich.live.Live`: https://rich.readthedocs.io/en/stable/live.html — refresh dinámico de displays.
- `rich.layout.Layout`: https://rich.readthedocs.io/en/stable/layout.html — split panels horizontal/vertical.
- `rich.table.Table` + `rich.panel.Panel` + `rich.markdown.Markdown`: ya están en uso en `interactive.py`.
- `rich.console.Console.measure`: para terminales angostos.

NO usar:
- `textual` (sería dependencia nueva pesada — `rich` solo es suficiente).
- `prompt_toolkit` para keys (Fase 06 v1 no necesita keyboard interactivo).

---

## 2. Goal

Al finalizar esta fase:

1. **Existe `cortex session watch`** que abre una vista TUI viva con:
   - **Header**: nombre del proyecto, branch, modo Cortex (auto/interactive), número de sesiones OPEN.
   - **Active session panel**: id, status, mode (inferido), spec path, summary, branch, start commit (8 chars), opened-at relativo ("hace 2h 14m"), checkpoint count.
   - **Checkpoints panel**: tabla con los últimos N checkpoints (timestamp relativo, source, verified/unverified counts, note preview).
   - **Verification panel**: status de los hooks declarados en el spec (si la sesión ya corrió `cortex session verify`; sino, "pendientes").
   - **Recent sessions sidebar**: lista de las últimas 5-10 sesiones (closed/handoff/abandoned) con su mode y status.
   - **Footer / actions hint**: "Press Ctrl+C to quit. Use `cortex finish-session` to close.".
2. **`cortex session show --watch [SESSION_ID]`** abre la misma TUI pero focused en una sesión específica (o la activa si no se pasa id), refresh continuo.
3. **Refresh strategy**: cada 1.5s la TUI re-lee el storage. Detecta cambios por mtime de los YAML + `active.txt` (cheap polling). Re-renderiza si hubo cambios.
4. **Manejo de "sin sesión activa"**: el watch mode muestra una pantalla informativa ("No active session. Open one with `cortex create-spec`.") y sigue pollendo hasta que aparezca una.
5. **Cross-platform**: corre limpio en Windows (cmd.exe / Windows Terminal) y POSIX. Caracteres unicode/emoji funcionan; los fallbacks a ASCII se aplican solo si `console.encoding` no los soporta.
6. **Tests**: la TUI se ejercita con `Console(file=StringIO(), force_terminal=True, width=200)`. Snapshot/contains assertions sobre el output. Refresh logic se testea aislado (`_compute_layout` puro vs el loop de `Live`).
7. **Docs**: README + session-primitive.md actualizados.

**Lo que NO se hace en esta fase:**

- ❌ NO keyboard interactivo (q to quit, c to checkpoint inline, etc.). Sólo `Ctrl+C` para salir. **Razón:** keyboard interactivo cross-platform requiere `prompt_toolkit` o glue manual con `termios`/`msvcrt`. Out of scope para v1. Fase 06.1 (post-MVP) puede agregar.
- ❌ NO mouse / click handling.
- ❌ NO multi-pane resizable. La layout es fija con `rich.layout.Layout` y se adapta al ancho disponible.
- ❌ NO websocket-style streaming. El refresh es polling cada 1.5s — suficiente para un humano leyendo.
- ❌ NO modal views. Todo cabe en la layout principal. Si el diff es muy largo, se trunca con "(+N more lines)".

---

## 3. Decisiones de diseño clave

### 3.1 Layout

**Decisión:** layout fija de 3 columnas + header + footer, usando `rich.layout.Layout`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                            HEADER (1 row)                              │
│ project: Cortex · branch: feature/x · mode: auto · 1 OPEN · 3 closed   │
├──────────────────────┬──────────────────────────┬──────────────────────┤
│  ACTIVE SESSION      │      CHECKPOINTS         │  RECENT SESSIONS     │
│  (45% width)         │      (35% width)         │  (20% width)         │
│                      │                          │                      │
│ id: 2026-05-17_x     │ ts     source      file  │ id           status  │
│ status: OPEN         │ 2m ago manual      a.py  │ 2026-05-16   closed  │
│ mode: byo (inferred) │ 5m ago ide-hook    b.py  │ 2026-05-15   handoff │
│ spec: vault/.../x.md │ 12m... cortex-...  c.py  │ 2026-05-14   closed  │
│ summary: refactor    │                          │                      │
│ branch: feature/x    │ (2 of 4 checkpoints)     │ (+2 more)            │
│ opened: 2h 14m ago   │                          │                      │
│                      ├──────────────────────────┤                      │
│ VERIFICATION (3)     │  DIFF PREVIEW (truncated)│                      │
│ ✓ tests (5s)         │  diff --git a/src/x.py   │                      │
│ ✓ types (1s)         │  +def foo():             │                      │
│ ⏸ lint (not run)     │  +    return 42          │                      │
│                      │  (+15 more lines)        │                      │
├──────────────────────┴──────────────────────────┴──────────────────────┤
│ FOOTER · Refreshing every 1.5s · Ctrl+C to quit                        │
└────────────────────────────────────────────────────────────────────────┘
```

Detalles:
- Cuando la terminal es < 100 cols: collapsar a 2 columnas (sidebar derecha desaparece).
- Cuando es < 70 cols: stack vertical (panels apilados); el watch queda menos útil pero no roto.

### 3.2 Refresh strategy

**Decisión:** polling cada 1.5s con detección de cambios cheap.

Implementación:
1. Cada tick: leer mtime de `.cortex/sessions/active.txt` + mtime del YAML de la sesión activa.
2. Si ningún mtime cambió: solo re-render el "opened: X ago" timer (cosa cosmética). Esto es barato (sin I/O).
3. Si alguno cambió: re-leer el SessionRecord, re-correr `compute_diff`, re-render todo.
4. La sidebar (recent sessions) se refresca cada 10 ticks (~15s) — menor frecuencia, lower I/O cost.

Watchdog package: NO usarlo. Polling de 1-2 archivos cada 1.5s en POSIX/Windows es <1ms; agregar dep no vale la pena.

### 3.3 ¿Qué pasa si no hay sesión activa?

**Decisión:** la TUI no se cierra. Muestra una pantalla informativa:

```
┌──────────────────────────────────────────────────────────────┐
│                  NO ACTIVE SESSION                           │
│                                                              │
│  Open one with:                                              │
│    cortex create-spec --title "..." \                        │
│        --goal "..." --verification-hook 'name=t;command=...'│
│                                                              │
│  Or pick an existing one:                                    │
│    cortex session list                                       │
│    cortex session switch <ID>                                │
│                                                              │
│  Watching for a new session... (Ctrl+C to quit)              │
└──────────────────────────────────────────────────────────────┘
```

Sigue polling. Cuando aparezca una sesión activa, transiciona automáticamente al layout principal.

### 3.4 Manejo de Ctrl+C

**Decisión:** capturar `KeyboardInterrupt`, llamar a `live.stop()`, imprimir un mensaje de cierre limpio (`✓ Session watch stopped. Session is still OPEN.`), y `sys.exit(0)`. Sin traceback.

### 3.5 Encoding fallback (Windows)

**Decisión:** detectar `console.encoding` al inicio. Si no soporta unicode (`cp1252` u otro ASCII-only), reemplazar emojis con texto:

| Emoji preferido | Fallback ASCII |
|---|---|
| ✓ | `OK` |
| ✗ | `FAIL` |
| ⏸ | `pend.` |
| ⚠ | `warn` |
| › / › | `>` |

Helper: `cortex/cli/_unicode_fallback.py` con `glyph(name)` que devuelve la versión correcta. Reutilizable por otros comandos en el futuro.

### 3.6 Pure render vs IO

**Decisión:** separar el código en:
- `cortex/cli/session_tui.py::SessionTuiState` — dataclass con todo lo necesario para render (frozen, snapshot).
- `cortex/cli/session_tui.py::render_layout(state) -> Layout` — función pura. **Testeable sin TTY**.
- `cortex/cli/session_tui.py::run_tui(service, refresh_interval)` — el loop con `rich.live.Live`. NO testeado unitario; smoke test E2E.

Esto sigue el patrón de `cortex/documenter/interactive.py`: render puro + state machine separados del Live loop.

---

## 4. Task Breakdown

### T6.1 — Scaffold del módulo + entry point CLI

**Objetivo:** estructura inicial del comando `cortex session watch`.

**Archivos a crear:**
- `cortex/cli/session_tui.py` (esqueleto)
- `cortex/cli/_unicode_fallback.py` (helper para Windows)

**Archivos a modificar:**
- `cortex/cli/session.py` — agregar el comando `watch`.

**API esperada en `session_tui.py`:**

```python
from dataclasses import dataclass
from rich.layout import Layout
from rich.console import Console

@dataclass(frozen=True)
class SessionTuiState:
    """Snapshot of everything needed to render the TUI."""
    active_session: SessionRecord | None
    recent_sessions: list[SessionRecord]   # last 5-10
    diff_preview: str                       # truncated
    verification_summary: list[tuple[str, str]]  # (hook_name, status_glyph + label)
    refresh_tick: int                       # for "X ago" timestamps
    repo_root: Path
    project_name: str
    branch: str
    documenter_mode: str                    # auto|interactive

def render_layout(state: SessionTuiState, *, max_width: int) -> Layout:
    """Pure function: state → rich.Layout. Testable without TTY."""
    ...

def run_tui(
    service: SessionService,
    *,
    project_root: Path,
    refresh_interval: float = 1.5,
    console: Console | None = None,
    focus_session_id: str | None = None,
) -> None:
    """Main loop. Catches KeyboardInterrupt."""
    ...
```

**En `cortex/cli/session.py`:**

```python
@session_app.command("watch")
def watch_command(
    session_id: str | None = typer.Argument(
        None, help="Optional session id to focus on (defaults to active)."
    ),
    refresh: float = typer.Option(
        1.5, "--refresh", help="Refresh interval in seconds (min 0.5, max 30)."
    ),
    project_root: Path | None = typer.Option(None, "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    """Open a live TUI view of the active (or named) session."""
    if not (0.5 <= refresh <= 30):
        _error_exit("--refresh must be between 0.5 and 30 seconds.")
    service = _build_service(project_root)
    from cortex.cli.session_tui import run_tui
    run_tui(service, project_root=project_root or Path.cwd(), refresh_interval=refresh, focus_session_id=session_id)
```

Y agregar también el flag `--watch` al comando `show`:

```python
@session_app.command("show")
def show_command(
    session_id: str | None = typer.Argument(None, ...),
    watch: bool = typer.Option(False, "--watch", help="Open live TUI watch mode."),
    ...
) -> None:
    if watch:
        # Delegate to the TUI focused on this session
        from cortex.cli.session_tui import run_tui
        run_tui(_build_service(project_root), ..., focus_session_id=session_id)
        return
    # ... existing static show logic ...
```

**Definition of Done T6.1:**
- `cortex session watch --help` muestra la doc.
- `cortex session watch` invocado sin sesión activa muestra el placeholder y sale con Ctrl+C limpio.

---

### T6.2 — Render layout: header + footer + skeleton de panels

**Archivos a modificar:**
- `cortex/cli/session_tui.py` — implementar `render_layout` con la layout vacía (panels con "TODO" content).

**Detalles:**

```python
def render_layout(state: SessionTuiState, *, max_width: int) -> Layout:
    layout = Layout()
    layout.split(
        Layout(name="header", size=1),
        Layout(name="body"),
        Layout(name="footer", size=1),
    )

    if max_width >= 100:
        layout["body"].split_row(
            Layout(name="left", ratio=45),
            Layout(name="center", ratio=35),
            Layout(name="right", ratio=20),
        )
    elif max_width >= 70:
        layout["body"].split_row(
            Layout(name="left", ratio=55),
            Layout(name="center", ratio=45),
        )
    else:
        layout["body"].split_column(
            Layout(name="left"),
            Layout(name="center"),
        )

    layout["header"].update(_render_header(state))
    layout["footer"].update(_render_footer(state))
    layout["body"]["left"].update(_render_active_session_panel(state))
    layout["body"]["center"].update(_render_checkpoints_panel(state))
    if "right" in layout["body"]._children:
        layout["body"]["right"].update(_render_recent_sessions_panel(state))
    return layout
```

**Definition of Done T6.2:**
- Función `render_layout` retorna un `Layout` válido en los 3 modos de ancho.
- Tests unitarios snapshot básicos (assert que el output contiene "ACTIVE SESSION", "CHECKPOINTS", "RECENT SESSIONS" en 100 cols; ausencia del último en 80 cols).

---

### T6.3 — Active session panel completo

**Archivos a modificar:**
- `cortex/cli/session_tui.py::_render_active_session_panel`

**Contenido del panel (cuando hay sesión activa):**

```
┌─ ACTIVE SESSION ──────────────────────────────────────┐
│ id      : 2026-05-17_jwt-refresh                      │
│ status  : OPEN                                        │
│ mode    : byo (inferred)                              │
│ spec    : vault/specs/2026-05-17_jwt-refresh.md       │
│ summary : Implement JWT refresh tokens with rotation  │
│ branch  : feature/jwt-refresh                         │
│ start   : abc123de                                    │
│ opened  : 2h 14m ago                                  │
│                                                       │
│ ── verification (3) ──                                │
│ ✓ tests       (5.2s, last run 12m ago)                │
│ ✓ types       (0.8s, last run 12m ago)                │
│ ⏸ lint        (not yet run)                           │
└───────────────────────────────────────────────────────┘
```

Helpers:
- `_format_relative(ts: datetime) -> str` — "5m ago", "2h 14m ago", "1d 4h ago", "5s ago", "just now". Implementación inline (no usar `humanize` package).
- `_verification_glyph(result) -> str` — `✓` / `✗` / `⏸` (con fallback ASCII).
- `_format_duration_ms(ms: int) -> str` — `"5.2s"`, `"824ms"`, `"2m 4s"`.

**Cuando NO hay sesión activa:** el panel muestra el placeholder de §3.3.

**Definition of Done T6.3:** panel renderiza correctamente con datos reales; tests con session de fixture verifican que el output contiene los datos esperados.

---

### T6.4 — Checkpoints panel + diff preview

**Archivos a modificar:**
- `cortex/cli/session_tui.py::_render_checkpoints_panel`
- `cortex/cli/session_tui.py::_render_diff_panel`

**Decisión visual:** el centro de la layout es vertical-split de 2 sub-panels: checkpoints arriba, diff preview abajo. Ratio 60/40.

**Checkpoints panel** (tabla `rich.Table`):

```
┌─ CHECKPOINTS (4) ──────────────────────────────────┐
│ TIME       SOURCE              VERIF  FILES  NOTE  │
│ 2m ago     cortex-SDDwork       ✓ 2   src/x.py    │
│ 8m ago     ide-hook              0   src/y.py    │
│            cortex-code-impl     ✓ 1   src/x,y.py │
│ 18m ago    manual                0   —          ttl │
│ 25m ago    cortex-sync          ✓ 1   —          init │
└────────────────────────────────────────────────────┘
```

- Muestra los últimos 5 checkpoints (más recientes arriba). Si hay más: footer "(+N earlier)".
- Si una columna es muy angosta, truncar con `…`.

**Diff preview panel** (`rich.Syntax` para colorear, o un `Panel` con texto monoespacio):

```
┌─ DIFF PREVIEW ─────────────────────────────────────┐
│ diff --git a/src/x.py b/src/x.py                   │
│ +def jwt_refresh(token):                           │
│ +    if expired(token):                            │
│ +        return rotate(token)                      │
│ -def old_legacy_refresh(): pass                    │
│ (+ 23 more lines)                                  │
└────────────────────────────────────────────────────┘
```

- Mostrar máximo 8 lines (configurable).
- Si la sesión está cerrada: usar end_commit; si OPEN: HEAD.
- Si `compute_diff` falla (git error): mostrar `"(diff unavailable: <error>)"`.

**Definition of Done T6.4:** ambos panels renderizan con datos reales; truncation funciona; tests con fixture cubren ambos.

---

### T6.5 — Recent sessions sidebar

**Archivos a modificar:**
- `cortex/cli/session_tui.py::_render_recent_sessions_panel`

**Contenido:**

```
┌─ RECENT SESSIONS ──────────┐
│ STATUS     AGE      ID     │
│ ▶ open     2h14m    2026-…jwt-refresh │
│ closed     9h ago   2026-…dashboard   │
│ handoff    1d ago   2026-…parser-fix  │
│ closed     2d ago   2026-…ui-cleanup  │
│ closed     3d ago   2026-…tests-perf  │
│                            │
│ (+ 12 more — see `list`)   │
└────────────────────────────┘
```

Detalles:
- La fila activa se prefija con `▶` y se renderiza en bold.
- `_format_relative` reutilizado.
- Máximo 5-7 sesiones visibles. El resto: footer "(+N more — see `list`)".
- En ancho < 100 (cuando el panel está oculto): este código no se invoca.

**Definition of Done T6.5:** sidebar renderiza correctamente; el separador activa-vs-resto es obvio visualmente.

---

### T6.6 — Header + footer

**Archivos a modificar:**
- `cortex/cli/session_tui.py::_render_header`
- `cortex/cli/session_tui.py::_render_footer`

**Header (1 línea):**

```
cortex · feature/jwt-refresh · documenter: auto · 1 open · 12 closed       refreshed: 14:32:11
```

- Project name: nombre del directorio del repo (`layout.repo_root.name`).
- Branch: `git.get_current_branch(repo_root)`. Si git falla: `"<no git>"`.
- Documenter mode: lee del config (`config.documenter.default_mode`).
- Conteos de sesiones: cheap (`len(storage.list_by_status(OPEN))`, etc.).
- Refresh timestamp: tiempo del último re-read, formato HH:MM:SS.

**Footer (1 línea):**

```
Watching · refresh every 1.5s · Ctrl+C to quit · Use `cortex finish-session` to close.
```

Si `--refresh` se configuró custom, mostrar ese número.

**Definition of Done T6.6:** header + footer renderizan en 1 línea; truncan elegantemente en terminales angostos.

---

### T6.7 — Refresh loop + file watching

**Archivos a modificar:**
- `cortex/cli/session_tui.py::run_tui`

**Implementación:**

```python
def run_tui(service, *, project_root, refresh_interval=1.5, console=None, focus_session_id=None):
    console = console or Console()
    state = _build_initial_state(service, project_root, focus_session_id)
    last_active_pointer_mtime = _safe_mtime(service._storage._active_pointer_path)
    last_session_mtimes: dict[str, float] = {}

    try:
        with Live(render_layout(state, max_width=console.width), console=console, refresh_per_second=4) as live:
            tick = 0
            while True:
                time.sleep(refresh_interval)
                tick += 1
                changed = _detect_changes(service, last_active_pointer_mtime, last_session_mtimes)
                if changed or tick % 10 == 0:
                    state = _build_state(service, project_root, focus_session_id, refresh_tick=tick)
                    last_active_pointer_mtime = _safe_mtime(service._storage._active_pointer_path)
                    last_session_mtimes = _snapshot_session_mtimes(service)
                # Always re-render to update "X ago" timestamps and refresh-time
                live.update(render_layout(state, max_width=console.width))
    except KeyboardInterrupt:
        console.print("\n[dim]✓ Session watch stopped. Session is still OPEN.[/dim]")
        raise typer.Exit(0)
```

Helpers necesarios:
- `_safe_mtime(path: Path) -> float | None` — return mtime or None if missing.
- `_detect_changes(service, prev_active_mtime, prev_session_mtimes) -> bool` — compare current mtimes against snapshot.
- `_snapshot_session_mtimes(service) -> dict[str, float]` — snapshot all session YAML mtimes.

**Definition of Done T6.7:** TUI se mantiene corriendo; cambios externos (otro proceso modifica la session) son visibles dentro de 1.5s; Ctrl+C sale limpio.

---

### T6.8 — Encoding fallback helper

**Archivos a crear:**
- `cortex/cli/_unicode_fallback.py`

**API:**

```python
"""Cross-platform glyph helpers — fallback to ASCII when console can't render unicode."""

_UNICODE_GLYPHS = {
    "check": "✓",
    "fail": "✗",
    "pending": "⏸",
    "warn": "⚠",
    "arrow_right": "▶",
    "ellipsis": "…",
}

_ASCII_FALLBACK = {
    "check": "OK",
    "fail": "FAIL",
    "pending": "...",
    "warn": "!",
    "arrow_right": ">",
    "ellipsis": "...",
}

def glyph(name: str, *, console: Console) -> str:
    """Return the unicode glyph or its ASCII fallback based on console encoding."""
    if _supports_unicode(console):
        return _UNICODE_GLYPHS.get(name, "")
    return _ASCII_FALLBACK.get(name, "")

def _supports_unicode(console: Console) -> bool:
    encoding = (getattr(console.file, "encoding", "") or "").lower()
    return any(token in encoding for token in ("utf", "unicode"))
```

**Tests unitarios:**

```python
def test_glyph_unicode_console_returns_unicode(): ...
def test_glyph_cp1252_console_returns_ascii(): ...
def test_glyph_unknown_name_returns_empty_string(): ...
```

**Definition of Done T6.8:** helper testeado, usado por todos los `_render_*` panels.

---

### T6.9 — Tests unitarios del módulo

**Archivos a crear:**
- `tests/unit/cli/test_session_tui.py`

**Estructura mínima (15-20 tests):**

```python
class TestRenderLayoutNoSession:
    def test_shows_no_active_session_message(self): ...
    def test_no_session_works_in_narrow_terminal(self): ...

class TestRenderLayoutWithSession:
    def test_panels_present_at_full_width(self, fixture_state): ...
    def test_sidebar_hidden_at_medium_width(self, fixture_state): ...
    def test_stacked_at_narrow_width(self, fixture_state): ...
    def test_active_panel_includes_session_id(self, ...): ...
    def test_active_panel_includes_relative_open_time(self, ...): ...
    def test_checkpoints_table_lists_recent_first(self, ...): ...
    def test_diff_preview_truncates_long_diffs(self, ...): ...
    def test_recent_sessions_marks_active_with_arrow(self, ...): ...

class TestRelativeTimeFormatter:
    def test_seconds_ago(self): ...
    def test_minutes_ago(self): ...
    def test_hours_minutes_ago(self): ...
    def test_days_hours_ago(self): ...
    def test_just_now(self): ...

class TestUnicodeFallback:
    def test_glyph_unicode_console(self): ...
    def test_glyph_cp1252_fallback(self): ...

class TestHeaderFooter:
    def test_header_includes_branch(self): ...
    def test_footer_includes_refresh_interval(self): ...
    def test_header_handles_no_git(self): ...
```

Setup pattern: `Console(file=StringIO(), force_terminal=True, width=200)`, then `console.print(render_layout(state, max_width=200))`, then assert sobre el `getvalue()`.

**Definition of Done T6.9:** 15+ tests, todos verdes. Coverage de `cortex/cli/session_tui.py` y `cortex/cli/_unicode_fallback.py` > 85%.

---

### T6.10 — E2E smoke test del comando

**Archivos a crear:**
- `tests/e2e/test_session_tui_smoke.py`

**Escenarios:**

```python
@pytest.mark.e2e
class TestSessionWatchSmoke:
    def test_watch_with_no_active_session_renders_placeholder(self, tmp_cortex_repo):
        """Run `cortex session watch` for 2 seconds, capture stdout, assert placeholder."""
        # Use subprocess.Popen + send SIGINT after 2s

    def test_watch_with_active_session_renders_layout(self, tmp_cortex_repo_with_session):
        """Same as above but with an active session — assert layout panels visible."""

    def test_watch_detects_new_checkpoint_within_3s(self, tmp_cortex_repo_with_session):
        """Run watch, append a checkpoint externally, assert TUI re-renders with the new checkpoint."""
```

**Helper:** un `subprocess_with_sigint` que lanza `cortex session watch` con timeout, captura stdout, envía SIGINT, recoge output.

**Definition of Done T6.10:** 3 escenarios pasan; tolerantes a ~1s de jitter.

---

### T6.11 — `cortex session show --watch` (variant)

**Archivos a modificar:**
- `cortex/cli/session.py::show_command` — agregar flag `--watch`.

**Comportamiento:**
- Sin `--watch`: comportamiento actual (snapshot estático).
- Con `--watch`: invoca `run_tui` con `focus_session_id=session_id`.
- Si `session_id` es None: equivalente a `cortex session watch` sin argumentos.

**Tests:** un test CLI con CliRunner que verifica que `--watch` invoca la TUI (mock de `run_tui`).

**Definition of Done T6.11:** comando funciona, test verde.

---

### T6.12 — Documentación

**Archivos a modificar:**
1. `README.md` §"Comandos Sessions" — agregar `cortex session watch` y mencionar `cortex session show --watch`.
2. `docs/architecture/session-primitive.md` §5 (CLI) — agregar fila a la tabla.
3. `docs/architecture/pluggable-middle-overview.md` §9 — mencionar `watch` en diagnostics.
4. `docs/pluggable-middle/README.md` — marcar Fase 06 ✅.

**Contenido nuevo en README:**

```markdown
| `cortex session watch [ID] [--refresh 1.5]` | **TUI viva** (Fase 06): refresca la sesión activa (o la indicada) cada N segundos. Muestra checkpoints, diff preview, verification status, recent sessions. Ctrl+C para salir. |
| `cortex session show <ID> --watch` | Alias del anterior pero focused en una sesión específica. |
```

Sección visual con un mockup ASCII (puede tomar el de §3.1).

**Definition of Done T6.12:** docs actualizadas; el mockup ASCII se ve bien renderizado en GitHub markdown viewer.

---

## 5. Cross-cutting concerns

### 5.1 Performance

- Cada tick (1.5s) ejecuta `os.stat()` sobre 2-3 archivos en el caso happy. <1ms total.
- Cuando hay un cambio: `storage.load()` un YAML (<10KB) + `git diff` (cacheable en el SessionStorage o invocado fresco). Total <50ms.
- Sidebar: refresh cada 10 ticks → impacto despreciable.
- **No hilos.** Single-threaded polling loop.

### 5.2 Logging

- `cortex session watch` NO debe escribir logs a stdout/stderr durante el watch (rompe la TUI). Configurar logger a NullHandler durante el loop, restore al salir.
- Errors: si `service.list()` falla durante un refresh, render el panel con `"(error: <e>)"` en lugar de crashear.

### 5.3 Multi-process safety

- La TUI sólo lee del storage. NUNCA escribe.
- Si otro proceso (e.g. un hook IDE) escribe un nuevo checkpoint mientras la TUI está leyendo, la atomicidad de `SessionStorage.save` (write-tmp + rename) garantiza que el lector ve siempre estado consistente.

### 5.4 Cross-platform

- Windows: confirmar que `rich.live.Live` con `screen=False` no rompe en cmd.exe. Si rompe, fallback a `screen=True` (alternate screen buffer).
- Terminales sin TTY (e.g. pipe a `less`): `cortex session watch` detecta `not console.is_terminal` y emite un error claro: `"watch requires an interactive terminal; redirect to a file or use `cortex session show` for snapshot output."`.

### 5.5 Coordinación con fases futuras

- **El campo `mode` se renderiza como string genérico** (`session.mode.value`). Cualquier valor adicional del enum (e.g. `ci-review` que Fase 07 Nivel 3 introduce, u otros futuros) **NO requiere cambios al código de la TUI** — aparece automáticamente.
- **Tasks granulares (Fase 09)** y **quality gate status en checkpoints (Fase 08)** son intencionalmente fuera del scope de la TUI v1. Si esas fases entregan después, **una iteración post-MVP de la TUI** puede sumar paneles dedicados. No tocar la TUI v1 para soportar tasks/quality-gates anticipadamente.

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Tests
pytest tests/unit/cli/test_session_tui.py tests/e2e/test_session_tui_smoke.py --no-cov -v
# expected: all green

# 2. mypy + ruff
mypy --strict --follow-imports=silent cortex/cli/session_tui.py cortex/cli/_unicode_fallback.py
ruff check cortex/cli/session_tui.py cortex/cli/_unicode_fallback.py tests/unit/cli/test_session_tui.py
# expected: clean

# 3. CLI smoke (en un repo con cortex configurado y sesión activa)
cortex session watch &
WATCH_PID=$!
sleep 3
kill -INT $WATCH_PID
# expected: TUI corre 3s, exits cleanly on SIGINT

# 4. Manual smoke en Windows Terminal + cmd.exe
# Verificar: emojis visibles en WT; fallback ASCII en cmd.exe legacy
cortex session watch

# 5. Smoke con cambio externo
# Term 1: cortex session watch
# Term 2: cortex session checkpoint --source manual --note "from term 2"
# Expected: Term 1 muestra el nuevo checkpoint dentro de ~1.5s
```

---

## 7. Handoff to next phase

Al cerrar Fase 06:

### Artefactos producidos

| Artefacto | Path |
|---|---|
| TUI module | `cortex/cli/session_tui.py` |
| Unicode fallback helper | `cortex/cli/_unicode_fallback.py` |
| CLI commands | `cortex session watch`, `cortex session show --watch` |
| Tests | `tests/unit/cli/test_session_tui.py`, `tests/e2e/test_session_tui_smoke.py` |
| Docs | README §"Comandos Sessions"; session-primitive.md §5; overview §9 |

### Lo que el resto del ecosistema gana

- Visibilidad en tiempo real para usuarios que dejan corriendo `cortex session watch` mientras trabajan en otro IDE / agente externo.
- Ya no es necesario re-correr `cortex session show <ID>` manualmente.
- Las ideas post-MVP (keyboard interactivo, mouse, multi-session panels) ahora tienen un punto de extensión claro.

---

## 8. Progress Log

- [x] T6.1 — Scaffold del módulo + entry point CLI (2026-05-17)
- [x] T6.2 — Render layout: header + footer + skeleton de panels (2026-05-17)
- [x] T6.3 — Active session panel completo (2026-05-17)
- [x] T6.4 — Checkpoints panel + diff preview (2026-05-17)
- [x] T6.5 — Recent sessions sidebar (2026-05-17)
- [x] T6.6 — Header + footer (2026-05-17)
- [x] T6.7 — Refresh loop + file watching (2026-05-17)
- [x] T6.8 — Encoding fallback helper (2026-05-17) — `cortex/cli/_unicode_fallback.py` con `glyph()` + `supports_unicode()`. Cubre `cmd.exe` legacy / cp1252.
- [x] T6.9 — Tests unitarios (2026-05-17) — 42 tests en `tests/unit/cli/test_session_tui.py` + `test_unicode_fallback.py`. Cubre format helpers, layout en 3 anchos, paneles individuales, edge cases.
- [x] T6.10 — E2E smoke test (2026-05-17) — `tests/e2e/test_session_tui_smoke.py`: no-TTY exit (cross-platform) + subprocess SIGINT (POSIX/Windows con CTRL_BREAK_EVENT).
- [x] T6.11 — `cortex session show --watch` variant (2026-05-17) — flag agregada al `show_command` que delega al mismo `_run_watch_tui`.
- [x] T6.12 — Documentación (2026-05-17) — README §Comandos Sessions, `session-primitive.md` §5, `pluggable-middle-overview.md` §9, `pluggable-middle/README.md` marca Fase 06 ✅.
- [x] Completion Verification Commands pasan (2026-05-17) — Suite completa verde (1779 + 44 = 1823 passed). mypy strict + ruff clean en módulos nuevos.
- [x] Tabla `../README.md` actualizada ✅ (2026-05-17)
- [ ] Commit final (pendiente — esperando autorización del usuario al cierre de todas las fases)

---

## 9. Notas para el agente ejecutor

- **Priorizá el visual.** Esta fase NO es funcionalidad — el usuario ya tiene `cortex session show` para info. La TUI vende **calidad de presentación**. Si una columna queda mal alineada, una fila trunca a mitad de palabra, o un emoji rompe en Windows, **arreglalo antes de pasar a la siguiente task**.
- **Separá render puro vs loop.** El `Live` loop es difícil de testear; las funciones `_render_*` son puras y triviales. Mantén esa separación o la cobertura colapsa.
- **Probá en terminales reales** además de los unit tests:
  - VSCode terminal integrado.
  - Windows Terminal (WT).
  - cmd.exe legacy (sin unicode).
  - macOS Terminal / iTerm2 si tenés acceso.
  - tmux/screen para asegurarse que `Live` no rompe.
- **Refresh interval default 1.5s.** Más rápido es flicker visual. Más lento es laggy. No tocar sin razón.
- **No metas keyboard interactivo en v1.** Si te tienta, anota la idea en post-MVP roadmap. La complejidad de `prompt_toolkit` o `termios`/`msvcrt` no vale el ROI inicial.
- **El "no active session" placeholder importa.** Es lo primero que ve un usuario nuevo. Mantenelo amigable, con comandos de copy-paste listos.
