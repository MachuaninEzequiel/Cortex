# cortex/ide/registry.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/registry.py` (191 líneas).
- **Módulo Python:** `cortex.ide.registry`.
- **Docstring del módulo:** cortex.ide.registry ------------------- Auto-discovery and registration of IDE adapters.
- **Funciones de módulo:**
  - `_build_registry()` — Import and register all known adapters.
  - `get_registry()` — Return the adapter registry, building it on first call.
  - `get_adapter(ide_name)` — Get an adapter instance by IDE name.
  - `get_all_adapters()` — Return instances of registered adapters.
  - `get_supported_ides()` — Return sorted list of IDE names intended for user-facing selection.
  - `get_target_ides()` — Return the IDEs officially targeted by Cortex (Claude Code, OpenCode, Pi, Codex).
  - `get_ide_tier(ide_name)` — Classify an IDE as ``target | community | experimental``.
  - `is_ide_validated(ide_name)` — ¿El adapter de este IDE fue validado contra docs oficiales 2026?
  - `get_validated_ides_list()` — Lista de IDEs cuyos adapters estan validados contra docs oficiales 2026.
  - `get_unvalidated_ides_list()` — Lista de IDEs registrados pero NO validados contra docs oficiales 2026.
- **Constantes / símbolos de módulo:** `_ALIASES`, `TARGET_IDES`, `_EXPERIMENTAL_IDES`, `COMMUNITY_IDES`, `VALIDATED_IDES`

## Para qué sirve

cortex.ide.registry
-------------------
Auto-discovery and registration of IDE adapters.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.cli.ide`
- `cortex.ide`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 191.
Docstrings de símbolos públicos:
- `get_registry`: Return the adapter registry, building it on first call.
- `get_adapter`: Get an adapter instance by IDE name.
- `get_all_adapters`: Return instances of registered adapters.
- `get_supported_ides`: Return sorted list of IDE names intended for user-facing selection.
- `get_target_ides`: Return the IDEs officially targeted by Cortex (Claude Code, OpenCode, Pi, Codex).
- `get_ide_tier`: Classify an IDE as ``target | community | experimental``.
- `is_ide_validated`: ¿El adapter de este IDE fue validado contra docs oficiales 2026?
- `get_validated_ides_list`: Lista de IDEs cuyos adapters estan validados contra docs oficiales 2026.
- `get_unvalidated_ides_list`: Lista de IDEs registrados pero NO validados contra docs oficiales 2026.

---
Fuente: código de `cortex/ide/registry.py` (AST + grafo de imports internos). No se usó documentación previa.
