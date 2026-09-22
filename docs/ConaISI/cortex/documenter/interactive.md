# cortex/documenter/interactive.py

## Qué tiene adentro

- **Ruta de código:** `cortex/documenter/interactive.py` (343 líneas).
- **Módulo Python:** `cortex.documenter.interactive`.
- **Docstring del módulo:** cortex.documenter.interactive — Interactive prompt UX for ``finish-session``.
- **Clases definidas:**
  - `InteractiveAction` (StrEnum)
    - Top-level decision the user makes at the interactive prompt.
  - `InteractiveResult`
    - Outcome of one :meth:`InteractiveSession.prompt` invocation.
    - Métodos públicos/especiales: `cancelled`
  - `InteractiveSession`
    - Drive the interactive finish-session prompt loop.
    - Métodos públicos/especiales: `__init__`, `prompt`
    - Métodos internos: `_render`, `_ask_main_action`, `_ask_main_action_after_edit`, `_ask_handoff_reason`, `_maybe_edit_title`, `_maybe_edit_body`, `_review_adrs`, `_seed_body_for_editor`
- **Funciones de módulo:**
  - `_render_summary_panel(reconstruction)`
  - `_render_draft_panel(reconstruction)` — Render the would-be session note body as Markdown inside a Panel.
  - `_render_adr_panel(reconstruction)`
  - `_render_actions_panel()`
- **Constantes / símbolos de módulo:** `_MAIN_ACTION_KEYS`, `_AFTER_EDIT_KEYS`, `__all__`

## Para qué sirve

cortex.documenter.interactive — Interactive prompt UX for ``finish-session``.

Phase 04 (T4.1) of the Pluggable Middle architecture: when the user runs
``cortex finish-session --interactive`` (or sets ``documenter.default_mode:
interactive`` in ``config.yaml``), the documenter renders the
reconstruction output with :mod:`rich`, surfaces ADR suggestions one by
one, and waits for the user's verdict before persisting anything.

Design:
    * UI rendering lives behind narrow methods on :class:`InteractiveSession`
      so tests can stub them out and exercise the state machine in
      isolation.
    * Actual user input goes through ``console.input`` and
      :func:`click.edit` (for the multi-line body editor), both of which
      are trivially monkeypatchable in tests.
    * The state machine emits a single :class:`InteractiveResult`. The
      caller (``cortex finish-session``) translates that into a
      :class:`cortex.documenter.persistence.FinishOverrides` and either
      invokes the persister or leaves the session OPEN (on cancel).

## Relaciones

### Recibe de

- `cortex.session.models` (SessionStatus)
- Dependencias externas/stdlib: `click`, `__future__`, `collections.abc`, `dataclasses`, `enum`, `typing`, `rich.console`, `rich.markdown`, `rich.panel`, `rich.table`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 343.
Docstrings de símbolos públicos:
- `InteractiveSession.prompt`: Render the reconstruction and capture the user's verdict.

---
Fuente: código de `cortex/documenter/interactive.py` (AST + grafo de imports internos). No se usó documentación previa.
