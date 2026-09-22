# cortex/session/hooks/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/__init__.py` (43 líneas).
- **Módulo Python:** `cortex.session.hooks`.
- **Docstring del módulo:** cortex.session.hooks — IDE-hook installer system for the Observed mode.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.session.hooks — IDE-hook installer system for the Observed mode.

Phase 03 (T3.6–T3.10) of the Pluggable Middle architecture introduces
*Observed mode*: the user works with their IDE of choice, and an IDE
hook automatically emits ``cortex session checkpoint`` events so that
the documenter can later reconstruct context from a session enriched
with real-world activity.

Public API:
    :class:`HookAdapter`     — Protocol every IDE adapter implements.
    :class:`HookInstaller`   — orchestrator with a registry of adapters.
    :class:`InstallResult`   — outcome of an install operation.
    :class:`UninstallResult` — outcome of an uninstall operation.
    :class:`HookStatus`      — current installed/not-installed state.
    :func:`default_installer` — factory that wires the bundled adapters
                                (Claude Code, Cursor, Pi).

The installer NEVER writes outside ``target_dir`` (project root or user
config dir, depending on the caller's choice). All operations are
designed to be safe to re-run: ``install`` is idempotent, ``uninstall``
is a no-op if nothing is installed.

## Relaciones

### Recibe de

- `cortex.session.hooks.installer` (HookAdapter, HookInstaller, HookStatus, InstallResult, UninstallResult, default_installer)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.autopilot.doctor`
- `cortex.cli.ide`
- `cortex.cli.session`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 43.
Reexportes observados:
- cortex.session.hooks.installer: HookAdapter, HookInstaller, HookStatus, InstallResult, UninstallResult, default_installer

---
Fuente: código de `cortex/session/hooks/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
