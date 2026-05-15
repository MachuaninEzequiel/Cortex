# FASE 0 — REALIZACION

**Fecha de ejecucion:** 2026-05-15
**Output formal:** `INVENTARIO.md`
**Estado:** Completada — items pendientes de firma del creador documentados al final.

Este documento describe **como se ejecuto** la Fase 0 (proceso) y registra las **decisiones y hallazgos en el camino**. El output formal con datos concretos es `INVENTARIO.md`. Este documento sirve para que la proxima persona que lea el plan entienda no solo el "que" sino tambien el "como" y el "por que" de los hallazgos.

---

## 1. Plan de ejecucion seguido

Las 5 tasks definidas en `FASE-0-inventario.md` se ejecutaron secuencialmente, cada una con un objetivo de output discreto, todas read-only (cero modificaciones de codigo).

| Task | Output |
|---|---|
| 0.1 | Lista exhaustiva de copias de prompts + diff por par. |
| 0.2 | Tabla de adapters de IDE con mecanismo de inyeccion, MCP key, vocabulario de tools. |
| 0.3 | Lista de callers del delegate experimental clasificados como prod/test/doc. |
| 0.4 | Inventario del MCP server (tools, subprocess, lazy load, logging, concurrencia). |
| 0.5 | Consolidar en `INVENTARIO.md` y producir este documento de realizacion. |

---

## 2. Como se realizo cada task

### 2.1 Task 0.1 — Inventariar copias de prompts canonicos

**Pasos ejecutados:**

1. Glob exhaustivo en el repo de archivos `.md` bajo paths que contengan `subagents/`, `agents/`, `skills/`, `.pi/`, `.cortex/`. Resultado: ~50 archivos candidatos.
2. Clasificacion manual en 4 categorias: subagentes Cortex (cross-IDE), skills Cortex (cross-IDE), agentes/skills exclusivos de pi, skills genericos no-Cortex (obsidian/json-canvas/etc).
3. Para cada par con el mismo nombre logico, `diff -q` y luego `diff` detallado.
4. Cuando el diff inicial mostro "todas las lineas distintas", verificacion con `file` y `wc -lc` revelo CRLF vs LF. Recalculo de hashes con `tr -d '\r'` para hash canonicalizado.
5. Para los archivos con drift real (post-canonicalizacion), grep en `cortex/` para validar cual nombre de funcion es el real.

**Hallazgos clave que cambiaron el planteo del plan:**

- **Hallazgo 1:** `cortex-code-explorer.md` y `cortex-code-implementer.md` son IDENTICOS modulo CRLF/LF entre `.cortex/subagents/` y `cortex-pi/.pi/agents/`. El "drift" reportado por `diff` era 100% line endings.
- **Hallazgo 2:** `cortex-documenter.md` SI tiene drift semantico real: la SSoT cita funciones que **no existen en el codigo**. El nombre real (`write_session_note_canonical`) solo aparece en la copia de pi. Esto invierte la asuncion del plan ("la SSoT esta correcta y pi puede estar drift") — la realidad es la contraria.
- **Hallazgo 3:** existe `cortex-SDDwork-cursor.md` como SKILL en la SSoT — variante por IDE en la misma SSoT, viola el principio rector. No estaba contemplado por el plan.
- **Hallazgo 4:** `cortex-sync` y `cortex-SDDwork` existen tambien como AGENT en `cortex-pi/.pi/agents/`, con contenido distinto a su version SKILL. Esto es una distincion conceptual (skill vs agent) que el plan no consideraba — abre pregunta arquitectural para discutir con el creador.
- **Hallazgo 5:** existen 4 archivos huerfanos en `cortex-pi/.pi/agents/` sin contraparte en `.cortex/subagents/` (`cortex-SDDwork`, `cortex-sync`, `cortex-security-auditor`, `cortex-test-verifier`). Decision sobre migracion pendiente.

**Tiempo aproximado:** 30 minutos.

### 2.2 Task 0.2 — Inventariar adapters de IDE y vocabulario de tools

**Pasos ejecutados:**

1. `ls cortex/ide/adapters/*.py` — listado de 11 adapters.
2. `wc -l` por adapter para tener orden de magnitud.
3. Lectura completa de los 4 adapters mas grandes / mas relevantes: `claude_code` (194), `opencode` (162), `codex` (246), `cursor` (111), `pi` (169).
4. Para los 6 restantes (mas pequeños y/o MCP-only): grep dirigido para extraer `name`, `get_config_paths`, MCP key, y si referencian la SSoT (`subagents_dir`, `.cortex/subagents`, `get_subagent_prompt`).

