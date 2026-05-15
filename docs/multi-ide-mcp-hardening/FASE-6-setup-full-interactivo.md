# FASE 6 — Setup full con seleccion interactiva de IDE

**Semaforo:** Verde (alcance acotado, sin impacto en runtime de Cortex).
**Pre-requisitos:** Ninguno (independiente; puede ejecutarse en paralelo con Fases 1-5).
**Bloquea:** Fase 7 (parcialmente; el smoke test E2E debe ejercitar este flujo).

---

## Objetivo

Eliminar la asimetria entre `cortex setup full` y `cortex setup agent` respecto a la seleccion de IDE. Hoy `setup_agent` ofrece un menu interactivo (numerado) y `setup_full` no — obliga al adopter a correr dos comandos en lugar de uno.

Coherencia con la experiencia del adopter: una sola ejecucion de `cortex setup full` debe dejar el proyecto **completamente listo**, incluyendo el adapter del IDE elegido.

---

## Tasks

### Task 6.1 — Extraer helper `_select_ide_interactive`

**Archivo nuevo:** `cortex/cli/_setup_helpers.py`.

**Contenido:**

```python
"""Helpers compartidos por los comandos `cortex setup *`."""

from __future__ import annotations

import typer

import cortex.ide as cortex_ide


def select_ide_interactive(provided_ide: str | None, non_interactive: bool) -> str | None:
    """Resolve the target IDE for setup.

    Returns the IDE name (str) or None (skip IDE configuration).

    Resolution order:
    - If `provided_ide` is given (CLI flag --ide), use it directly.
    - If `non_interactive` is True, return None (no prompt, no IDE).
    - Otherwise prompt the user with a numbered menu of supported IDEs.
    """
    if provided_ide is not None:
        return provided_ide
    if non_interactive:
        return None

    typer.echo("\nSelect IDE to configure:")
    supported = cortex_ide.get_supported_ides()
    for i, ide_name in enumerate(supported, 1):
        typer.echo(f"  {i}. {ide_name}")
    typer.echo("  0. Skip IDE configuration")

    choice = typer.prompt("\nEnter IDE number or name", default="0")

    if choice == "0":
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(supported):
            return supported[idx]
        typer.echo("Invalid selection, skipping IDE configuration.")
        return None
    if choice in supported:
        return choice
    typer.echo("Invalid selection, skipping IDE configuration.")
    return None
```

### Task 6.2 — Refactor `setup_agent` para usar el helper

**Archivo:** `cortex/cli/main.py`.

**Cambios:**
- Reemplazar el bloque interactivo actual de `setup_agent` (lineas 446-466 aprox) por una llamada al helper:

```python
from cortex.cli._setup_helpers import select_ide_interactive

selected_ide = select_ide_interactive(provided_ide=ide, non_interactive=False)
```

(`setup_agent` no tiene flag `--non-interactive` actualmente; mantener el comportamiento pidiendo siempre prompt cuando `--ide` no se da. O agregar `--non-interactive` por consistencia. Decision a confirmar con el creador.)

### Task 6.3 — Agregar seleccion interactiva a `setup_full`

**Archivo:** `cortex/cli/main.py`.

**Cambios:**
- En el cuerpo de `setup_full`, antes de instanciar `SetupOrchestrator`:

```python
from cortex.cli._setup_helpers import select_ide_interactive

selected_ide = select_ide_interactive(provided_ide=ide, non_interactive=non_interactive)
```

- Pasar `selected_ide` a `orchestrator.run(..., ide=selected_ide, ...)` (en vez de pasar `ide` crudo).

### Task 6.4 — Tests del helper

**Archivo nuevo:** `tests/unit/cli/test_setup_helpers.py`.

**Tests:**
- `test_select_ide_with_flag_returns_flag`: si `provided_ide="claude_code"`, devuelve `"claude_code"` sin prompt.
- `test_select_ide_non_interactive_returns_none`: si `non_interactive=True` y no hay flag, devuelve `None` sin prompt.
- `test_select_ide_interactive_valid_number`: simular input `"1"`, devolver primer IDE de `get_supported_ides()`.
- `test_select_ide_interactive_zero_returns_none`: simular input `"0"`, devolver `None`.
- `test_select_ide_interactive_valid_name`: simular input `"opencode"`, devolver `"opencode"`.
- `test_select_ide_interactive_invalid_input_returns_none`: simular input invalido, devolver `None` con mensaje de warning.

