# cortex/cli/hu.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/hu.py` (51 líneas).
- **Módulo Python:** `cortex.cli.hu`.
- **Docstring del módulo:** ``cortex hu`` — gestión de work items trackeados (import read-only).
- **Funciones de módulo:**
  - `hu_import(external_id, provider, no_remember)` — Import one external tracked item into ``vault/hu/``.
  - `hu_list()` — List tracked item notes already stored in ``vault/hu/``.
  - `hu_show(item_id)` — Show the local vault note path for one tracked item.

## Para qué sirve

``cortex hu`` — gestión de work items trackeados (import read-only).

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4).

## Relaciones

### Recibe de

- `cortex.cli.common` (_load_memory)
- Dependencias externas/stdlib: `typer`, `__future__`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 51.
Docstrings de símbolos públicos:
- `hu_import`: Import one external tracked item into ``vault/hu/``.
- `hu_list`: List tracked item notes already stored in ``vault/hu/``.
- `hu_show`: Show the local vault note path for one tracked item.

---
Fuente: código de `cortex/cli/hu.py` (AST + grafo de imports internos). No se usó documentación previa.
