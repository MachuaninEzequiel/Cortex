# cortex/tutor/topics/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/tutor/topics/__init__.py` (35 líneas).
- **Módulo Python:** `cortex.tutor.topics`.
- **Docstring del módulo:** cortex.tutor.topics ------------------- Registry of all built-in tutor topics. Each topic module exposes a class that satisfies the TutorTopic protocol.
- **Funciones de módulo:**
  - `get_all_topics()` — Return all built-in topics in display order.

## Para qué sirve

cortex.tutor.topics
-------------------
Registry of all built-in tutor topics.
Each topic module exposes a class that satisfies the TutorTopic protocol.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `typing`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 35.
Docstrings de símbolos públicos:
- `get_all_topics`: Return all built-in topics in display order.

---
Fuente: código de `cortex/tutor/topics/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
