# cortex/session/hooks/adapters/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/adapters/__init__.py` (17 líneas).
- **Módulo Python:** `cortex.session.hooks.adapters`.
- **Docstring del módulo:** cortex.session.hooks.adapters — Bundled IDE hook adapters.

## Para qué sirve

cortex.session.hooks.adapters — Bundled IDE hook adapters.

Each module here implements :class:`cortex.session.hooks.HookAdapter` for
a specific IDE / runtime:

* :mod:`claude_code` — Claude Code's native ``hooks`` block in
  ``settings.json``.
* :mod:`cursor`      — git ``post-commit`` script (works for Cursor,
  VSCode-with-Cline, plain editors).
* :mod:`pi`          — Pi Coding Agent ``just`` recipes.

Adapters are imported lazily by ``HookInstaller.default_installer`` so a
broken adapter does not poison the rest of the installer.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 17.

---
Fuente: código de `cortex/session/hooks/adapters/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