**Hallazgos clave:**

- **Adapter pi tiene un mecanismo `sync_canonical_subagents`** que ya implementa el principio rector: copia desde `.cortex/subagents/` a `cortex-pi/.pi/agents/` antes de inyectar. El plan original asumia que `cortex-pi/.pi/agents/` era una "copia paralela mal mantenida" — la realidad es que es un **staging directory managed**. Reescribi la decision en INVENTARIO 5.7.
- **Adapter cursor usa `build_cursor_prompts()`** y NO lee de la SSoT. Esto es exactamente el anti-patron que el principio rector prohibe. Fase 4 debe arreglarlo.
- **Adapter codex** documenta explicitamente que "Codex has no native Task tool" (linea 113 del adapter). Esto valida que el mecanismo de delegacion debe ser declarativo por adapter (algunos lo soportan, otros no) — coincide con la propuesta de Fase 4 Task 4.4.
- **Hay 3 patrones de tools en MCP** segun como cada IDE los nombra: prefijo `mcp__cortex__` (claude_code), nombre directo (opencode), descubrimiento dinamico sin frontmatter (codex, cursor, vscode, los MCP-only).
- **6 de los 11 adapters son MCP-only** (solo configuran MCP server discovery, no inyectan profiles): windsurf, zed, hermes, antigravity, claude_desktop. Son irrelevantes para la SSoT de prompts; relevantes solo para Fase 4 Task 4.3 en lo que respecta a config de MCP.

**Tiempo aproximado:** 25 minutos.

### 2.3 Task 0.3 — Inventariar callers del delegate experimental

**Pasos ejecutados:**

1. Grep regex amplio: `cortex_delegate_task|cortex_delegate_batch|_delegate_task|_delegate_batch|_store_task_result|_get_task_result|cortex_get_task_result|register_task|get_task_result`.
2. Triage manual de cada hit en 5 categorias: produccion, tests, docs, plan en si (auto-referencia ignorada), historia (CHANGELOG).
3. Inspeccion de `cortex/autopilot/delegation.py` para entender si es parte del delegate experimental o un sistema independiente.

**Hallazgos clave:**

- **Existen DOS sistemas con nombres similares:** el "MCP Delegate" (a eliminar) y el "Autopilot Delegation Engine" (a preservar). El plan original los confundia. Documente la distincion en INVENTARIO seccion 3.1.
- **El template `cortex/setup/cortex_workspace.py:249-250` GENERA la skill canonica con referencia hardcoded a `cortex_delegate_task`.** Esto significa que Fase 5 no solo debe editar la skill canonica — debe editar PRIMERO el template, sino el siguiente `cortex setup` revierte el cambio. Lo agregue en INVENTARIO 5.6.
- **5 sets de tests dependen del delegate** — cada uno requiere decision distinta (eliminar/modificar/preservar/revisar).
- **Docs historicos** (`docs/autopilot/`) referencian el delegate. Decision: preservar como historia pero anotar en cada uno que los tools fueron retirados.

**Tiempo aproximado:** 20 minutos.

### 2.4 Task 0.4 — Inventariar shape del MCP server

**Pasos ejecutados:**

1. Grep estructurado por categoria sobre `cortex/mcp/server.py`:
   - Tools registrados (`name="cortex_`)
   - Handler dispatch (`elif name ==`)
   - Subprocess (`subprocess\.|asyncio\.create_subprocess_exec|shutil\.which`)
   - Logging (`logging\.|StreamHandler|FileHandler|basicConfig`)
   - Concurrencia (`asyncio\.Lock|threading\.|ThreadPool|asyncio\.gather`)
   - Init/stdio (`stdio_server|InitializationOptions`)
2. Inspeccion focal de las lineas 50-72 (init de logging y stdout hijack).
3. Verificacion en `cortex/semantic/vector_cache.py` de la existencia de locks alrededor de la carga del modelo.

**Hallazgos clave:**

