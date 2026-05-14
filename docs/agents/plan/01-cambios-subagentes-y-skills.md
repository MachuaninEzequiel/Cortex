---
title: Plan 01 — Cambios canonical en subagents y skills
status: pendiente
phase: 1 (debe cerrarse antes de Fase 2)
---

# Plan 01 — Cambios canonical en subagents y skills

Los 8 cambios al canonical. Esta es la **fuente de verdad**: los 4 IDEs heredan de aquí vía `cortex inject`.

## Resumen

| § | Cambio | Archivos canonical | Esfuerzo |
|---|--------|---------------------|----------|
| 1 | Signal > Noise en documenter | `.cortex/subagents/cortex-documenter.md` | 30 min |
| 2 | ADR 3 criterios | `.cortex/subagents/cortex-documenter.md` + `cortex/doc_generator.py` | 1 h |
| 3 | CONTEXT.md como prompt asset | `cortex/workspace/layout.py`, `cortex/cli/main.py` (setup), `.cortex/skills/cortex-sync.md`, `.cortex/skills/cortex-SDDwork.md`, `.cortex/subagents/cortex-documenter.md` | 2 h |
| 4 | Verification Gate | `.cortex/subagents/cortex-documenter.md` + nuevo helper | 2 h |
| 5 | Handoff Mode | `.cortex/subagents/cortex-documenter.md` + `cortex/autopilot/models.py` (status enum) + `cortex/autopilot/session_writer.py` (tag handoff) + `cortex/documentation.py` (template) | 3 h |
| 6 | Confidence levels (post gate) | `cortex/models.py` (MemoryEntry metadata) + `cortex/autopilot/session_writer.py` (extra_metadata) | 1 h |
| 7 | Anti-rationalization en los 5 agentes | `.cortex/subagents/cortex-{code-explorer,code-implementer,documenter}.md` + `.cortex/skills/cortex-{sync,SDDwork}.md` | 2 h |
| 8 | Structured YAML handoff | `.cortex/subagents/*.md` (output contract) + nuevo Pydantic schema en `cortex/handoff.py` | 4 h |

**Total estimado: ~15 horas (2 días focal).**

## Orden de ejecución sugerido

1. **Cambios sólo de prompt (1, 2, 7)** — más simples, sin código nuevo.
2. **Cambios con código nuevo (3, 5, 8)** — agregan helpers, modelos, properties.
3. **Cambios que dependen de #8 (4, 6)** — Verification Gate y Confidence Levels usan el schema de handoff.

---

## §1. Signal > Noise en documenter

### Objetivo

Cambiar la filosofía del documenter de "documenta TODO" a "persistir solo el delta cognitivo, referenciar lo demás".

### Archivos a tocar

- `.cortex/subagents/cortex-documenter.md` — sección "Responsabilidades Principales" + "Reglas de Persistencia".
- (Pi-side espejo) `cortex-pi/.pi/agents/cortex-documenter.md` — espejar el cambio. Si el ítem 5 del roadmap 0.5.x está cerrado (Pi sync mechanism), correr `cortex inject --ide pi --sync-canonical` después.

### Plan

1. Localizar la frase exacta `"NO OMITAS INFORMACIÓN. Documenta TODO el contexto acumulado."` en el archivo.
2. Reemplazar el bloque entero por el prompt propuesto en `docs/agents/ANALISIS-COMPLETO.md` §2.1 / `docs/agents/MEJORA-TRIPARTITO.md` §2.1.
3. Agregar sub-sección "Qué SÍ debe contener" y "Qué NO debe contener" como bullet lists.
4. Agregar ejemplo de "delta cognitivo correcto" (YAML frontmatter + body).

### Criterio de cierre

- [ ] Frase "documenta TODO" eliminada del canonical.
- [ ] Sección "HIGH-SIGNAL DOCUMENTATION MODE" agregada con regla de oro Reference > Duplicate.
- [ ] Lista explícita de "qué NO debe contener".
- [ ] Ejemplo de delta cognitivo presente.
- [ ] Espejo Pi-side actualizado (o programado para sync).

---

## §2. ADR 3 criterios

### Objetivo

