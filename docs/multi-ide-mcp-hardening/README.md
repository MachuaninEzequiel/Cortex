# Plan — Multi-IDE Uniformity & MCP Hardening

**Fecha de inicio:** 2026-05-15
**Origen:** Incidente reproducido por el creador de Cortex durante prueba real en el proyecto cliente `D:\ClubBelgrano-Prode` (refactor "Prode Club Belgrano"). El subagente `cortex-documenter` quedo colgado 14 minutos sin escribir un byte, y el MCP server de Cortex se desconecto entero a mitad del cierre.
**Estado:** Listo para ejecutar.

---

## 1. Resumen ejecutivo

Durante una sesion real de uso de Cortex en Claude Code, el creador descubrio cuatro fallas distintas:

1. `cortex setup full` no incluye seleccion interactiva de IDE — obliga a correr `cortex setup agent` por separado.
2. El MCP tool `cortex_delegate_task` esta hardcodeado a `opencode` y devuelve no-op silencioso en cualquier otro IDE.
3. El subagente `cortex-documenter` lanzado via `Task tool` nativo de Claude Code quedo colgado por completo.
4. El MCP server de Cortex cayo entero a mitad de la operacion, dejando todas las tools `mcp__cortex__*` indisponibles.

Las cuatro causas no son independientes: 3 y 4 se encadenan, y 2 revela un acoplamiento conceptual erroneo entre Cortex y un IDE especifico (opencode). Este plan ataca las causas, no los sintomas.

---

## 2. Principios rectores (no negociables)

1. **Cortex se comporta igual en todos los IDEs.** Los prompts canonicos de agentes y subagentes son **identicos**; solo cambia el **formato de instalacion** que cada IDE entiende.
2. **Single Source of Truth (SSoT) de prompts:** Las funciones `render_*` en `cortex/setup/cortex_workspace.py` son la unica fuente. Los archivos en `.cortex/subagents/*.md`, `.cortex/skills/*.md` y `cortex-pi/.pi/agents/*.md` son **outputs** de esos renders. Si difieren del render, estan desactualizados — el render es la verdad. **Refinado durante Fase 0; ver `HALLAZGOS-INESPERADOS.md` H-1.**
3. **El MCP server debe funcionar siempre que el IDE este abierto en un proyecto con Cortex instalado.** No hay fallback manual. Si el MCP cae, la operacion del agente aborta con error claro al usuario — nunca degrada features ni escribe markdown a mano.
4. **Cero deuda tecnica en cada fase.** Una fase NO se cierra si deja TODO comments, shims temporales, tests faltantes, codigo muerto, o features a medio implementar. Una fase puede dejar trabajo para la fase **siguiente** solo si esta documentado como dependencia explicita (no como deuda).
5. **Comportamiento de Cortex es UNIFORME — instalacion es ESPECIFICA por IDE.** Lo unico que el adapter de cada IDE puede modificar es: (a) el formato del archivo de configuracion del IDE, (b) la traduccion de nombres canonicos de tools al nombre que el IDE expone, (c) la sintaxis de descubrimiento del MCP server. NUNCA el cuerpo del prompt.

---

## 3. Estructura del plan

```
docs/multi-ide-mcp-hardening/
├── README.md                          ← Este archivo: vision, dependencias, gates
├── FASE-0-inventario.md               ← Inventario read-only previo (plan de la fase)
├── FASE-0-REALIZACION.md              ← Como se ejecuto Fase 0 + handoff
├── INVENTARIO.md                      ← Output formal de Fase 0
├── HALLAZGOS-INESPERADOS.md           ← Descubrimientos imprevistos + cambios realizados
├── MATRIZ-NATIVA-IDES.md              ← Estructura nativa REAL verificada contra docs oficiales 2026
├── FASE-1-mcp-defensivo.md            ← Robustecer MCP server (4 capas)
├── FASE-2-health-check.md             ← cortex_ping + last_error_seen
├── FASE-3-canonical-tools.md          ← Vocabulario canonico de tools
├── FASE-4-adapters-ssot.md            ← Adapters leen de SSoT y traducen
├── FASE-5-cleanup-delegate-mcp.md     ← Remover delegate experimental del MCP
├── FASE-6-setup-full-interactivo.md   ← Prompt interactivo de IDE en setup full
└── FASE-7-validacion-e2e.md           ← Smoke test multi-IDE + reproducir incidente
```

