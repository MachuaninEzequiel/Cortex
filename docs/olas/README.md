---
title: Olas de desarrollo pre-adopters
date: 2026-05-13
audience: Agente Cortex en sesiones futuras (cuando este contexto ya se haya perdido) + dev humano
context_window_assumption: La sesión que ejecute estos planes no va a tener el contexto pleno del repo que tengo hoy.
---

# Olas de desarrollo Cortex — camino a los primeros early adopters

Este directorio contiene **planes de ejecución autosuficientes** para llevar Cortex de su estado actual al nivel "framework funcionando completamente para early adopters". Cada documento describe **una ola** de trabajo: objetivo, contexto, pasos concretos con archivos y líneas, criterios de cierre y checklist final.

## Contexto general (leer antes que cualquier ola)

**Negocio.** El usuario (Ezequiel) tiene reunión próxima con **dos startups** que van a ser los **primeros early adopters** del framework. La indicación es:

- "No es demo — debe funcionar completamente."
- "No hay vault de ningún tipo, ningún usuario con Cortex instalado — va a ser la primera vez de alguien usándolo."
- La instalación que se recomienda a los adopters es la **completa**: parte agentic + WebGraph + Pipeline.
- IDEs target priorizados: **Claude Code, OpenCode, Pi, Codex**. Cursor existe en el repo pero no es prioridad.
- Stacks de los adopters: **desarrollo web** (no especificado más). No asumir Python.

**Regla operativa permanente.** "Dejar las cosas terminadas sin deuda técnica es una prioridad siempre". Cada ola se cierra al 100% antes de pasar a la siguiente. La única excepción: cuando cerrar algo implicaría re-trabajar después (caso explícito y documentado).

**Estado del repo al iniciar las olas (2026-05-13):**

- Ola 0 ya tiene 2 ítems cerrados (ver `ola-0-bugs-criticos.md`):
  - `autopilot finish --auto` persiste session note (transaccional).
  - Indexing obligatorio en todo flujo de escritura (`SpecService`, `SessionService`, `PRService.write_pr_docs`, Autopilot).
- Suite global: 789 passed, 6 skipped, 0 failed.
- Versión: 0.3.0 Alpha (pyproject + `__init__.py` unificados).
- Layout del repo Cortex en sí: **legacy** (config.yaml en raíz, vault/ y .memory/ en raíz, .cortex/ solo para agente).

**Documento de save state previo a las olas:** `docs/review/cortex-save-state.md` — releelo antes de tocar nada. Tiene mapa completo de módulos, riesgos, contratos y archivos por tarea.

## Índice de olas

| Ola | Archivo | Objetivo | Bloquea a |
|-----|---------|----------|-----------|
| 0 | `ola-0-bugs-criticos.md` | Cerrar bugs que rompen el flujo tripartito antes de cualquier demostración | 1, 2, 3, 4 |
| 1 | `ola-1-ides-y-mcp.md` | Los 4 IDEs target (Claude Code, OpenCode, Pi, Codex) funcionan end-to-end con MCP + workflow tripartito | 2 (parcial), 3 |
| 2 | `ola-2-pipelines-y-workflows.md` | Los 5 workflows CI/CD ejecutan limpio en PR real con stack web (no solo Python) | 3 |
| 3 | `ola-3-ux-primer-contacto.md` | Setup completo (agent + webgraph + pipeline) desde repo vacío y desde repo con código existente. Doctor verde end-to-end. Onboarding doc preciso | 4 |
| 4 | `ola-4-pulido-final.md` | Bugs cosméticos, README sincronizado con realidad, smoke test del demo path completo | — (cierra el ciclo pre-adopters → 0.4.0) |

## Post-adopters: Tripartita Refinada (0.5.0)

| Ciclo | Archivo | Objetivo | Estado |
|-------|---------|----------|--------|
| Tripartita Refinada | `tripartita-refinada.md` | Hardening de la promesa central: handoffs estructurados, Verification Gate, confidence labels, CONTEXT.md, anti-rationalization. Materialización completa en los 4 IDEs target. | ✅ CERRADA (2026-05-14) — bump a 0.5.0 |

