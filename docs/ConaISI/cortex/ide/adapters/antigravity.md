# cortex/ide/adapters/antigravity.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/antigravity.py` (176 líneas).
- **Módulo Python:** `cortex.ide.adapters.antigravity`.
- **Clases definidas:**
  - `AntigravityAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Funciones de módulo:**
  - `_unique_backup(file_path)` — ``_backup_file`` con nombre unico.

## Para qué sirve

Define AntigravityAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header)
- Dependencias externas/stdlib: `contextlib`, `json`, `logging`, `__future__`, `datetime`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 176.
Docstrings de símbolos públicos:
- `AntigravityAdapter.uninstall`: Revertir lo inyectado por Cortex en ``~/.gemini/settings.json``.

---
Fuente: código de `cortex/ide/adapters/antigravity.py` (AST + grafo de imports internos). No se usó documentación previa.
