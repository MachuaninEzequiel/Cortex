---
title: Análisis maestro post-Olas — Propuesta tripartita revisada
date: 2026-05-13
status: análisis ejecutivo final con perspectiva post-implementación de Olas 0-4
based_on:
  - docs/agents/MEJORA-TRIPARTITO.md
  - docs/agents/ANALISIS-MEJORA-TRIPARTITO.md
  - docs/agents/{1,2,3,4,5}.png
  - Lectura milimétrica del código tras Olas 0-4 (Cortex 0.4.0)
audience: Yo mismo en sesiones futuras + dev humano que retome este trabajo
---

# Análisis maestro — Propuesta tripartita revisada

Este documento integra:

1. La **propuesta original** (`MEJORA-TRIPARTITO.md`) de 9-13 cambios al modelo tripartito.
2. El **análisis crítico previo** (`ANALISIS-MEJORA-TRIPARTITO.md`) — útil pero **anterior** a las Olas 0-4 (Cortex 0.4.0).
3. Mi propia perspectiva tras haber **escrito el indexing transaccional, los IDE adapters, los workflows y el setup non-interactive**. Es decir, conozco el código que el análisis previo solo intuía.

El objetivo es producir un **veredicto operativo definitivo** y un **plan de implementación detallado por superficie** (CLI, MCP, IDEs) que vive en `docs/agents/plan/`.

---

## TL;DR

**De los 13 items de la propuesta original, 7 se implementan, 1 se redefine, 5 se descartan.**

| # | Item | Veredicto previo | **Veredicto definitivo** | Cambio |
|---|------|-----------------|--------------------------|--------|
| 2.1 | Signal > Noise en documenter | ✅ Aplicar | ✅ **Aplicar Tripartita Refinada** | sin cambio |
| 2.2 | ADR 3 criterios | ✅ Aplicar | ✅ **Aplicar Tripartita Refinada** | sin cambio |
| 2.3 | CONTEXT.md como capa léxica | ❌ Descartar | 🟡 **Redefinir** como guía de estilo (no capa) | promovido a "implementar como prompt asset" |
| 2.4 | Verification Gate | ✅ Aplicar | ✅ **Aplicar Tripartita Refinada** | sin cambio |
| 2.5 | Handoff Mode | ✅ Aplicar | ✅ **Aplicar Tripartita Refinada** | sin cambio |
| 2.6 | Progressive disclosure | ❌ Descartar | ❌ **Descartar** | sin cambio |
| 3.1 | Lexical boost en RRF | ❌ Descartar | ❌ **Descartar** | sin cambio |
| 3.2 | Confidence levels | ⚠️ Postergar | 🟡 **Aplicar parcial** post-Verification Gate | promovido a Tripartita Refinada fase 2 |
| 3.3 | Contradiction detection | ❌ Descartar | ❌ **Descartar** | sin cambio |
| 3.4 | Memory hygiene (cortex-prune) | ⚠️ Postergar | ❌ **Descartar** definitivamente | bajado: temporal decay ya cubre |
| 3.5 | Caveman mode | ❌ Descartar | ❌ **Descartar** | sin cambio |
| 4.2 | Anti-rationalization signals | ✅ Aplicar | ✅ **Aplicar Tripartita Refinada** | sin cambio |
| 4.3 | Structured YAML handoff | ✅ Aplicar | ✅ **Aplicar Tripartita Refinada** | sin cambio |

**Total para Tripartita Refinada:** 8 cambios (7 process/skill + 1 archivo asset CONTEXT.md como prompt material).

---

## 1. Contexto operativo (lo que es distinto vs el análisis previo)

El `ANALISIS-MEJORA-TRIPARTITO.md` fue escrito el **2026-05-12**. Las Olas 0-4 se ejecutaron entre el 2026-05-13 (este mismo día, mi sesión actual). Cambios concretos entre ese análisis y hoy:

### 1.1 Lo que cambió en el código tras Olas 0-4