Cada fase es un archivo autocontenido con: **Objetivo, Pre-requisitos, Tasks numeradas, Archivos involucrados, Criterios de aceptacion, Gate de cero-deuda-tecnica, Riesgos y mitigaciones, Handoff a la siguiente fase.**

---

## 4. Orden de ejecucion recomendado

```
FASE 0 (Inventario, read-only)
   │
   ├──> FASE 1 (MCP defensivo) ──> FASE 2 (Health-check)
   │                                         │
   ├──> FASE 3 (Canonical tools)             │
   │           │                             │
   │           └──> FASE 4 (Adapters SSoT) <─┘
   │                       │
   │                       └──> FASE 5 (Cleanup delegate MCP)
   │
   ├──> FASE 6 (Setup full interactivo)  [independiente, low-risk]
   │
   └────────────────────────────────────────────> FASE 7 (Validacion E2E)
```

### Razon del orden

- **Fase 1 antes que cualquier feature nuevo.** El MCP server debe ser confiable antes de exponer nuevos tools (ping) o nuevos contratos (multi-IDE). Es la fundacion del invariante "MCP siempre funciona".
- **Fase 2 inmediatamente despues de Fase 1.** El health-check necesita el server defensivo para ser confiable; en orden inverso el ping podria reportar OK mientras el server esta en estado degradado.
- **Fase 3 antes que Fase 4.** El vocabulario canonico es prerequisito tecnico de los adapters.
- **Fase 5 despues que Fase 4.** No se puede eliminar `cortex_delegate_task` del MCP hasta que los adapters generen la delegacion nativa por IDE — sino quedan callers sin destino.
- **Fase 6 puede ejecutarse en cualquier momento** despues de Fase 0; es independiente. La pongo al final solo para evitar choques con Fase 4 (ambas tocan area de setup/adapters).
- **Fase 7 al cierre.** Valida el sistema entero contra el incidente original.

---

## 5. Reglas de ejecucion

1. **Una fase a la vez.** No se avanza sin cerrar el gate de salida de la fase actual.
2. **El gate de cero-deuda-tecnica es invariante.** Si una task descubre deuda preexistente que NO estaba en alcance, se documenta como `ARRASTRE-N.md` dentro de la carpeta de la fase y se decide con el creador si entra en alcance o se difiere a una fase posterior **explicitamente**. Diferir requiere que la fase posterior la liste como task propia. No se difiere a "alguna vez".
3. **Cada task se commitea en una rama** `multi-ide-hardening/fase-N-task-M`.
4. **Antes de mergear una fase**, los tests de la fase + smoke tests de las fases anteriores deben pasar en CI.
5. **El creador es el unico aprobador** del cierre de fase y del cumplimiento del gate de cero-deuda.

---

## 6. Definicion operativa de "cero deuda tecnica"

Para cerrar una fase, **TODO** lo siguiente debe ser cierto:

- [ ] Cero `TODO`, `FIXME`, `XXX`, `HACK` agregados por la fase (los preexistentes se documentan en `ARRASTRE-N.md`).
- [ ] Cero shims temporales, flags de feature transitorios, o paths legacy paralelos.
- [ ] Cero codigo muerto (funciones, imports, branches inalcanzables).
- [ ] Cero comentarios `removed` / `kept for compat` / `legacy` sin issue rastreable.
- [ ] Cada cambio de comportamiento publico tiene test que falla sin el fix y pasa con el fix.
- [ ] Linter (`ruff`/`mypy` segun config del repo) sin warnings nuevos.
- [ ] CHANGELOG o seccion equivalente actualizada.
- [ ] El comando `cortex doctor` (cuando exista) reporta verde para la feature tocada.

