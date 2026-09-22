# cortex/cli/embedding.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/embedding.py` (216 líneas).
- **Módulo Python:** `cortex.cli.embedding`.
- **Docstring del módulo:** ``cortex embedding-status`` y ``cortex reindex`` — superficie de embeddings.
- **Funciones de módulo:**
  - `register(app)` — Registra ``embedding-status`` y ``reindex`` en el app principal.

## Para qué sirve

``cortex embedding-status`` y ``cortex reindex`` — superficie de embeddings.

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4). Dominio
de la Obra 04: estado de modelos por idioma y reindexación con
backup/rollback.

## Relaciones

### Recibe de

- `cortex.cli.common` (_load_memory)
- Dependencias externas/stdlib: `os`, `typer`, `yaml`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 216.
Docstrings de símbolos públicos:
- `register`: Registra ``embedding-status`` y ``reindex`` en el app principal.

---
Fuente: código de `cortex/cli/embedding.py` (AST + grafo de imports internos). No se usó documentación previa.