- **Autopilot `finish --auto` ahora persiste + indexa transaccionalmente** (Ola 0). Antes el path era un placeholder. **Implicación:** el Verification Gate (2.4) y el Handoff Mode (2.5) tienen ahora una infraestructura sobre la cual apoyarse. Pre-Olas eran solo "buenas ideas"; post-Olas son **necesidades operativas** porque la nota se persiste con autoridad.
- **`IndexingSessionWriter` transaccional con rollback** (Ola 0). Si un draft no pasa el verification gate, no queda archivo huérfano. Esto **convierte el verification gate en un sistema seguro de adoptar**: rechazar una sesión ya no produce side-effects parciales.
- **Codex adapter creado** + IDE tiers (target/community/experimental, Ola 1). El plan de implementación debe diferenciar **cómo cada IDE consume** los nuevos contratos.
- **CLI ↔ template alignment automated test** (Ola 2). Si un nuevo subagent expone un nuevo MCP tool, **se debe sumar al `MCP_TO_CLI` mapping** o el test rompe.
- **`AgentMemory()` descubre layout** (Ola 3). Cualquier helper nuevo de los subagents puede asumir que el WorkspaceLayout está disponible vía discovery.
- **Doc verifier classification fix** (Ola 4). `verify_from_diff` ahora produce particiones mutuamente exclusivas. **Implicación:** el verification gate puede confiar en `verify_from_diff` para diff intelligence sin riesgo de overlap.

### 1.2 Lo que NO cambió pero el análisis previo no vio bien

- **Cortex-pi tiene su propio sistema de teams** (`agent-chain.yaml`, `teams.yaml`). Las 4 cadenas (`cortex-sddwork`, `cortex-hotfix`, `cortex-research`, `cortex-audit`) son explícitas en Pi. El análisis previo trataba al pipeline como uniforme entre IDEs — **es uniforme en concepto pero la materialización en cada IDE es muy distinta**. Plan: ver §3.
- **5 estrategias de context enricher activas** (topic, files, keywords, pr_title, entity_search). Cualquier "boost léxico" tendría que coordinar con ellas. El análisis previo lo descartó por motivos correctos; reafirmamos.
- **Temporal decay en `memory_decay.py`** ya implementa half-life 168h + floor 10% + excepciones por tipo. El item 3.4 (memory hygiene) es **redundante con eso**, no complementario.

### 1.3 Lo que el análisis previo asumió que no tenemos pero sí tenemos

- **Indexing automático e inmediato** post-`save-session`. El previo decía que el problema era "memoria contaminada por session notes verbosas". Eso sigue cierto, pero el origen no es la falta de selective indexing (que ya existe) sino el **prompt del documenter que pide "documenta TODO"**. La solución sigue siendo Signal>Noise (2.1) pero la **urgencia es mayor** post-Ola 0: ahora cada session note va al índice **al instante**, así que la contaminación es inmediata.

---

## 2. Análisis ítem por ítem (refinado)

### 2.1 Signal > Noise — ✅ Aplicar

Sin cambios respecto al análisis previo. El prompt del documenter en `.cortex/subagents/cortex-documenter.md` debe pasar de *"NO OMITAS INFORMACIÓN. Documenta TODO el contexto acumulado"* a *"persistir SOLO el delta cognitivo, referenciar artefactos existentes en vez de duplicarlos"*. Ver `docs/agents/MEJORA-TRIPARTITO.md` para el prompt propuesto.

**Insight post-Ola:** ahora que el `IndexingSessionWriter` persiste + indexa transaccionalmente, una session note inflada **se ve inmediatamente en `cortex search`**. Si un adopter hace `cortex search "JWT auth"` y obtiene 5 session notes que repiten el mismo contenido, la promesa de "memoria limpia" se rompe en su primer uso.

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 1.

### 2.2 ADR 3 criterios — ✅ Aplicar

Sin cambios. La regla de Hard-to-reverse + Surprising + Real-trade-off elimina ADRs triviales.

**Insight post-Ola:** los workflows generados (Ola 2) usan `cortex pr-context generate` que produce ADRs como fallback cuando no hay docs del agente. Si el agente humano + Cortex agent ambos generan ADRs sin criterio, el vault acumula basura. La regla de los 3 criterios debe estar **tanto en el skill del documenter como en el `doc_generator.py`** (fallback). El segundo punto NO estaba en la propuesta original — lo agrego.

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 2.

### 2.3 CONTEXT.md — 🟡 Redefinir (no como capa de retrieval)

**Cambio respecto al análisis previo:** el previo lo descartó completamente. Yo lo **rescato como guía de estilo / prompt asset**, no como tercera capa de retrieval. La diferencia es crucial:

- ❌ **NO:** modificar `HybridSearch._rrf_fuse` para sumar `lexical_boost`. Eso rompe determinismo del RRF y añade fragilidad.
- ✅ **SÍ:** crear `.cortex/CONTEXT.md` como archivo opcional en cada proyecto, inyectarlo **como contenido del prompt del agente** cuando el adopter lo configure. Si el adopter quiere que sus agentes usen "Materialization Cascade" en lugar de "instanciar", lo escribe ahí, y los skills `cortex-sync` y `cortex-documenter` lo cargan al boot.

