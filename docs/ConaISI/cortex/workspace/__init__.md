# cortex/workspace/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/workspace/__init__.py` (38 líneas).
- **Módulo Python:** `cortex.workspace`.
- **Docstring del módulo:** cortex.workspace --------------- Workspace layout resolution for Cortex projects.
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.workspace
---------------
Workspace layout resolution for Cortex projects.

Provides a single source of truth for discovering and resolving
all filesystem paths used by the Cortex runtime, setup, CLI,
IDE adapters, MCP server, and WebGraph.

The layout supports two modes:

- **New layout** (layout_version >= 2): everything lives inside
  ``repo_root / ".cortex"``.  Relative paths in config files resolve
  against ``workspace_root`` (the ``.cortex`` directory).

- **Legacy layout** (layout_version 1 or absent): files are spread
  across the repo root — ``config.yaml``, ``vault/``, ``.memory/``
  at the top level, with ``.cortex/`` holding skills, subagents and
  org.yaml.

The ``WorkspaceLayout.discover()`` method walks up from a starting
directory to find the project root and determine which layout is
in use.  All consumers should use this class instead of hardcoding
paths.

Usage::

    from cortex.workspace import WorkspaceLayout

    layout = WorkspaceLayout.discover(Path.cwd())
    config = layout.config_path        # .cortex/config.yaml  or  config.yaml
    vault = layout.vault_path           # .cortex/vault         or  vault
    memory = layout.episodic_memory_path  # .cortex/memory       or  .memory/chroma

## Relaciones

### Recibe de

- `cortex.workspace.layout` (WorkspaceLayout)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 38.
Reexportes observados:
- cortex.workspace.layout: WorkspaceLayout

---
Fuente: código de `cortex/workspace/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
