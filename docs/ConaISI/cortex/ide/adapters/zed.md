# cortex/ide/adapters/zed.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/adapters/zed.py` (115 líneas).
- **Módulo Python:** `cortex.ide.adapters.zed`.
- **Clases definidas:**
  - `ZedAdapter` (IDEAdapter)
    - Métodos públicos/especiales: `name`, `display_name`, `get_config_paths`, `inject_profiles`, `inject_mcp`, `uninstall`
- **Constantes / símbolos de módulo:** `_CORTEX_AGENT_KEYS`

## Para qué sirve

Define ZedAdapter. No hay docstring de módulo; el propósito se infiere de las clases y métodos listados.

## Relaciones

### Recibe de

- `cortex.ide.base` (IDEAdapter, _backup_file, _deep_merge_dict, _generate_autogen_header)
- Dependencias externas/stdlib: `contextlib`, `json`, `logging`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 115.
Docstrings de símbolos públicos:
- `ZedAdapter.uninstall`: Quitar los agents canonico de Cortex de ``~/.zed/agents.json``.

---
Fuente: código de `cortex/ide/adapters/zed.py` (AST + grafo de imports internos). No se usó documentación previa.