Eliminar ADRs triviales aplicando el filtro objetivo Hard-to-reverse + Surprising + Real-trade-off **tanto en el agente humano como en el fallback automático**.

### Archivos a tocar

- `.cortex/subagents/cortex-documenter.md` — agregar sección "Criterios para crear un ADR".
- `cortex/doc_generator.py` — la función `generate_all` produce ADRs como fallback cuando hay label "adr" o "decision". Agregar gate: si el PR body no contiene evidencia de los 3 criterios, NO generar ADR (solo session note).
- `tests/unit/test_doc_generator.py` — test que verifica que un PR sin trade-off documentado no produce ADR fallback.

### Plan

1. En el skill del documenter, agregar la tabla de 4 ejemplos clasificados con veredicto (de ANALISIS-COMPLETO §2.2).
2. En `doc_generator.py::DocGenerator.generate_all`:
   - Localizar el path donde se genera ADR fallback.
   - Agregar función helper `_meets_adr_criteria(ctx: PRContext) -> bool`:
     ```python
     def _meets_adr_criteria(ctx: PRContext) -> bool:
         """Apply the 3-criteria filter to ADR generation."""
         body = (ctx.body or "").lower()
         # Hard to reverse: mentions migration, refactor, schema, contract
         hard_reverse = any(k in body for k in ("migration", "refactor", "schema", "breaking", "contract"))
         # Surprising: explicit "why" or "decision"
         surprising = any(k in body for k in ("decided", "rationale", "tradeoff", "trade-off", "why"))
         # Real trade-off: mentions alternatives
         tradeoff = any(k in body for k in ("alternative", "considered", "instead of", "rejected"))
         return hard_reverse and surprising and tradeoff
     ```
   - Solo generar ADR si `_meets_adr_criteria(ctx) and ctx.has_adr_label()`.
3. Test que verifica:
   - PR sin trade-off documentado y con label "adr" → NO ADR fallback.
   - PR con los 3 criterios + label "adr" → ADR fallback.
   - PR sin label "adr" → NO ADR fallback (sin cambio respecto a hoy).

### Criterio de cierre

- [ ] Sección "Criterios para crear un ADR" en canonical.
- [ ] Tabla de 4 ejemplos con veredicto.
- [ ] `_meets_adr_criteria` implementado.
- [ ] 3 tests del doc_generator agregados (caso veto, caso aprobado, regresión).

---

## §3. CONTEXT.md como prompt asset

### Objetivo

Soportar un archivo opcional `<workspace>/CONTEXT.md` que define el ubiquitous language del proyecto. Los skills `cortex-sync` y `cortex-documenter` lo cargan como referencia al boot. **NO** modifica retrieval ni RRF — es solo material de prompt.

### Archivos a tocar

- `cortex/workspace/layout.py` — agregar property `context_md_path`.
- `cortex/setup/templates.py` — agregar `render_context_md(ctx)` que produce un template stub.
- `cortex/setup/orchestrator.py::_create_vault_docs` — agregar `(workspace/CONTEXT.md, render_context_md)` a la lista (opcional, sólo si no existe).
- `.cortex/skills/cortex-sync.md` — agregar sección "Glosario del dominio (CONTEXT.md)" que indica al agente cargar el archivo si existe.
- `.cortex/skills/cortex-SDDwork.md` — idem.
- `.cortex/subagents/cortex-documenter.md` — agregar regla: "Si descubrís un término nuevo del dominio, anotálo en CONTEXT.md ANTES de cerrar la sesión".
- `tests/unit/workspace/test_layout.py` — test del nuevo property.

### Plan

1. **WorkspaceLayout property:**
   ```python
   @property
   def context_md_path(self) -> Path:
       """Path to the optional Ubiquitous Language glossary.

       Lives at <workspace>/CONTEXT.md (new layout) or <repo>/CONTEXT.md
       (legacy). Adopters create it manually or via ``cortex setup``.
       """
       if self.is_legacy_layout:
           return self.repo_root / "CONTEXT.md"
       return self.workspace_root / "CONTEXT.md"
   ```