---

## 7. Mapeo problema -> fase

| Problema del incidente | Fase que lo resuelve |
|---|---|
| `cortex setup full` no es interactivo | Fase 6 |
| `cortex_delegate_task` es no-op fuera de opencode | Fase 4 + Fase 5 |
| Subagente `cortex-documenter` colgado | Fase 1 + Fase 2 (causa: MCP cayendose mientras el subagente esperaba respuesta) |
| MCP server desconectandose | Fase 1 |
| Drift entre `cortex-pi/.pi/agents/` y `.cortex/subagents/` | Fase 0 (deteccion) + Fase 4 (resolucion) |
| Falta de pre-flight check antes de operaciones costosas | Fase 2 |

---

## 8. Riesgos transversales

| Riesgo | Mitigacion |
|---|---|
| El refactor del MCP server (Fase 1) introduce regresiones en clients en produccion | Tests de contrato exhaustivos antes de mergear; smoke en Claude Code + opencode antes del cierre. |
| El cambio de SSoT (Fase 4) deja IDEs con instalaciones obsoletas | El comando `cortex setup` re-inyecta perfiles idempotentemente; documentar al cierre que los adopters corran `cortex setup agent` para refrescar. |
| Eliminar `cortex_delegate_task` (Fase 5) rompe a algun adopter que lo este usando | Fase 0 inventaria callers; si hay alguno se contacta antes del cierre de Fase 5. |
| El plan se queda a mitad y deja al sistema en estado mixto | El gate de cero-deuda hace que cada fase sea independientemente mergeable; abandonar entre fases nunca deja el sistema peor. |

---

## 9. Progreso global