### Task 6.5 — Test de integracion del comando

**Archivo:** `tests/integration/test_setup_commands.py` (puede existir; ampliar).

**Tests:**
- `test_setup_full_non_interactive_skips_ide_prompt`: `cortex setup full --non-interactive --git-depth 50` no prompt-ea.
- `test_setup_full_with_ide_flag_skips_prompt`: `cortex setup full --ide claude-code --git-depth 50` no prompt-ea, instala claude-code.
- `test_setup_full_interactive_picks_ide` (puede usar `pexpect` o input simulado): la version interactiva muestra el menu y respeta la eleccion.

### Task 6.6 — Documentacion

**Archivo:** README, guia de adopter, o `docs/guides/setup.md` (segun donde viva la doc actual).

**Cambios:**
- Documentar que `cortex setup full` ahora prompt-ea por IDE si no se pasa `--ide`.
- Documentar `--non-interactive` como flag para CI / scripted setups.
- Eliminar cualquier mencion de "tras `setup full`, correr `setup agent` para configurar el IDE".

---

## Archivos involucrados

- Nuevos:
  - `cortex/cli/_setup_helpers.py`
  - `tests/unit/cli/test_setup_helpers.py`
- Modificados:
  - `cortex/cli/main.py` (refactor `setup_agent` + ampliar `setup_full`).
  - `tests/integration/test_setup_commands.py` (nuevos tests; archivo puede existir).
  - Documentacion de adopter.

---

## Criterios de aceptacion

- [ ] `cortex setup full` (sin flags) prompt-ea por IDE.
- [ ] `cortex setup full --non-interactive` no prompt-ea (CI safe).
- [ ] `cortex setup full --ide claude-code` no prompt-ea, instala directamente.
- [ ] `cortex setup agent` mantiene exactamente el mismo comportamiento que antes (prompt cuando no se pasa `--ide`).
- [ ] El helper `select_ide_interactive` es la unica implementacion del menu — `setup_agent` y `setup_full` lo comparten.
- [ ] Tests cubren los 4 paths del helper (flag, non-interactive, interactivo valido, interactivo invalido).

---

## Gate de cero deuda tecnica

- [ ] CERO duplicacion entre `setup_agent` y `setup_full` para la seleccion de IDE.
- [ ] CERO referencias en docs a la "vieja forma" (necesidad de correr dos comandos).
- [ ] El helper no tiene dependencias circulares con `cortex.ide` ni con `cortex.setup.orchestrator`.
- [ ] Tests cubren los caminos felices Y los infelices (input invalido).
- [ ] No quedan imports de `typer` desorganizados — los imports en `main.py` para el flujo viejo se eliminan limpiamente.

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Un script de CI existente del repo o de un adopter usa `cortex setup full` esperando que NO prompt-ee | Documentar `--non-interactive` claramente en CHANGELOG. Cualquier script existente que no use `--non-interactive` Y no use `--ide` ahora se va a colgar esperando input. Mitigacion: el comando actual ya prompt-ea por `git_depth` cuando no se da, asi que un script existente sin `--git-depth` ya estaba roto en CI; el cambio no introduce regresion sobre scripts ya correctos. |
| El helper queda en `cortex/cli/` y crea acoplamiento entre cli y orchestrator | El helper solo usa `cortex.ide` (lista de IDEs) y `typer` (prompts). No toca el orchestrator. Acoplamiento minimo. |
| `get_supported_ides()` puede cambiar el orden y romper los tests que asumen "primer IDE" | El test usa el indice computado de `get_supported_ides()`, no un literal. |

---

## Estimacion

1 sesion. Es la fase mas pequeña y autocontenida del plan.

---

## Handoff a Fase 7

```yaml
agent: fase-6-setup-full-interactivo
status: completed
artifacts_produced:
  - cortex/cli/_setup_helpers.py
  - tests/unit/cli/test_setup_helpers.py
  - tests/integration/test_setup_commands.py (ampliado)
artifacts_modified:
  - cortex/cli/main.py
verified_claims:
  - "cortex setup full prompt-ea por IDE en interactivo y respeta --non-interactive y --ide"
  - "Cero duplicacion entre setup_agent y setup_full"
context_for_next:
  - "Fase 7 puede ejercitar el flujo end-to-end de un adopter empezando por cortex setup full"
```
