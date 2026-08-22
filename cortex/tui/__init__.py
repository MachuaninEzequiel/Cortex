"""cortex.tui — pantallas rich del Home/acciones/sesión/búsqueda (Obra 05 Fase D).

Patrón: estado congelado + renderer puro (probable sin TTY), heredado de
``cli/session_tui.py``. La TUI ORQUESTA comandos/servicios existentes,
nunca reimplementa lógica (anti-patrón prohibido §3.6).
"""

from cortex.tui.core import (
    HomeState,
    render_actions_screen,
    render_home,
    run_home,
    snapshot_home,
)

__all__ = [
    "HomeState",
    "render_actions_screen",
    "render_home",
    "run_home",
    "snapshot_home",
]