**Insight post-Ola:** con `WorkspaceLayout.discover()` consolidado en Ola 3, agregar `layout.context_md_path` es trivial. Los IDEs pueden inyectar el contenido en sus profiles cuando corren `cortex inject`. Esto es **proceso, no arquitectura** — exactamente el sweet spot del análisis previo.

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 3 y `plan/03-06-ide-*.md` para cómo cada IDE lo carga.

### 2.4 Verification Gate — ✅ Aplicar (es ahora seguro de adoptar)

El análisis previo lo marcó como crítico. Yo refuerzo: tras Ola 0, el `IndexingSessionWriter` hace rollback si el indexing falla — esto significa que un verification gate que **rechaza la sesión** (lanza excepción antes de finalizar) **no deja side-effects**. Era inseguro pre-Olas; ahora es seguro.

**Insight post-Ola:** el gate puede **ejecutar `cortex verify-docs --vault $vault`** (ya existe en CLI) para hacer cross-check con git diff automáticamente. No hace falta inventar nada — la herramienta de doc verification ya tiene clasificación mutuamente exclusiva (Ola 4).

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 4 + `plan/02-mcp-server-cambios.md` para el nuevo MCP tool `cortex_verify_session_claims`.

### 2.5 Handoff Mode — ✅ Aplicar

Sin cambios respecto al análisis previo. Frontmatter `status: handoff` con campos estructurados (`next-session-needs`, `blockers`, `verified-state`, `unverified-claims`, `suggested-skills`).

**Insight post-Ola:** Autopilot `finish` ya tiene un campo `state.status` (`started | preflight_done | implementation_seen | documented | finished | failed`). Hay que agregar `handoff` al enum. Y el `VaultSessionWriter._build_tags` actualmente etiqueta con `["session", "autopilot"]`; en handoff debería ser `["session", "autopilot", "handoff"]` automáticamente.

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 5 + cambios al schema en `plan/02-mcp-server-cambios.md`.

### 2.6 Progressive Disclosure — ❌ Descartar

Sin cambios. El skill `cortex-documenter.md` actual es ~135 líneas. Dividirlo en 6 archivos añade complejidad sin beneficio. Si tras aplicar 2.1+2.2+2.4+2.5+4.2+4.3 el skill crece >300 líneas, **reconsiderar**.

### 3.1 Lexical Memory boost en RRF — ❌ Descartar

Sin cambios. Razones técnicas insalvables documentadas en el análisis previo. Confirmadas por mi lectura del código de `HybridSearch._rrf_fuse()`.

### 3.2 Confidence Levels — 🟡 Aplicar parcial post-Verification Gate

**Cambio respecto al análisis previo:** el previo lo postergó porque "sin verification gate, los agentes no pueden etiquetar confiablemente". Yo refuerzo y matizo:

- Si implementamos 2.4 (Verification Gate) en Tripartita Refinada fase 1, **el gate produce automáticamente confidence levels como side-product**. Cualquier claim que pasó el gate (read_file + grep en diff) es `verified`; cualquier claim que el implementer reportó pero no se verificó es `asserted`; cualquier claim contradicho por el diff es `contradicted`.
- Implementar 3.2 en Tripartita Refinada fase 2 (después del gate) significa **persistir** lo que el gate ya produjo, no inventar un sistema nuevo.
- Schema change: `MemoryEntry.metadata["confidence"]` campo opcional. No requiere migración: las memorias existentes no tienen el campo y eso está bien (Pydantic default).

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 6 + extensión del schema en `plan/02-mcp-server-cambios.md`.

### 3.3 Contradiction Detection — ❌ Descartar

Sin cambios. Falsos positivos masivos sin LLM-judge, costo computacional alto, y el Verification Gate cubre el caso real (detección en el momento, no post-hoc).

### 3.4 Memory Hygiene (`cortex-prune`) — ❌ Descartar definitivamente

**Cambio respecto al análisis previo:** el previo lo postergó. Yo lo descarto definitivamente porque:

1. `cortex/feedback_loop.py` + `cortex/memory_decay.py` ya implementan decay temporal con half-life 168h y floor 10%.
2. Si en el futuro se acumula ruido, el fix correcto es **ajustar parámetros del decay** (más agresivo), no agregar un skill paralelo de pruning manual.
3. Implementar un agente de pruning con CI semanal es riesgoso (borra memoria que un dev necesita 6 meses después).