- **Bug colateral inesperado:** `cortex_search_vector` esta REGISTRADO en `handle_list_tools` (linea 113) pero **no tiene handler en el dispatch**. Solo `cortex_search` existe como branch. Esto es un bug pre-existente que cae fuera del alcance del plan multi-IDE; lo registre como ARRASTRE-1 en INVENTARIO 5.4 para discusion con el creador (¿se arregla en Fase 1 mientras se refactoriza el server, o plan separado?).
- **Confirmacion del bug latente del logging:** `StreamHandler(sys.stderr)` en linea 55. El server SIEMPRE corre en stdio (linea 1006, no hay branch HTTP), por lo que el "modo stdio" es siempre true. Fase 1 Capa 2 puede simplificarse: eliminar directamente el handler stderr.
- **Confirmacion de la falta de lock alrededor de la carga del modelo ONNX:** `VectorCache` tiene `RLock` solo a nivel de cache (operaciones get/put), no a nivel de inicializacion del modelo. Fase 1 Capa 4 es necesaria.
- **Sin ThreadPoolExecutor:** todo corre en el event loop async. Cualquier `subprocess.run` sincrono o IO bloqueante (carga ONNX, sync_vault) bloquea el loop entero. Fase 1 Capa 1 es el cambio mas grande del plan.
- **stdout hijack** (linea 65-72) solo cubre stdout y solo durante init de AgentMemory. NO protege stderr durante runtime — exactamente donde esta el bug.

**Tiempo aproximado:** 25 minutos.

### 2.5 Task 0.5 — Producir INVENTARIO.md y este documento

**Pasos ejecutados:**

1. Sintesis de los hallazgos de las 4 tasks en un documento estructurado siguiendo la plantilla definida en `FASE-0-inventario.md` Task 0.5 (5 secciones obligatorias).
2. Agregado de seccion 5 "Hallazgos imprevistos" para registrar items que NO estaban en el plan original.
3. Agregado de seccion 6 "Conclusion: matriz de SSoT vs derivados" para dejar explicita la imagen final que el plan necesita.
4. Agregado de seccion 7 "Items para discutir con el creador" con las preguntas abiertas que deben firmarse antes de cerrar la fase.
5. Escritura de este documento de realizacion como complemento del output formal.

---

## 3. Decisiones tomadas durante la realizacion

### 3.1 Decision: tratar el "drift por CRLF/LF" como NO-drift

Cuando `diff -q` reporto que los 3 subagentes diferian, en lugar de aceptar el reporte y registrar 3 drifts, se canonicalizo a LF con `tr -d '\r'` antes de hashear. Resultado: 2 de los 3 son identicos, 1 es drift real.

**Justificacion:** registrar 3 drifts cuando solo hay 1 inflaria el alcance de Fase 4 innecesariamente y enmascarararia el unico drift que importa.

### 3.2 Decision: clasificar `cortex/autopilot/delegation.py` como PRESERVAR

Inicialmente el plan asumia que todos los `_delegate_*`, `_store_task_result`, `_get_task_result`, `register_task`, `get_task_result` formaban parte del delegate experimental. La inspeccion del autopilot revelo que su `DelegationEngine` y funciones asociadas son un motor independiente de two-stage review, NO acoplado a opencode.

**Justificacion:** eliminar ese motor seria sacar funcionalidad legitima del autopilot. El alcance del plan multi-IDE es eliminar el acoplamiento erroneo del MCP a opencode, no rediseñar el autopilot.

### 3.3 Decision: documentar el bug `cortex_search_vector` sin handler como ARRASTRE

El bug podria arreglarse en 2 lineas, pero no esta en alcance del plan multi-IDE. Decisiones discrecionales como "ya que estoy aca, lo arreglo" violan el principio de cero deuda tecnica al revez (introducir cambios fuera de alcance que no estan documentados).

**Justificacion:** se documenta como ARRASTRE-1 para que el creador decida si entra al alcance de Fase 1 o se difiere a un plan separado. Decision explicita > inclusion silenciosa.

### 3.4 Decision: NO eliminar `cortex-pi/.pi/agents/` como categoria

El plan original sugeria "eliminar `cortex-pi/.pi/agents/` como copia paralela". La realidad mostro que pi adapter ya usa esa carpeta como **staging directory managed** (no como SSoT paralela). Eliminarla romperia el adapter pi.

**Justificacion:** Fase 4 debe eliminar **archivos especificos** que se demuestren obsoletos (los 3 shared agents si se mueven todos a `.cortex/subagents/` como SSoT y se regeneran via `sync_canonical_subagents`), pero la carpeta como staging se mantiene. Reflejado en INVENTARIO 5.7.

---

## 4. Cumplimiento del gate de cero deuda tecnica de Fase 0

Verificacion contra el gate definido en `FASE-0-inventario.md`:

| Item del gate | Estado |
|---|---|
| No queda ninguna pregunta abierta sobre "hay mas copias de X?" | OK — la busqueda fue exhaustiva con grep amplio. INVENTARIO seccion 1 documenta TODAS las ubicaciones encontradas. |
| Si Task 0.1 detecto drift, esta documentado en INVENTARIO como input para Fase 4 | OK — INVENTARIO seccion 1.1 + 5.1 lo cubren. |
| Si Task 0.3 detecto callers huerfanizables, esta listado para Fase 5 | OK — INVENTARIO seccion 3 lo cubre con clasificacion prod/test/doc. |
| No hay archivos creados/modificados de codigo. Esta fase es 100% read + 1 documento (+ realizacion) | OK — solo se crearon `INVENTARIO.md` y este `FASE-0-REALIZACION.md`. Cero codigo tocado. |
| Hallazgos imprevistos discutidos con el creador antes de cerrar | **PENDIENTE** — los 4 items de INVENTARIO seccion 7 requieren firma del creador antes de considerar Fase 0 cerrada formalmente. Hasta que se firmen, Fase 0 esta "completada de ejecucion, pendiente de aprobacion". |

---

## 5. Items para handoff a las siguientes fases

### Lo que Fase 1 puede empezar inmediatamente:

- Refactor del MCP server con las 4 capas. INVENTARIO seccion 4 le da el shape exacto a tocar.
- Capa 2 simplificada: eliminar directamente `StreamHandler(sys.stderr)` (hallazgo 4.5).

### Lo que Fase 1 necesita decision del creador:

- ARRASTRE-1 (`cortex_search_vector` sin handler): ¿se incluye o se difiere?

### Lo que Fase 3 puede empezar inmediatamente:

- Crear `cortex/ide/canonical_tools.py`. INVENTARIO seccion 2.2 + 2.3 le da la matriz de tools y nombres por IDE.

### Lo que Fase 4 necesita decision del creador:

- Items 1, 3, 4 de INVENTARIO seccion 7 (dualidad skill/agent, archivos huerfanos pi, matriz SSoT/derivados).

### Lo que Fase 5 necesita decision del creador:

- Items en INVENTARIO seccion 3.3 (que tests preservar/eliminar/modificar caso por caso).

### Lo que Fase 6 puede empezar inmediatamente:

- No depende de Fase 0. Es independiente.

---

## 6. Handoff formal

```yaml
agent: fase-0-inventario
status: completed
artifacts_produced:
  - docs/multi-ide-mcp-hardening/INVENTARIO.md
  - docs/multi-ide-mcp-hardening/FASE-0-REALIZACION.md (este documento)
verified_claims:
  - "10 prompts cross-IDE inventariados con diff canonicalizado"
  - "11 adapters de IDE inventariados con mecanismo de inyeccion, MCP key y vocabulario de tools"
  - "Distincion entre MCP Delegate (eliminar) y Autopilot Delegation Engine (preservar) clarificada"
  - "Shape completo del MCP server documentado: 19 tools, 3 sites de subprocess, 1 bug latente de logging, 0 ThreadPoolExecutor, 0 lock en carga ONNX"
unverified_claims:
  - "(no aplica) — todo el inventario es verificable por grep/diff/read"
contradicted_claims:
  - "Plan original asumia 'cortex-pi/.pi/agents/ es copia paralela mal mantenida'. Realidad: es staging directory managed por pi adapter."
  - "Plan original asumia '.cortex/subagents/ es la SSoT correcta'. Realidad: .cortex/subagents/cortex-documenter.md cita funciones MCP que no existen; la copia de pi tiene los nombres reales."
artifacts_unchanged:
  - cortex/* (cero modificaciones de codigo en esta fase)
context_for_next:
  - "Fase 1 puede empezar; consultar ARRASTRE-1 con el creador antes de cerrar Capa 1"
  - "Fase 3 puede empezar"
  - "Fase 6 puede empezar"
  - "Fase 4 necesita firma del creador en items 1/3/4 de INVENTARIO seccion 7 antes de empezar"
  - "Fase 5 necesita firma del creador en clasificacion de tests (INVENTARIO seccion 3.3) antes de empezar"
suggested_adr: false
suggested_context_terms:
  - "SSoT (Single Source of Truth)"
  - "Staging directory managed (cortex-pi/.pi/agents/ como caso)"
  - "MCP Delegate vs Autopilot Delegation Engine (dos sistemas con nombres similares)"
  - "ARRASTRE-N (deuda preexistente fuera de alcance, documentada para decision explicita)"
```
