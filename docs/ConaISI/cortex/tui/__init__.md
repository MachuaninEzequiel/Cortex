# cortex/tui/__init__.py

## Qué tiene adentro

- **Ruta de código:** `cortex/tui/__init__.py` (23 líneas).
- **Módulo Python:** `cortex.tui`.
- **Docstring del módulo:** cortex.tui — pantallas rich del Home/acciones/sesión/búsqueda (Obra 05 Fase D).
- **Constantes / símbolos de módulo:** `__all__`

## Para qué sirve

cortex.tui — pantallas rich del Home/acciones/sesión/búsqueda (Obra 05 Fase D).

Patrón: estado congelado + renderer puro (probable sin TTY), heredado de
``cli/session_tui.py``. La TUI ORQUESTA comandos/servicios existentes,
nunca reimplementa lógica (anti-patrón prohibido §3.6).

## Relaciones

### Recibe de

- `cortex.tui.core` (HomeState, render_actions_screen, render_home, run_home, snapshot_home)

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 23.
Reexportes observados:
- cortex.tui.core: HomeState, render_actions_screen, render_home, run_home, snapshot_home

---
Fuente: código de `cortex/tui/__init__.py` (AST + grafo de imports internos). No se usó documentación previa.