Si en 0.6.x el vault tiene >10,000 documentos y el decay no alcanza, reconsiderar — pero hoy es overhead.

### 3.5 Caveman Mode — ❌ Descartar

Sin cambios. Contradice la filosofía de documentación rica y trazable. Los handoffs estructurados YAML (4.3) son la solución correcta.

### 4.2 Anti-rationalization Signals — ✅ Aplicar

Sin cambios. La tabla de "Cuando pienses X, verificá Y" obliga al agente a auto-cuestionarse.

**Insight post-Ola:** la propuesta original tiene la tabla solo para el documenter. Yo la **generalizo**: cada subagent (sync, SDDwork, explorer, implementer, documenter) tiene su propio set de anti-rationalization patterns. El de explorer es distinto del de documenter.

**Plan:** ver `plan/01-cambios-subagentes-y-skills.md` sección 7.

### 4.3 Structured YAML Handoff — ✅ Aplicar (es la pieza central del cambio)

Sin cambios respecto al análisis previo, pero quiero **enfatizar** que este es **el cambio arquitectónico más importante** de toda la propuesta. Hoy los subagents se pasan prosa (teléfono roto). Mañana se pasan contratos YAML verificables (auditable).

**Insight post-Ola:** este cambio tiene **alcance MCP**. El servidor MCP debe exponer un nuevo tool `cortex_validate_handoff` que toma el YAML del agente saliente, valida el schema con Pydantic, y rechaza handoffs malformados. Sin esto, el contrato es solo aspiracional. Con esto, es enforced.

**Plan:** ver `plan/02-mcp-server-cambios.md` sección 2 (nuevo tool).

---

## 3. Cómo cada IDE interpreta agentes/subagentes/skills/herramientas/delegación/MCP

Esto es lo que el análisis previo no abordó y el usuario explícitamente pide. Cada IDE tiene **modelo mental distinto** sobre estos conceptos. Implementar los 8 cambios requiere **traducir** el contrato canónico (en `.cortex/subagents/` y `.cortex/skills/`) al formato que cada IDE espera.

### 3.1 Mapa conceptual: qué es cada cosa en cada IDE

| Concepto Cortex | Claude Code | OpenCode | Pi | Codex |
|-----------------|-------------|----------|-----|-------|
| **Agente** (rol orquestador) | "Skill" en `.claude/skills/<name>/SKILL.md` | "Agent" en `~/.config/opencode/opencode.json::agent` | "Agent" en `.pi/agents/<name>.md` con `agent-chain.yaml` | "Skill" en `.codex/skills/<name>.md` |
| **Subagente** (rol delegable) | "Agent" en `.claude/agents/<name>.md` | "Subagent" en `~/.config/opencode/subagents/<name>.md` | Misma carpeta `.pi/agents/` (sin distinción) | "Agent" en `.codex/agents/<name>.md` |
| **Skill** (capacidad reusable) | Sub-skills dentro de `.claude/skills/` | "skills" dict en JSON | "skills" en `settings.json` | Skills como agents secundarios |
| **Herramienta** (MCP tool) | `enabledMcpjsonServers` en `settings.json` | `tools` dict por agent en JSON | `mcp.json` global | `mcpServers` en `mcp.json` |
| **Delegación** | `Task` tool (nativo) | `Task` tool (nativo) | `agent-chain.yaml` declarativo | (limitada — solo via prompts) |
| **MCP server** | `.mcp.json::mcpServers.cortex` | `~/.config/opencode/opencode.json::mcp.cortex` | `.pi/mcp.json` (pipx-bin) | `.codex/mcp.json::mcpServers.cortex` |

### 3.2 Implicaciones para el plan

Cada uno de los 8 cambios tiene que **rematerializarse en 4 formatos**. Por ejemplo, "agregar Verification Gate al documenter":