2. **Template `render_context_md`** en `templates.py`:
   ```python
   def render_context_md(ctx: ProjectContext) -> str:
       return """---
   title: Ubiquitous Language Guide
   tags: [glossary, domain, cortex-context]
   ---

   # Ubiquitous Language (CONTEXT.md)

   Este archivo define el vocabulario canónico del dominio. Los agentes
   `cortex-sync` y `cortex-documenter` lo leen al boot para usar términos
   consistentes.

   ## Cómo extenderlo

   Cuando descubrás un término del dominio nuevo:

   1. Agregalo a la tabla de abajo con su definición canónica.
   2. Listá sinónimos prohibidos (que NO se deben usar en docs).
   3. Si entra en conflicto con uso previo, creá un ADR de rename.

   ## Términos

   | Término canónico | Definición | Sinónimos prohibidos |
   |------------------|------------|----------------------|
   | _completar con términos del dominio_ | | |
   """
   ```

3. **Orchestrator setup:** agregar `(workspace_root / "CONTEXT.md", render_context_md)` a la creación de vault docs en `_create_vault_docs`. **Solo crear si no existe** (idempotente).

4. **Skills (en `.cortex/skills/cortex-sync.md`):** agregar al inicio:
   ```markdown
   ## Pre-flight: cargar CONTEXT.md si existe

   Antes de empezar, leé `<workspace>/CONTEXT.md` (o `<repo>/CONTEXT.md`
   en layout legacy). Es opcional. Si existe, los términos canónicos
   listados allí son **obligatorios** en la spec y en cualquier
   comunicación con otros agentes. NO uses los sinónimos prohibidos.

   Si el archivo no existe, ignorá esta sección.
   ```

5. **Documenter:** agregar sección "Mantenimiento de CONTEXT.md":
   ```markdown
   ## Mantenimiento de CONTEXT.md (responsabilidad del documenter)

   Al finalizar la sesión, revisá si surgieron términos del dominio
   nuevos o redefinidos. Si sí:

   1. Leé `CONTEXT.md` actual.
   2. El término ya existe → verificá uso consistente. Si no, marcá
      conflicto y proponé ADR de rename.
   3. Es nuevo → agregalo con definición canónica + sinónimos prohibidos + ejemplo de uso.
   4. Entró en conflicto con uso previo → creá ADR de rename y actualizá glosario.
   ```

### Criterio de cierre

- [ ] `WorkspaceLayout.context_md_path` property implementada + test.
- [ ] `render_context_md` template creado.
- [ ] `_create_vault_docs` lo crea idempotentemente.
- [ ] Skills `cortex-sync.md` y `cortex-SDDwork.md` referencian el archivo.
- [ ] Documenter tiene sección de "Mantenimiento de CONTEXT.md".
- [ ] Test que verifica que setup full crea `CONTEXT.md` template.

---

## §4. Verification Gate en documenter

### Objetivo

Antes de cerrar una sesión, el documenter verifica claims contra el diff real. Si no puede verificar, marca como `unverified` o degrada el status a `handoff`.

### Archivos a tocar

- `.cortex/subagents/cortex-documenter.md` — sección "VERIFICATION GATE" antes de `cortex_save_session`.
- `cortex/mcp/server.py` — nuevo MCP tool `cortex_verify_session_claims` (cubierto en `02-mcp-server-cambios.md`).

### Plan

1. En el canonical del documenter, agregar bloque "VERIFICATION GATE" con la checklist pre-flight (de ANALISIS-COMPLETO §2.4).
2. La checklist obliga al agente a:
   - Ejecutar `git diff` o leer archivos mencionados.
   - Cross-check tests si dice "tests pasan".
   - Buscar memorias previas relacionadas.
   - Verificar ADRs referenciados.
3. Reglas explícitas para discrepancia: marcar con `⚠️ Discrepancia detectada` en la session note.
4. Reglas explícitas para failed check: cerrar sesión como `status: handoff` (depende de §5).

### Criterio de cierre

- [ ] Sección "VERIFICATION GATE" en canonical del documenter.
- [ ] Checklist de 5 items pre-flight.
- [ ] Reglas claras para discrepancia y para failed check.
- [ ] Test integración: invocar `cortex_save_session` desde un agent simulado que afirma "tests pasan" sin haber ejecutado tests → verificar que el documenter (o el gate) detecta el claim no verificado.

