# cortex/ide/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/ide/__init__.py` (162 líneas).
- **Módulo Python:** `cortex.ide`.
- **Docstring del módulo:** cortex.ide ---------- IDE adapter layer for Cortex agent profile injection.
- **Funciones de módulo:**
  - `inject(ide_name, project_root)` — Inject Cortex profiles and MCP config into a specific IDE.
  - `inject_all(project_root)` — Inject Cortex profiles into all IDE adapters.
  - `uninstall(ide_name)` — Remove Cortex profiles and MCP config from a specific IDE.
  - `uninstall_all()` — Remove Cortex profiles and MCP config from every registered IDE adapter.
  - `_find_project_root()` — Find the Cortex project root using WorkspaceLayout discovery.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.ide
----------
IDE adapter layer for Cortex agent profile injection.

Provides a unified interface for injecting Cortex agent profiles and MCP
configuration across all supported IDEs. Each IDE has its own adapter that
implements the common IDEAdapter contract.

Usage::

    from cortex.ide import inject, inject_all, uninstall, get_supported_ides

    inject("cursor", project_root=Path.cwd())
    inject_all(project_root=Path.cwd())
    uninstall("cursor")
    print(get_supported_ides())

## Relaciones

### Recibe de

- `cortex.ide.prompts` (build_all_prompts)
- `cortex.ide.registry` (get_adapter, get_all_adapters, get_supported_ides)
- `cortex.workspace.layout` (WorkspaceLayout)
- Dependencias externas/stdlib: `__future__`, `pathlib`

### Envía a

- `cortex.cli._setup_helpers`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 162.
Docstrings de símbolos públicos:
- `inject`: Inject Cortex profiles and MCP config into a specific IDE.
- `inject_all`: Inject Cortex profiles into all IDE adapters.
- `uninstall`: Remove Cortex profiles and MCP config from a specific IDE.
- `uninstall_all`: Remove Cortex profiles and MCP config from every registered IDE adapter.
Reexportes observados:
- cortex.ide.prompts: build_all_prompts
- cortex.ide.registry: get_adapter, get_all_adapters, get_supported_ides
- cortex.workspace.layout: WorkspaceLayout

---
Fuente: código de `cortex/ide/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
