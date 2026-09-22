# cortex/setup/cold_start.py

## Qué tiene adentro

- **Ruta de código:** `cortex/setup/cold_start.py` (541 líneas).
- **Módulo Python:** `cortex.setup.cold_start`.
- **Docstring del módulo:** cortex.setup.cold_start ------------------------- Cold Start bootstrap for Cortex memory system.
- **Funciones de módulo:**
  - `layer1_preseed_vault(vault_path, memory_store)` — Layer 1: Pre-seed memories from existing vault documentation.
  - `_extract_title(content, fallback)` — Extract title from markdown content.
  - `_extract_tags(content, md_file)` — Extract tags from YAML frontmatter.
  - `_extract_links(content)` — Extract wiki-links from markdown.
  - `layer2_git_history(project_root, memory_store, max_commits)` — Layer 2: Mine git history for architectural decisions and patterns.
  - `_get_git_commits(project, max_count)` — Get commits from git log.
  - `_chunk_commits_by_time(commits)` — Group commits by time proximity (same day = same chunk).
  - `_classify_commit_chunk(commits)` — Classify the type of work in a commit chunk.
  - `_is_architectural_decision(message)` — Check if a commit message indicates an architectural decision.
  - `layer3_readme_fallback(project_root, memory_store)` — Layer 3: Use README.md as fallback context.
  - `_parse_readme_sections(content)` — Parse README into sections.
  - `run_cold_start(project_root, memory_store, vault_path, git_depth)` — Run all Cold Start layers as complementary context sources.

## Para qué sirve

cortex.setup.cold_start
-------------------------
Cold Start bootstrap for Cortex memory system.

Provides 3-layer fallback when no memories exist:
  Layer 1: Pre-seed from existing vault documentation
  Layer 2: Git history mining (extract decisions from commits)
  Layer 3: README fallback (project intro from README.md)

This ensures agents always have context, even on first use.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `re`, `subprocess`, `__future__`, `pathlib`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 541.
Docstrings de símbolos públicos:
- `layer1_preseed_vault`: Layer 1: Pre-seed memories from existing vault documentation.
- `layer2_git_history`: Layer 2: Mine git history for architectural decisions and patterns.
- `layer3_readme_fallback`: Layer 3: Use README.md as fallback context.
- `run_cold_start`: Run all Cold Start layers as complementary context sources.

---
Fuente: código de `cortex/setup/cold_start.py` (AST + grafo de imports internos). No se usó documentación previa.