---

## §5. Handoff Mode

### Objetivo

Permitir que el documenter cierre una sesión con `status: handoff` cuando hay TODOs críticos, blockers o checks fallidos. El siguiente agente recupera la nota con tag `#handoff` priorizado.

### Archivos a tocar

- `.cortex/subagents/cortex-documenter.md` — sección "Modo Handoff".
- `cortex/autopilot/models.py` — agregar `"handoff"` al enum `AutopilotSessionState.status`.
- `cortex/autopilot/session_writer.py::_build_tags` — agregar `"handoff"` cuando state.status == "handoff".
- `cortex/documentation.py::write_session_note` — soportar frontmatter `status: handoff` con campos opcionales `next-session-needs`, `blockers`, `verified-state`, `unverified-claims`, `suggested-skills`.
- `tests/unit/autopilot/test_session_writer.py` — test del tag handoff.
- `tests/unit/test_documentation.py` (si existe; sino crear) — test del nuevo frontmatter.

### Plan

1. **Enum AutopilotSessionState.status** en `cortex/autopilot/models.py`:
   ```python
   status: Literal[
       "started",
       "preflight_done",
       "implementation_seen",
       "documented",
       "finished",
       "failed",
       "handoff",  # NUEVO
   ] = "started"
   ```

2. **`session_writer.py::_build_tags`:**
   ```python
   @staticmethod
   def _build_tags(draft: SessionDraft, state: AutopilotSessionState | None = None) -> list[str]:
       tags = ["session", "autopilot"]
       if draft.confidence == "auto-draft":
           tags.append("auto-draft")
       if state and state.status == "handoff":
           tags.append("handoff")
       return tags
   ```
   Actualizar la signature de `_build_tags` y todos los call sites.

3. **`documentation.py::write_session_note`** — extender la firma:
   ```python
   def write_session_note(
       vault_path: str | Path,
       *,
       title: str,
       spec_summary: str,
       changes_made: list[str] | None = None,
       files_touched: list[str] | None = None,
       key_decisions: list[str] | None = None,
       next_steps: list[str] | None = None,
       tags: list[str] | None = None,
       note_date: date | None = None,
       # NUEVOS para handoff
       handoff: bool = False,
       blockers: list[str] | None = None,
       verified_state: list[str] | None = None,
       unverified_claims: list[str] | None = None,
       suggested_skills: list[str] | None = None,
   ) -> Path:
   ```
   Si `handoff=True`, el frontmatter incluye `status: handoff` + los campos opcionales.

4. **Canonical documenter:** agregar sección "Modo Handoff" con la estructura del frontmatter (de ANALISIS-COMPLETO §2.5).

5. **Tests:**
   - Verificar que `state.status = "handoff"` → tag `"handoff"` en metadata episódico.
   - Verificar que `write_session_note(handoff=True, blockers=[...])` produce frontmatter correcto.

### Criterio de cierre

- [ ] Enum status incluye `"handoff"`.
- [ ] `_build_tags` agrega tag `"handoff"` cuando aplica.
- [ ] `write_session_note` acepta los 5 campos nuevos.
- [ ] Canonical documenter tiene sección "Modo Handoff" con structure.
- [ ] 3 tests: tag handoff, frontmatter handoff, retrieval de notas handoff (`cortex search` debería encontrar memorias con tag handoff prioritariamente).

---

## §6. Confidence levels (post-gate)

### Objetivo

Cuando el Verification Gate corre, persistir el resultado como confidence level en la memoria episódica: `verified` (pasó el gate), `asserted` (no se verificó pero se reportó), `contradicted` (el diff contradice el claim).

**Solo viable después de §4 (Verification Gate).**

### Archivos a tocar

