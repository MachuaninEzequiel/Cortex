# cortex/ide/adapters/claude_desktop.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/claude_desktop.py` (114 líneas).
- **Módulo Python:** `cortex.ide.adapters.claude_desktop`.
- **Clases definidas:**
  - `ClaudeDesktopAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `needs_wsl_shielding`, `inject_profiles`, `inject_mcp`, `uninstall`

## Para qué sirve

Define ClaudeDesktopAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict)
- Dependencias externas/stdlib: `contextlib`, `json`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 114.
Docstrings de símbolos públicos:
- `ClaudeDesktopAdapter.uninstall`: Remove the Cortex MCP server from claude_desktop_config.json.

---
Fuente: código de `cortex/ide/adapters/claude_desktop.py` (AST + grafo de imports internos). No se usó documentación previa.
