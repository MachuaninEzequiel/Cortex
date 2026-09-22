# cortex/cli/_unicode_fallback.py

## Qué tiene adentro

- **Ruta de código:** `cortex/cli/_unicode_fallback.py` (64 líneas).
- **Módulo Python:** `cortex.cli._unicode_fallback`.
- **Docstring del módulo:** Cross-platform glyph helpers — fallback to ASCII when the console encoding cannot render unicode (e.g. ``cmd.exe`` defaulting to cp1252).
- **Funciones de módulo:**
  - `supports_unicode(console)` — Return True if ``console.file.encoding`` clearly supports unicode.
  - `glyph(name)` — Return the unicode glyph for ``name``, or its ASCII fallback.
- **Constantes / símbolos de módulo:** `_UNICODE_GLYPHS`, `_ASCII_FALLBACK`, `__all__`

## Para qué sirve

Cross-platform glyph helpers — fallback to ASCII when the console
encoding cannot render unicode (e.g. ``cmd.exe`` defaulting to cp1252).

The Phase 06 TUI uses a small set of decorative glyphs (✓, ✗, ⏸, ⚠, ▶, …).
Hard-coding them breaks on Windows legacy consoles where the unicode
points are replaced with ``?`` or raise ``UnicodeEncodeError`` from
``rich``'s file writer. ``glyph(name, console=...)`` returns the right
character for the active console.

This helper is intentionally cheap: a dict lookup plus a substring check
on ``console.file.encoding``. No locale probing, no platform branching.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- `cortex.cli.session_tui`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 64.
Docstrings de símbolos públicos:
- `supports_unicode`: Return True if ``console.file.encoding`` clearly supports unicode.
- `glyph`: Return the unicode glyph for ``name``, or its ASCII fallback.

---
Fuente: código de `cortex/cli/_unicode_fallback.py` (AST + grafo de imports internos). No se usó documentación previa.