- `cortex/models.py::MemoryEntry` — agregar `confidence: Literal["verified", "asserted", "contradicted"] | None` (opcional, default None para backwards compat).
- `cortex/autopilot/session_writer.py::_build_metadata` — incluir `confidence` cuando el state lo tiene.
- `cortex/autopilot/models.py::SessionDraft` — agregar `confidence_level: str | None = None`.
- `cortex/episodic/memory_store.py::_serialize_metadata` y `_deserialize_metadata` — preservar `confidence` (ya se preserva via metadata_json — verificar).
- Tests: round-trip del campo.

### Plan

1. **`MemoryEntry`:** agregar campo opcional.
2. **`SessionDraft`:** agregar campo opcional. El SessionBuilder lo setea según el resultado del gate.
3. **`session_writer._build_metadata`:**
   ```python
   metadata["confidence"] = draft.confidence_level or "asserted"
   ```
4. **Test round-trip:**
   ```python
   def test_confidence_persists_through_episodic_roundtrip(episodic_store):
       episodic_store.add(
           content="JWT refresh validated against diff",
           memory_type="session",
           extra_metadata={"confidence": "verified"},
       )
       entries = episodic_store.list_entries()
       assert entries[0].metadata["confidence"] == "verified"
   ```

### Criterio de cierre

- [ ] `MemoryEntry.confidence` campo opcional.
- [ ] `SessionDraft.confidence_level` agregado.
- [ ] `session_writer` persiste el confidence.
- [ ] Round-trip test verde.
- [ ] Documentación del campo en `docs/review/cortex-save-state.md` §7 (modelos).

---

## §7. Anti-rationalization en los 5 agentes

### Objetivo

Cada subagent tiene su propia tabla de "Cuando pienses X, verificá Y". La propuesta original lo tenía solo para documenter; generalizamos.

### Archivos a tocar

- `.cortex/subagents/cortex-code-explorer.md` — tabla específica de explorer.
- `.cortex/subagents/cortex-code-implementer.md` — tabla específica de implementer.
- `.cortex/subagents/cortex-documenter.md` — tabla de documenter (la de ANALISIS-COMPLETO §4.2).
- `.cortex/skills/cortex-sync.md` — tabla de sync (corta).
- `.cortex/skills/cortex-SDDwork.md` — tabla de orquestador.

### Plan

Por cada agent, una tabla específica. Ejemplos:

**Explorer:**
| Pensamiento | Realidad | Acción |
|-------------|----------|--------|
| "Ya entendí el código" | Quizá leíste solo el archivo principal. | Lee también los tests y los imports. |
| "Hay un patrón obvio" | Patrón obvio sin tests no es patrón. | Verifica con grep o `cortex_search`. |
| "El implementer ya sabrá esto" | El implementer no lee tu mente. | Documenta explícitamente en context_for_next del handoff. |

**Implementer:**
| Pensamiento | Realidad | Acción |
|-------------|----------|--------|
| "El test pasa, está bien" | ¿Cubrió el edge case que reportaste? | Lee el test, no el output. |
| "Es solo un fix simple" | Los fixes simples ocultan los regresions. | Run `cortex search` por keyword del fix antes de mergear. |
| "Lo dejo para el documenter" | El documenter NO inventa contexto. | Captura decisiones in-flight ANTES de pasar el handoff. |

**Documenter:** ya cubierto por ANALISIS-COMPLETO §4.2.

**Sync (corta):**
| Pensamiento | Realidad | Acción |
|-------------|----------|--------|
| "El ticket ya describe todo" | Probable que falte historial. | Run `cortex_sync_ticket` para historial real. |
| "No hay decisión previa relevante" | Hay 3 ADRs sobre el tema. | Búscalos en vault/decisions/ antes de proponer. |

**SDDwork (orquestador):**
| Pensamiento | Realidad | Acción |
|-------------|----------|--------|
| "Tarea simple, voy directo" | "Simple" para vos puede ser deep track. | Aplica los 3 criterios de routing. |
| "No hace falta explorer" | Si tocás >2 archivos, sí. | Default: explorer first en deep track. |
| "El documenter es opcional" | NO. Es el último gate. | Siempre invocar documenter. |

### Criterio de cierre

- [ ] 5 tablas anti-rationalization (una por agent).
- [ ] Cada tabla con mínimo 3 entradas específicas al rol.
- [ ] Tablas integradas en los skills/subagents canonical.

