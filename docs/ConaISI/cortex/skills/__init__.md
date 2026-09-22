# cortex/skills/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/skills/__init__.py` (99 líneas).
- **Módulo Python:** `cortex.skills`.
- **Docstring del módulo:** cortex.skills ------------- Bundled Obsidian skills for Markdown documentation.
- **Funciones de módulo:**
  - `install_skills(target_dir)` — Copy all bundled skills into the target directory.
  - `_copy_tree(src_ref, dest)` — Recursively copy a directory tree from importlib resources to disk.
- **Constantes / símbolos de módulo:** `SKILL_NAMES`

## Para qué sirve

cortex.skills
-------------
Bundled Obsidian skills for Markdown documentation.

These skills are installed into the project's .cortex/skills/ directory
during ``cortex setup agent`` so that AI agents working on the project know
how to write proper documentation.

Available skills
----------------
- obsidian-markdown — Obsidian Flavored Markdown (wikilinks, embeds, callouts, properties)
- json-canvas       — JSON Canvas format for visual note connections
- obsidian-bases    — Obsidian Bases for filtered/sorted note views
- obsidian-cli      — Obsidian CLI commands
- defuddle          — Web page cleanup and extraction

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `importlib.resources`, `logging`, `__future__`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 99.
Docstrings de símbolos públicos:
- `install_skills`: Copy all bundled skills into the target directory.

---
Fuente: código de `cortex/skills/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
