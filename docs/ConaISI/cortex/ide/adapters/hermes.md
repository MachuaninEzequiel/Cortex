# cortex/ide/adapters/hermes.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/hermes.py` (133 líneas).
- **Módulo Python:** `cortex.ide.adapters.hermes`.
- **Clases definidas:**
  - `HermesAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Constantes / símbolos de módulo:** `_CORTEX_PROMPT_KEYS`

## Para qué sirve

Define HermesAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header)
- Dependencias externas/stdlib: `contextlib`, `json`, `logging`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 133.
Docstrings de símbolos públicos:
- `HermesAdapter.uninstall`: Quitar lo inyectado por Cortex de ``~/.config/hermes/config.json``.

---
Fuente: código de `cortex/ide/adapters/hermes.py` (AST + grafo de imports internos). No se usó documentación previa.