Las olas pre-adopters (0.4.0) y Tripartita Refinada (0.5.0) usan **convenciones de planificación distintas**:
- Olas: un archivo monolítico por ola con plan + checklist al final.
- Tripartita Refinada: 7 planes ejecutables en `docs/agents/plan/<NN>-*.md` + 7 bitácoras de implementación en `docs/agents/implementacion/<NN>-*.md` + 1 doc de cierre acá. Esa convención es la recomendada para ciclos futuros (post-0.5.0) porque permite parallelismo en planes y trazabilidad explícita entre el "qué hacer" y el "qué se hizo".

## Cómo usar estos documentos en una sesión futura

1. **Leer `docs/review/cortex-save-state.md`** para recuperar el mapa mental.
2. **Leer este README** para entender el contexto de negocio.
3. **Identificar la ola activa**: revisar el estado de los checklists al final de cada `ola-*.md`. La ola más alta con checklist no cumplido es la activa.
4. **Ejecutar la ola en orden estricto.** No saltearse pasos. Cada paso tiene archivos y líneas explícitos.
5. **Marcar el checklist con `[x]`** al completar cada item. No marcar sin verificar.
6. **Antes de cerrar una ola**: correr la suite completa (`pytest tests/unit tests/integration tests/e2e --no-cov`) y dejar el resultado documentado en el archivo.

## Convenciones

- Rutas en estos documentos son **relativas al repo Cortex** (`D:\DevSecDocOps\DevSecDocOps-3erCortex\cortex-repo\cortex` en la máquina del autor).
- Cuando un paso dice "verificar end-to-end", significa **probar con CLI real**, no solo con tests.
- Cuando un paso dice "obligatorio", significa que sin eso la ola no cierra. No hay tibieza.
- Comentarios de código en español o inglés según contexto del módulo. No mezclar dentro de un mismo archivo.
- Tests que validan cierre van en `tests/e2e/scenarios/test_ola_<N>_*.py` cuando son nuevos. Tests que cubren cambios puntuales viven en su módulo.

## Restricciones que aplican a todas las olas

1. **Indexing obligatorio.** Toda escritura de documentación debe persistir + indexar en la misma transacción. Si una nueva feature escribe a `vault/` y no indexa, **no se mergea**. Ver `feedback_autopilot_persistence.md` en memoria del proyecto.
2. **WorkspaceLayout siempre.** No hardcodear paths del estilo `.memory/`, `vault/`, `.cortex/skills/`. Todo va por `WorkspaceLayout.discover()` o sus properties. Excepción: paths que GitHub fuerza (ej. `.github/workflows/`).
3. **Path safety.** Toda escritura desde input externo (CLI args, MCP arguments, PR body) pasa por `cortex.security.paths.resolve_safe` + `validate_under_root`.
4. **Sin breaking changes públicos sin alerta.** Cualquier cambio en el contrato de un servicio público (CLI flag, MCP tool, AgentMemory method) debe estar registrado en `CHANGELOG.md` antes de cerrar la ola.
5. **Stack-agnostic en pipeline.** Los workflows no deben asumir Python. Plantillas deben detectar stack via `ProjectDetector` y adaptar comandos.

## Definición de "framework funcionando completamente"

Para los early adopters, el framework está listo cuando:

- Un usuario clona Cortex, ejecuta `pipx install --editable .` (o equivalente), corre `cortex setup full` en su repo web vacío y obtiene un workspace `.cortex/` operativo con agentic + webgraph + pipeline configurados.
- Los 4 IDEs target reconocen y usan Cortex como servidor MCP sin pasos manuales adicionales más allá del `cortex inject --ide <name>`.
- El flujo tripartito (sync → SDDwork → documenter) funciona desde el primer prompt del agente en cualquiera de los 4 IDEs.
- Una session note generada por `autopilot finish --auto` (o por `save-session` manual) aparece inmediatamente en `cortex search` sin sync manual.
- Los 5 workflows CI/CD pasan en un PR real con stack web.
- `cortex doctor --scope all --strict` retorna verde sin warnings críticos.
- `cortex webgraph serve` muestra el grafo del nuevo vault con nodos legibles.

Cualquier desvío de esto es deuda que debe quedar registrada en el archivo de la ola pertinente.
