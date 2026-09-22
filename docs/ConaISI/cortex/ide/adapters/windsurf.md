# cortex/ide/adapters/windsurf.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/windsurf.py` (171 líneas).
- **Módulo Python:** `cortex.ide.adapters.windsurf`.
- **Clases definidas:**
  - `WindsurfAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Funciones de módulo:**
  - `_unique_backup(file_path)` — ``_backup_file`` con nombre unico (evita colisiones mismo-segundo
- **Constantes / símbolos de módulo:** `_CORTEX_AGENTS_MD`

## Para qué sirve

Define WindsurfAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, is_content_identical_to_bundle)
- Dependencias externas/stdlib: `contextlib`, `json`, `logging`, `__future__`, `datetime`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 171.
Docstrings de símbolos públicos:
- `WindsurfAdapter.uninstall`: Eliminar lo inyectado por Cortex en Windsurf.

---
Fuente: código de `cortex/ide/adapters/windsurf.py` (AST + grafo de imports internos). No se usó documentación previa.
