# Fase 6 — Meta-skill y Assets de Workspace: Realización

## Fecha
2026-05-09

## Resumen
Se crearon las meta-skills de Autopilot como assets del paquete, se modificó el setup del workspace para instalarlas opcionalmente, y se agregó `build_autopilot_prompts()` como función separada en el módulo de prompts. El setup normal sin Autopilot queda idéntico.

## Archivos creados
1. `cortex/autopilot/skills/using-cortex-autopilot.md` — meta-skill bootstrap con los 11 puntos obligatorios, tabla anti-racionalización (§10.4), regla de verificación (§10.5) y prioridad de instrucciones (§10.6).
2. `cortex/autopilot/skills/cortex-autopilot-finish.md` — skill de cierre de sesión.
3. `tests/unit/autopilot/test_skills_assets.py` — 14 tests validando contenido, instalación, y comportamiento de los prompt builders.

## Archivos modificados
1. `cortex/setup/cortex_workspace.py`:
   - Se agregó `_autopilot_skills_dir()` para resolver la ruta del paquete.
   - Se agregó `autopilot_file_map()` que lee dinámicamente todos los `*.md` de `cortex/autopilot/skills/`.
   - Se extendió `ensure_cortex_workspace(..., autopilot: bool = False)` para instalar skills Autopilot solo cuando se solicita explícitamente.
2. `cortex/ide/prompts.py`:
   - `build_all_prompts()` permanece sin cambios (no carga Autopilot por defecto).
   - Se agregó `build_autopilot_prompts()` que lee `using-cortex-autopilot` y `cortex-autopilot-finish` desde el workspace skills directory (con fallback si no están instalados).

## Diseño clave
- **Assets como archivos reales del paquete**: las skills viven en `cortex/autopilot/skills/` en lugar de strings inline en `cortex_workspace.py`. Esto permite versionarlas junto al código y leerlas dinámicamente.
- **Instalación opcional**: `ensure_cortex_workspace(..., autopilot=True)` copia los archivos a `.cortex/skills/`. El default `autopilot=False` mantiene el comportamiento legacy intacto.
- **Prompt builder separado**: `build_autopilot_prompts()` es independiente de `build_all_prompts()`, permitiendo que los harnesses decidan cuándo inyectarlas.
- **Presupuesto de tokens**: la meta-skill tiene ~480 palabras, bien por debajo del límite de 1500.

## Tests
- `pytest tests/unit/autopilot/test_skills_assets.py` — 14/14 passed.
- Suite completa Autopilot — 161/161 passed (sin regresiones).

## Incidentes y resoluciones
**Ninguno.** La integración fue directa porque `WorkspaceLayout` ya centralizaba la resolución de `skills_dir`, y `get_skill_prompt()` ya soportaba fallback cuando un skill no existe en el workspace.