| Fase | Titulo | Semaforo | Estado |
|------|--------|----------|--------|
| FASE 0 | Inventario | Verde | **Completada y firmada (2026-05-15)** — output: `INVENTARIO.md`, `FASE-0-REALIZACION.md`, `HALLAZGOS-INESPERADOS.md` (H-1 a H-6), `MATRIZ-NATIVA-IDES.md` (con 4 decisiones firmadas por el creador en seccion 4). 1 archivo regenerado (`.cortex/subagents/cortex-documenter.md` desde su render). Fase 3 y Fase 4 desbloqueadas. |
| FASE 1 | MCP defensivo | Rojo | **Completada (2026-05-15)** — 4 capas defensivas + ARRASTRE-1 resuelto + cleanup del executor + fix de `asyncio.get_running_loop`. 23 tests nuevos, 97 preexistentes sin regresion (120 totales). Linter ruff verde. Output: `cortex/mcp/_subprocess.py` (nuevo), `cortex/embedders/onnx.py` (refactor), `cortex/mcp/server.py` (integracion + shutdown), `docs/architecture/mcp-server-resilience.md`, `FASE-1-REALIZACION.md`. |
| FASE 2 | Health-check | Amarillo | **Completada (2026-05-15)** — `cortex_ping` con `last_error_seen` rolling buffer. 14 tests nuevos, 120 preexistentes sin regresion (134 totales). Linter verde. Latencia p99 <50ms validada. Output: `cortex/mcp/server.py` (tool + handler + tracking), `tests/unit/mcp/test_ping.py`, `docs/architecture/mcp-server-resilience.md` (Capa 5), `FASE-2-REALIZACION.md`. |
| FASE 3 | Canonical tools | Amarillo | **Completada (2026-05-15)** — `cortex/ide/canonical_tools.py` con vocabulario (13 tools: 3 fs + 1 shell + 9 MCP) + matriz para los 2 IDEs validados (claude_code, opencode). 49 tests nuevos, 134 preexistentes sin regresion (183 totales). Linter verde. Output: `cortex/ide/canonical_tools.py`, `tests/unit/ide/test_canonical_tools.py`, `docs/architecture/canonical-tools.md`, `FASE-3-REALIZACION.md`. |
| FASE 4 | Adapters SSoT | Amarillo | **Completada (2026-05-15)** — 5 adapters trabajados segun decisiones firmadas: claude_code (inyecta `tools` traducido), opencode (migrado a `permission`), codex (rediseno: AGENTS.md root + MCP TOML), cursor (rediseno: 3 subagents canonicos), pi (NO tocado). Eliminado hibrido `cortex-SDDwork-cursor.md` + `build_cursor_prompts`. Pre-flight check inyectado en renders. Registry con metadata de validacion. 13 tests nuevos + 19 actualizados + 14 obsoletos eliminados. **255 tests verdes**, linter ruff clean. Output: `cortex/ide/adapters/{claude_code,opencode,codex,cursor}.py`, `cortex/setup/cortex_workspace.py` (renders), `cortex/ide/registry.py`, `cortex/ide/prompts.py`, `cortex/ide/__init__.py`, `tests/unit/ide/test_adapters_phase4.py`, `FASE-4-REALIZACION.md`. |
| FASE 5 | Cleanup delegate MCP | Amarillo | **Completada (2026-05-15)** — 3 tools MCP (`cortex_delegate_task`, `cortex_delegate_batch`, `cortex_get_task_result`) + 4 metodos privados eliminados; vocabulario canonico depurado; skill `cortex-SDDwork.md` regenerada sin referencia al delegate; tests obsoletos eliminados; CHANGELOG `[0.6.0]` + docs autopilot actualizados con nota retroactiva. Autopilot `DelegationEngine` (two-stage review legitimo) PRESERVADO. **355 tests verdes**, linter ruff clean. ARRASTRE-2 documentado (F841 preexistente en test_artefact_integrity.py:52). Output: `cortex/mcp/server.py`, `cortex/ide/canonical_tools.py`, `cortex/setup/cortex_workspace.py`, `.cortex/skills/cortex-SDDwork.md`, tests, `CHANGELOG.md`, `docs/architecture/canonical-tools.md`, `FASE-5-REALIZACION.md`. |
| FASE 6 | Setup full interactivo | Verde | **Completada (2026-05-15)** — helper compartido `cortex/cli/_setup_helpers.py:select_ide_interactive`. `setup_agent` y `setup_full` ahora invocan el helper (cero duplicacion). `setup_agent` ahora soporta `--non-interactive` (paridad con `setup_full`). 16 tests nuevos (10 helper + 6 integracion CLI), 718 preexistentes sin regresion (**734 totales**). Linter verde. ARRASTRE-3 documentado (UP042 preexistente en `DoctorScope`). Output: `cortex/cli/_setup_helpers.py`, `cortex/cli/main.py`, `tests/unit/cli/test_setup_helpers.py`, `tests/unit/cli/test_setup_commands_phase6.py`, `FASE-6-REALIZACION.md`. |
| FASE 7 | Validacion E2E | Amarillo | **Completada (2026-05-15)** — replay programatico del incidente del 2026-05-15: **NO se reproduce**. Smoke multi-IDE 5/5 verde. Stress test del MCP server: p99 <200ms en 500 secuenciales, 50 concurrentes <5s. 17 tests nuevos (7 replay + 5 smoke + 5 stress). Suite expandida: **751 tests verdes**. Cero deuda introducida por el plan. ARRASTRES preexistentes documentados (F841, UP042, asyncio.get_event_loop). Output: `tests/integration/test_incident_replay_2026_05_15.py`, `tests/integration/test_smoke_multi_ide_phase7.py`, `tests/integration/test_mcp_stress_phase7.py`, `CIERRE.md`, `FASE-7-REALIZACION.md`. **PLAN COMPLETO CERRADO.** |

Leyenda:
- **Verde:** bajo riesgo, alcance acotado, sin impacto en runtime de adopters.
- **Amarillo:** cambios visibles para el adopter, requieren smoke test antes de cerrar.
- **Rojo:** toca el invariante critico (MCP siempre disponible). Cero margen de error.
