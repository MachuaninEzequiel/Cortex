# cortex/episodic/summarizer.py

## Qué tiene adentro

- **Ruta de código:** `cortex/episodic/summarizer.py` (115 líneas).
- **Módulo Python:** `cortex.episodic.summarizer`.
- **Docstring del módulo:** cortex.episodic.summarizer -------------------------- Compresses verbose agent action logs into concise memory entries using an LLM backend (OpenAI, Anthropic, or local via Ollama).
- **Clases definidas:**
  - `Summarizer`
    - Compresses raw agent activity logs into short memory summaries.
    - Métodos públicos/especiales: `__init__`, `compress`
    - Métodos internos: `_call_openai`, `_call_anthropic`, `_call_ollama`, `_truncate_fallback`
- **Constantes / símbolos de módulo:** `COMPRESS_PROMPT`

## Para qué sirve

cortex.episodic.summarizer
--------------------------
Compresses verbose agent action logs into concise memory entries
using an LLM backend (OpenAI, Anthropic, or local via Ollama).

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `logging`, `os`, `__future__`, `typing`

### Envía a

- `cortex.core`
- `cortex.episodic`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 115.
Docstrings de símbolos públicos:
- `Summarizer.compress`: Summarize content. Falls back to a simple truncation if no LLM

---
Fuente: código de `cortex/episodic/summarizer.py` (AST + grafo de imports internos). No se usó documentación previa.
