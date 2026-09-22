# cortex/ide/adapters/opencode.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/opencode.py` (281 líneas).
- **Módulo Python:** `cortex.ide.adapters.opencode`.
- **Clases definidas:**
  - `OpenCodeAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `needs_wsl_shielding`, `inject_profiles`, `inject_mcp`, `uninstall`

## Para qué sirve

Define OpenCodeAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header, _is_wsl)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `contextlib`, `json`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 281.
Docstrings de símbolos públicos:
- `OpenCodeAdapter.uninstall`: Remove Cortex artifacts from OpenCode (Obra 02 Fase 2).

---
Fuente: código de `cortex/ide/adapters/opencode.py` (AST + grafo de imports internos). No se usó documentación previa.
