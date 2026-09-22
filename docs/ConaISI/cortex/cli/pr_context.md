# cortex/cli/pr_context.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/pr_context.py` (249 líneas).
- **Módulo Python:** `cortex.cli.pr_context`.
- **Docstring del módulo:** ``cortex pr-context`` — pipeline DevSecDocOps (captura → docs → memoria).
- **Funciones de módulo:**
  - `pr_context_capture(title, body, author, branch, commit, pr_number, target_branch, labels, output)` — Capture PR metadata and save as JSON context.
  - `pr_context_store(context_file, lint_result, audit_result, test_result)` — Store PR context in episodic memory.
  - `pr_context_search(context_file, top_k, output)` — Search for similar past PRs in memory.
  - `pr_context_generate(context_file, vault)` — Generate documentation from PR context.
  - `pr_context_full(title, body, author, branch, commit, pr_number, target_branch, labels, lint_result, audit_result, test_result, vault, context_file)` — Full pipeline: capture + store + search + generate + sync (all in one).

## Para qué sirve

``cortex pr-context`` — pipeline DevSecDocOps (captura → docs → memoria).

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4). Los
comandos conservan nombres y comportamiento exactos.

## Relaciones

### Recibe de

- `cortex.cli.common` (_load_memory)
- Dependencias externas/stdlib: `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 249.
Docstrings de símbolos públicos:
- `pr_context_capture`: Capture PR metadata and save as JSON context.
- `pr_context_store`: Store PR context in episodic memory.
- `pr_context_search`: Search for similar past PRs in memory.
- `pr_context_generate`: Generate documentation from PR context.
- `pr_context_full`: Full pipeline: capture + store + search + generate + sync (all in one).

---
Fuente: código de `cortex/cli/pr_context.py` (AST + grafo de imports internos). No se usó documentación previa.
