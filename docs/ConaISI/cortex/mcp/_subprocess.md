# cortex/mcp/_subprocess.py

## Qué tiene adentro

- **Ruta de código:** `cortex/mcp/_subprocess.py` (189 líneas).
- **Módulo Python:** `cortex.mcp._subprocess`.
- **Docstring del módulo:** Defensive subprocess helpers for the Cortex MCP server.
- **Clases definidas:**
  - `Result`
    - Outcome of a defensive subprocess call.
- **Funciones de módulo:**
  - `_windows_creation_flags()` — ``CREATE_NEW_PROCESS_GROUP`` en Windows, 0 en otros OS.
  - `safe_run(cmd)` — Run a subprocess defensively. NEVER raises.
  - `_decode_capture(value)` — Devuelve string seguro a partir de captures que pueden ser bytes o None.
  - `git_branch_exists(branch)` — Pre-validar que una rama git existe ANTES de invocar ``git diff``.

## Para qué sirve

Defensive subprocess helpers for the Cortex MCP server.

Fase 1 — Capa 3 del plan multi-IDE & MCP hardening.

Razon de existir:

El MCP server ejecuta subprocesos (`git diff`, etc.) dentro de sus handlers.
Sin proteccion, una llamada que se cuelga (rama inexistente, lock de git,
antivirus de Windows escaneando .git/) bloquea el event loop async del
server entero, causando el incidente del 2026-05-15.

Este modulo provee un helper unico ``safe_run`` que:

1. Aplica timeout enforced (no se puede colgar indefinidamente).
2. En Windows, usa ``creationflags=CREATE_NEW_PROCESS_GROUP`` para evitar
   procesos zombie con handles del pipe MCP cuando el padre muere.
3. Envuelve TODAS las exceptions en un ``Result`` estructurado — nunca
   propaga al handler MCP.
4. Devuelve un ``Result`` con ``ok: bool``, ``stdout``, ``stderr``,
   ``returncode``, ``error``. El caller siempre tiene un objeto sobre el
   que decidir.

Tambien provee ``git_branch_exists`` como pre-validacion barata para
``cortex_verify_session_claims`` y otros handlers que dependen de una
rama base.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `subprocess`, `sys`, `__future__`, `dataclasses`, `pathlib`

### Envía a

- Ningún otro módulo `cortex.*` lo importa por nombre de módulo en el AST de `cortex/` (puede ser entrypoint CLI, script, o import dinámico).

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 189.
Docstrings de símbolos públicos:
- `safe_run`: Run a subprocess defensively. NEVER raises.
- `git_branch_exists`: Pre-validar que una rama git existe ANTES de invocar ``git diff``.

---
Fuente: código de `cortex/mcp/_subprocess.py` (AST + grafo de imports internos). No se usó documentación previa.