---

## §8. Structured YAML handoff + schema

### Objetivo

Reemplazar prosa libre entre agents por contratos YAML verificables.

### Archivos a tocar

- `cortex/handoff.py` — **nuevo archivo**. Pydantic schema `AgentHandoff`.
- `.cortex/subagents/cortex-code-explorer.md` — sección "Contrato de Salida".
- `.cortex/subagents/cortex-code-implementer.md` — idem.
- `.cortex/subagents/cortex-documenter.md` — idem (consume handoff del implementer).
- `.cortex/skills/cortex-sync.md` — agente sync produce handoff inicial.
- `.cortex/skills/cortex-SDDwork.md` — orquestador valida handoffs entre etapas.
- `tests/unit/test_handoff.py` — **nuevo**. Tests del schema.

### Plan

1. **Schema `cortex/handoff.py`:**
   ```python
   """cortex.handoff — Structured agent handoff schema.

   Replaces prose handoffs between subagents with verifiable YAML.
   Validated by ``cortex_validate_handoff`` MCP tool (see plan/02).
   """
   from __future__ import annotations

   from typing import Literal
   from pydantic import BaseModel, Field


   class ArtifactProduced(BaseModel):
       path: str
       action: Literal["created", "modified", "deleted", "renamed"]
       lines_changed: int = 0
       lines_added: int = 0


   class AgentHandoff(BaseModel):
       """Structured handoff produced by every subagent at completion."""

       agent: Literal[
           "cortex-sync",
           "cortex-SDDwork",
           "cortex-code-explorer",
           "cortex-code-implementer",
           "cortex-documenter",
       ]
       status: Literal["complete", "partial", "blocked"]
       verified_claims: list[str] = Field(default_factory=list)
       unverified_claims: list[str] = Field(default_factory=list)
       artifacts_produced: list[ArtifactProduced] = Field(default_factory=list)
       context_for_next: list[str] = Field(default_factory=list)
       suggested_adr: bool = False
       suggested_adr_reason: str = ""
       suggested_context_terms: list[str] = Field(default_factory=list)

       def to_yaml(self) -> str:
           import yaml
           return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False)

       @classmethod
       def from_yaml(cls, text: str) -> "AgentHandoff":
           import yaml
           data = yaml.safe_load(text)
           return cls.model_validate(data)
   ```

2. **Sección "Contrato de Salida" en cada subagent:**
   Texto de ANALISIS-COMPLETO §4.3 con el ejemplo YAML.

3. **Tests `tests/unit/test_handoff.py`:**
   - `test_minimal_handoff_validates` — solo agent + status.
   - `test_full_handoff_round_trip` — to_yaml → from_yaml es identidad.
   - `test_invalid_agent_rejected` — agent="random" falla validación.
   - `test_invalid_status_rejected` — status="foo" falla.
   - `test_artifact_action_validated` — action="banana" falla.

### Criterio de cierre

- [ ] `cortex/handoff.py` creado con `AgentHandoff` y `ArtifactProduced`.
- [ ] 5 tests del schema verdes.
- [ ] 5 skills/subagents canonical con sección "Contrato de Salida" + ejemplo YAML.
- [ ] Documentación del schema en `docs/review/cortex-save-state.md` §7.

---

## Checklist final del Plan 01

- [ ] §1 Signal > Noise aplicado en documenter.
- [ ] §2 ADR 3 criterios en documenter + doc_generator (con tests).
- [ ] §3 CONTEXT.md como prompt asset (layout + template + skills).
- [ ] §4 Verification Gate en documenter.
- [ ] §5 Handoff Mode (status enum + tag + write_session_note + canonical).
- [ ] §6 Confidence levels (post §4) en MemoryEntry + SessionDraft.
- [ ] §7 Anti-rationalization en los 5 agentes.
- [ ] §8 Structured YAML handoff schema + 5 tests + 5 canonicals.
- [ ] Espejos en `cortex-pi/.pi/agents/` sincronizados (manual o vía mecanismo del roadmap 0.5.x ítem #5).
- [ ] Suite global verde.

**Fase 1 completa cuando todos los items están en `[x]`.**
