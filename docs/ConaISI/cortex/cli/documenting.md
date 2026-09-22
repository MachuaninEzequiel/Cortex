# cortex/cli/documenting.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/documenting.py` (372 líneas).
- **Módulo Python:** `cortex.cli.documenting`.
- **Docstring del módulo:** ``save-session`` / ``create-spec`` / ``finish-session`` — flujo documental.
- **Funciones de módulo:**
  - `_parse_verification_hooks(specs)` — Parse repeatable ``--verification-hook 'name=...;command=...'`` arguments.
  - `register(app)` — Registra save-session / create-spec / finish-session en el app principal.

## Para qué sirve

``save-session`` / ``create-spec`` / ``finish-session`` — flujo documental.

Extraído del monolito cli/main.py (deuda V2, Obra 01 fase P4).
``_parse_verification_hooks`` vive acá y se re-exporta desde main para
no romper imports existentes (tests/unit/cli/).

## Relaciones

### Recibe de

- `cortex.cli.common` (_load_memory)
- Dependencias externas/stdlib: `json`, `typer`, `__future__`, `pathlib`

### Envía a

- `cortex.cli.main`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 372.
Docstrings de símbolos públicos:
- `register`: Registra save-session / create-spec / finish-session en el app principal.

---
Fuente: código de `cortex/cli/documenting.py` (AST + grafo de imports internos). No se usó documentación previa.
