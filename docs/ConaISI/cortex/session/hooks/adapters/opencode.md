# cortex/session/hooks/adapters/opencode.py

## Qué tiene adentro

- **Ruta de código:** `cortex/session/hooks/adapters/opencode.py` (180 líneas).
- **Módulo Python:** `cortex.session.hooks.adapters.opencode`.
- **Docstring del módulo:** cortex.session.hooks.adapters.opencode — opencode IDE hook adapter.
- **Clases definidas:**
  - `OpencodeHookAdapter`
    - Manage the Cortex block inside ``.opencode/hooks.md``.
    - Métodos públicos/especiales: `is_supported`, `install`, `uninstall`, `status`
    - Métodos internos: `_hooks_path`, `_read`, `_render`, `_strip_block`
- **Constantes / símbolos de módulo:** `HOOKS_RELATIVE`, `START_MARKER`, `END_MARKER`, `_HOOK_COMMAND`, `HOOK_BLOCK`, `__all__`

## Para qué sirve

cortex.session.hooks.adapters.opencode — opencode IDE hook adapter.

Installs a Cortex-managed entry into ``.opencode/hooks.md`` (project
scope) so that opencode emits a checkpoint to the active Cortex session
on every file-edit event. The hook block is delimited by HTML-comment
sentinel markers so install / uninstall preserve user content.

Format research is captured in
``docs/pluggable-middle/fases/_internal/opencode-hooks-research.md``.

## Relaciones

### Recibe de

- `cortex.session.hooks.installer` (HookStatus, InstallResult, UninstallResult)
- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 180.

---
Fuente: código de `cortex/session/hooks/adapters/opencode.py` (AST + grafo de imports internos). No se usó documentación previa.
