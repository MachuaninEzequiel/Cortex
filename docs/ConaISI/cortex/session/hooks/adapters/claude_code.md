# cortex/session/hooks/adapters/claude_code.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/adapters/claude_code.py` (214 líneas).
- **Módulo Python:** `cortex.session.hooks.adapters.claude_code`.
- **Docstring del módulo:** cortex.session.hooks.adapters.claude_code — Claude Code hook adapter.
- **Clases definidas:**
  - `ClaudeCodeHookAdapter`
    - Manage the ``PostToolUse`` Cortex entry in ``.claude/settings.json``.
    - Métodos públicos/especiales: `is_supported`, `install`, `uninstall`, `status`
    - Métodos internos: `_settings_path`, `_load`
- **Funciones de módulo:**
  - `_cortex_hook_entry()`
  - `_has_cortex_hook(settings)`
  - `_inject_cortex_hook(settings)`
  - `_remove_cortex_hook(settings)`
- **Constantes / símbolos de módulo:** `CORTEX_HOOK_MARKER`, `CLAUDE_SETTINGS_RELATIVE`, `HOOK_MATCHER`, `HOOK_COMMAND`, `__all__`

## Para qué sirve

cortex.session.hooks.adapters.claude_code — Claude Code hook adapter.

Installs a Cortex-managed entry into Claude Code's native ``hooks`` block
inside ``.claude/settings.json`` so that every ``Edit`` / ``Write`` /
``MultiEdit`` tool-use emits a checkpoint to the active Cortex session.

The hook command is short, runs in the background (``>/dev/null 2>&1``)
and is suffixed with ``|| true`` so a Cortex failure never blocks Claude
Code. The entry carries a ``_cortex_managed: true`` marker so install /
uninstall are precise even if the user adds other hooks manually.

Format of the Claude Code settings (subset we care about)::

    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
              {"type": "command", "command": "cortex session checkpoint ..."}
            ],
            "_cortex_managed": true
          }
        ]
      }
    }

## Relaciones

### Recibe de

- `cortex.session.hooks.installer` (HookStatus, InstallResult, UninstallResult)
- Dependencias externas/stdlib: `json`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 214.

---
Fuente: código de `cortex/session/hooks/adapters/claude_code.py` (AST + grafo de imports internos). No se usó documentación previa.
