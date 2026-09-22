# cortex/embedders/language.py

## Qué tiene adentro

- **Ruta de código:** `cortex/embedders/language.py` (128 líneas).
- **Módulo Python:** `cortex.embedders.language`.
- **Docstring del módulo:** cortex.embedders.language ---------------------------- Heuristic ES/EN language detection — pure functions, zero dependencies.
- **Funciones de módulo:**
  - `detect_language(text)` — Classify *text* as ``"es"`` / ``"en"``, or ``None`` when unsure.
  - `resolve_language(frontmatter_lang, text)` — Resolve the effective language: frontmatter ALWAYS beats detection.
- **Constantes / símbolos de módulo:** `_ES_DIACRITICS`, `_ES_STOPWORDS`, `_EN_STOPWORDS`, `_WORD_RE`, `_LETTER_RE`

## Para qué sirve

cortex.embedders.language
----------------------------
Heuristic ES/EN language detection — pure functions, zero dependencies.

Used by Obra 04 Fase C (per-language embedding config). Priority order for
resolving the language of a document/query is ALWAYS:

1. Explicit ``lang:`` frontmatter (or explicit argument) — wins over anything.
2. Heuristic detection here (only when ``language_detection: heuristic``).
3. Default model (detection returns ``None`` on doubt).

Heuristic signals
-----------------
- Diacritics ratio: ``á é í ó ú ü ñ ¿ ¡`` over total letters. Spanish-only
  characters are a strong positive signal; English has none.
- Stopword frequency: common ES vs EN function words over tokens.

A text is only classified when it is long enough (default >= 20 words, per
spec: "never guess on short text") and one language clearly outscores the
other. Mixed or ambiguous text returns ``None``.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `re`, `__future__`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 128.
Docstrings de símbolos públicos:
- `detect_language`: Classify *text* as ``"es"`` / ``"en"``, or ``None`` when unsure.
- `resolve_language`: Resolve the effective language: frontmatter ALWAYS beats detection.

---
Fuente: código de `cortex/embedders/language.py` (AST + grafo de imports internos). No se usó documentación previa.
