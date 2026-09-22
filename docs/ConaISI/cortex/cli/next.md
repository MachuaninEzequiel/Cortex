# cortex/cli/next.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/next.py` (138 líneas).
- **Módulo Python:** `cortex.cli.next`.
- **Docstring del módulo:** ``cortex next`` — lista de acciones sugeridas sin TUI (Obra 05 Fase B).
- **Funciones de módulo:**
  - `register(app)` — Registra ``cortex next`` en el app principal.

## Para qué sirve

``cortex next`` — lista de acciones sugeridas sin TUI (Obra 05 Fase B).

Para agentes y scripts. Gate: <2s en repo mediano (contexto perezoso;
snapshot on-open, no escaneo completo salvo ``--all``).

## Relaciones

### Recibe de

- `cortex.action_engine.actions` (build_default_registry)
- `cortex.action_engine.context` (ActionContext)
- `cortex.action_engine.scheduler` (Scheduler)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 138.
Docstrings de símbolos públicos:
- `register`: Registra ``cortex next`` en el app principal.

---
Fuente: código de `cortex/cli/next.py` (AST + grafo de imports internos). No se usó documentación previa.