- **Canonical:** modificar `.cortex/subagents/cortex-documenter.md` con la nueva sección.
- **Claude Code:** `cortex inject --ide claude-code` regenera `.claude/agents/cortex-documenter.md` desde el canonical. La sección aparece automáticamente.
- **OpenCode:** `cortex inject --ide opencode` actualiza `~/.config/opencode/subagents/cortex-documenter.md`.
- **Pi:** `cortex inject --ide pi` copia `cortex-pi/` que YA debe tener la sección actualizada — **esto requiere mantenerlo en sync** (el ítem #5 del roadmap 0.5.x lo cubre).
- **Codex:** `cortex inject --ide codex` regenera `.codex/agents/cortex-documenter.md`.

**Conclusión:** si el canonical en `.cortex/subagents/` es la única fuente de verdad, los 4 IDEs heredan el cambio automáticamente — salvo Pi que tiene un bundle paralelo en `cortex-pi/` y necesita sync explícito.

El plan en `docs/agents/plan/` desarrolla esto en detalle por IDE.

---

## 4. Resumen ejecutivo del análisis

### Lo que se aplica (8 cambios)

| # | Cambio | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 2.1 | Signal > Noise en documenter (reescritura del prompt) | **Alto** | Bajo |
| 2.2 | ADR 3 criterios objetivos | **Alto** | Bajo |
| 2.3 | CONTEXT.md como prompt asset (NO capa retrieval) | Medio | Bajo |
| 2.4 | Verification Gate en documenter | **Alto** | Medio |
| 2.5 | Handoff Mode con frontmatter estructurado | **Alto** | Medio |
| 3.2 | Confidence levels (fase 2, post-gate) | Medio | Medio |
| 4.2 | Anti-rationalization signals (generalizado a 5 agentes) | Medio | Bajo |
| 4.3 | Structured YAML handoff + MCP validator | **Alto** | Medio |

**Total estimado: 7-10 días de trabajo focal.**

### Lo que se descarta (5 cambios)

- 2.6 Progressive disclosure (skills monolíticos no son problema).
- 3.1 Lexical boost en RRF (rompe determinismo del RRF, redundante con BM25 + entity extraction).
- 3.3 Contradiction detection (falsos positivos sin LLM judge).
- 3.4 Memory hygiene cortex-prune (temporal decay ya cubre).
- 3.5 Caveman mode (contradice filosofía de documentación rica).

### La lección clave (refinada)

El análisis previo concluía: *"ejecutar cambios de skill, no tocar arquitectura"*. Yo refino: la **arquitectura de memoria está estable y validada por las Olas 0-4** (829 tests verdes), por lo que tocarla ahora es regression risk innecesario. Pero **sí tocamos arquitectura cuando es necesaria para los cambios de skill** — específicamente:

- Nuevo MCP tool `cortex_validate_handoff` (4.3 requiere enforcement).
- Nuevo estado `handoff` en `AutopilotSessionState.status` enum (2.5).
- Nuevo campo `confidence` en `MemoryEntry.metadata` (3.2).
- Nuevo property `WorkspaceLayout.context_md_path` (2.3).

Estos cambios arquitectónicos son **mínimos y orientados a soportar el process change**. No son refactor de retrieval ni cambios al motor de RRF.

---

## 5. Plan de implementación

El plan detallado vive en `docs/agents/plan/`. Estructura:

- `plan/00-README.md` — índice + contexto operativo.
- `plan/01-cambios-subagentes-y-skills.md` — los 8 cambios al canonical en `.cortex/subagents/` y `.cortex/skills/`.
- `plan/02-mcp-server-cambios.md` — nuevos MCP tools (`cortex_validate_handoff`, opcionalmente `cortex_verify_session_claims`).
- `plan/03-ide-claude-code.md` — cómo se materializa cada cambio en Claude Code.
- `plan/04-ide-opencode.md` — idem OpenCode.
- `plan/05-ide-pi.md` — idem Pi, incluyendo `cortex-pi/` bundle sync.
- `plan/06-ide-codex.md` — idem Codex.
- `plan/07-tests-y-cierre.md` — tests por capa + smoke 4×IDE + criterio de cierre.

Cada uno con:
- **Objetivo** específico.
- **Archivos a tocar** exactos.
- **Plan paso a paso** ejecutable.
- **Criterio de cierre** marcable.
- **Esfuerzo** estimado.

Cuando se cierre Tripartita Refinada, este documento + los del plan se mueven a `docs/olas/ola-5-tripartita-refinada.md` con el detalle del cierre, siguiendo la convención de Olas 0-4.

---

## 6. Apéndice: Por qué este documento existe (en lugar de actualizar el análisis previo)

El análisis previo (`ANALISIS-MEJORA-TRIPARTITO.md`) es **históricamente valioso** y debe preservarse. Refleja la opinión de otro agente con un nivel de contexto distinto (pre-Olas). Sobreescribirlo perdería la pista de cómo evolucionó el pensamiento del proyecto.

Este documento es la **versión definitiva post-Olas**. Si se decide cerrar Tripartita Refinada con los 8 cambios, este doc se convierte en la "spec aprobada" y el previo queda como "primera iteración del pensamiento".

Cuando se discuta el sistema tripartito en el futuro, **leer este documento primero**.
