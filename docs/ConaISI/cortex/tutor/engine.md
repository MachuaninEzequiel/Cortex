# cortex/tutor/engine.py

## Qué tiene adentro

- **Ruta de código:** `cortex/tutor/engine.py` (233 líneas).
- **Módulo Python:** `cortex.tutor.engine`.
- **Docstring del módulo:** cortex.tutor.engine ------------------- TUI engine for the interactive Cortex tutor. Handles menu rendering, topic navigation, and the main loop.
- **Clases definidas:**
  - `TutorTopic` (Protocol)
    - Contract that each tutor topic must implement.
    - Métodos públicos/especiales: `title`, `icon`, `one_liner`, `slug`, `guide_path`, `render`
  - `TutorEngine`
    - Interactive TUI engine for the Cortex tutor.
    - Métodos públicos/especiales: `register`, `show_topic`, `show_topic_by_slug`, `run`, `default`
    - Métodos internos: `_render_menu`, `_render_topic`, `_render_footer`
- **Funciones de módulo:**
  - `_safe_console()` — Create a Console that works on Windows with emoji support.

## Para qué sirve

cortex.tutor.engine
-------------------
TUI engine for the interactive Cortex tutor.
Handles menu rendering, topic navigation, and the main loop.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `sys`, `__future__`, `dataclasses`, `typing`, `rich.console`, `rich.panel`, `rich.table`, `rich.text`

### Envía a

- `cortex.tutor`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 233.
Docstrings de símbolos públicos:
- `TutorTopic.title`: Short title for the menu (e.g. 'Pipeline CI/CD').
- `TutorTopic.icon`: Emoji icon for the menu entry.
- `TutorTopic.one_liner`: One-line description shown in the menu.
- `TutorTopic.slug`: Machine-readable name for direct access (e.g. 'pipeline').
- `TutorTopic.guide_path`: Relative path to the extended guide in docs/guides/, or None.
- `TutorTopic.render`: Render the topic content to the console (max 20-25 lines).
- `TutorEngine.register`: Register a navigable topic.
- `TutorEngine.show_topic`: Render a single topic by its 0-based index.
- `TutorEngine.show_topic_by_slug`: Render a topic by its slug name. Returns True if found.
- `TutorEngine.run`: Start the interactive TUI loop.
- `TutorEngine.default`: Create an engine pre-loaded with all built-in topics.

---
Fuente: código de `cortex/tutor/engine.py` (AST + grafo de imports internos). No se usó documentación previa.
