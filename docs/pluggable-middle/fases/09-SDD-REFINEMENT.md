# Fase 09 — SDD Refinement: Proposal + Design + Tasks granular

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 04 cerrada · **Recomendado ejecutar después de:** Fase 08 (Quality Gates) · **Esfuerzo estimado:** ~3-4 semanas (3 sub-fases incrementales)

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 09 |
| Nombre | SDD Refinement: Proposal + Design + Tasks granular |
| Versión del plan | 1.0 |
| Dependencias | Fase 04 cerrada. **Recomendado:** Fase 08 cerrada antes (coordinación con cambios al SDDwork prompt + documenter persistence). |
| Output principal | Acerca SDDwork al workflow SDD completo (openspec-style): agrega los steps **proposal** (post-explore), **design** (intra-Deep Track) y **tasks granulares** (descomposición trackeable del spec). |
| Breaking changes | Ninguno. `SessionRecord.tasks` es **campo nuevo aditivo** (default lista vacía); MCP tools nuevas son aditivas; un nuevo subagent y un nuevo `doc_type` son aditivos. |

---

## 0.1 Origen de esta fase

Esta fase nace del análisis post-Fase 04 comparando SDDwork actual contra el workflow de openspec
(`init → explore → proposal → spec → design → tasks → apply → verify → sync → archive`). De los
10 steps, SDDwork cubría plenamente 5, parcialmente 2, y faltaban 3:

- **proposal** — falta. Sync va de explore → spec sin discutir alternativas.
- **design** — falta como entregable separado. El implementer lo infiere inline.
- **tasks** — falta descomposición granular. Fast/Deep Track es binario.

Esta fase cierra los 3 gaps.

---

## 0.2 Estructura por sub-fases

Igual que Fase 07 (CI Plugin), Fase 09 entrega **3 sub-fases independientes** que se construyen
secuencialmente. Cada una cierra con sus propios Completion Verification Commands.

| Sub-fase | Esfuerzo | Entrega | Cierra |
|---|---|---|---|
| **09.A** — Proposal step | 2-3 días | `cortex-sync` agrega step opcional de proposal pre-spec | Filtra ideas malas antes de gastar tokens en spec detallada |
| **09.B** — Design step | ~1-1.5 sem | Nuevo subagent `cortex-code-designer` + doc_type `design` + extensión Deep Track | Evita decisiones de arquitectura mal tomadas inline durante implementación |
| **09.C** — Tasks granular | ~1.5-2 sem | `SessionRecord.tasks[]` + CLI `cortex session task ...` + SDDwork emite descomposición | Permite tracking granular, pause/resume, % completion en session note |

Es válido **mergear / release después de cada sub-fase**. Si capacidad limitada, ejecutar
09.A solo (~3 días) ya entrega valor; 09.B y 09.C pueden hacerse en iteraciones posteriores.

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) §4 (los 3 modos), §6 (flujo end-to-end), §8 (verification hooks).
- [`fases/02-SDDWORK-MIGRATION.md`](02-SDDWORK-MIGRATION.md) §3.1 (granularidad de checkpoints) — para entender que la descomposición granular debe respetar la regla "1-3 checkpoints ricos, no 50 micro-checkpoints".
- [`fases/08-MANAGED-QUALITY-GATES.md`](08-MANAGED-QUALITY-GATES.md) — coordinación crítica: Fase 08 ya modifica el SDDwork prompt; Fase 09 debe respetar esa estructura al agregar más steps.
- [`fases/07-CI-PLUGIN.md`](07-CI-PLUGIN.md) §3.5 — para entender cómo Fase 07 N3 extendió enums; Fase 09 sigue el mismo patrón aditivo al extender `SessionRecord`.

### 1.2 Código que vas a tocar

Leé enteros:

- `cortex/session/models.py` — donde se agrega el campo `tasks: list[Task]` y el nuevo modelo `Task`.
- `cortex/session/service.py` — agregar API CRUD para tasks.
- `cortex/session/storage.py` — verificar que los tasks se serialicen/deserialicen correctamente (es Pydantic, debería ser automático).
- `cortex/documenter/persistence.py` — reportar % completion de tasks en el summary del session note.
- `.cortex/skills/cortex-sync.md` y su renderer — sub-fase 09.A modifica este.
- `.cortex/skills/cortex-SDDwork.md` y su renderer — sub-fase 09.B agrega designer step, 09.C agrega descomposición de tasks.
- `cortex/documentation/data.py`, `schemas/`, `writers.py`, `templates/` — donde se agrega el nuevo `doc_type="design"`.
- `cortex/cli/session.py` — donde se agrega el subapp `cortex session task ...`.

Leé bajo demanda:

- `cortex/autopilot/detectors/` — los detectors clasifican task_type; útil para que el SDDwork decida si descomponer en tasks granulares (sólo en Deep Track) o no (Fast Track).

### 1.3 Documentación externa

- **openspec workflow** (referencia del usuario): `init → explore → proposal → spec → design → tasks → apply → verify → sync → archive`. Fase 09 implementa los 3 steps faltantes (proposal, design, tasks) sin copiar la nomenclatura — adaptados al modelo de Cortex.

---

## 2. Goal

Al finalizar las 3 sub-fases:

### Sub-fase 09.A entrega

1. **`cortex-sync` agrega step `proposal` opcional** entre la exploración y `cortex_create_spec`. Después de `cortex_sync_ticket` + glob/read, sync emite al usuario:
   > "Propongo: [resumen en 2-3 líneas]. Alternativas consideradas: [A, B, C]. Riesgos principales: [...]. ¿Procedo a spec? [y / edit / cancel]"
2. Flag `--proposal-mode required|optional|skip` (default: `optional`) en `cortex_create_spec` MCP tool. Si el sync no obtuvo confirmación explícita y el modo es `required`, falla con error.
3. Skill `cortex-sync.md` actualizado para guiar la emisión del proposal.

### Sub-fase 09.B entrega

4. **Nuevo subagent `cortex-code-designer`** (`.cortex/subagents/cortex-code-designer.md` + entrada en `cortex-pi/.pi/agents/`). Se invoca entre `cortex-code-explorer` y `cortex-code-implementer` en Deep Track. Produce un design document en `vault/designs/<session_id>.md` con:
   - **Architecture decision** (capas afectadas, separation of concerns).
   - **Data model changes** (schemas, migrations, validators).
   - **API contracts** (signatures de funciones nuevas/cambiadas).
   - **Test plan** (qué tests, en qué orden).
5. **Nuevo `doc_type="design"`** en `cortex/documentation/` con:
   - Pydantic schema (`DesignDocData`).
   - Writer canónico (`write_design_note`).
   - Template Jinja2 (`design.md.j2`).
   - Entry en la tabla de routing canónica del documenter.
6. **SDDwork Deep Track ahora es 4 pasos**: explorer → designer → implementer → SDDwork wrap-up. Cada subagent emite su propio checkpoint.
7. Implementer lee el design document (path explícito en el spec referenciado por el SDDwork) y lo sigue. NO improvisa decisiones de arquitectura.

### Sub-fase 09.C entrega

8. **Nuevo modelo `Task`** en `cortex/session/models.py`:
   ```python
   class TaskStatus(StrEnum):
       PENDING = "pending"
       IN_PROGRESS = "in-progress"
       DONE = "done"
       SKIPPED = "skipped"
       BLOCKED = "blocked"

   class Task(BaseModel):
       id: str  # e.g. "T1.1"
       description: str
       files_in_scope: list[str] = []
       depends_on: list[str] = []  # other task ids
       status: TaskStatus = TaskStatus.PENDING
       completed_at: datetime | None = None
       checkpoint_index: int | None = None  # which Session.checkpoints[i] closed it
   ```
9. **`SessionRecord.tasks: list[Task]`** — campo nuevo aditivo (default `[]`). Backwards compatible: sessions viejas siguen cargando sin tasks.
10. **CLI `cortex session task`** — subcomandos:
    - `cortex session task list [--session ID] [--status pending|done|...]`
    - `cortex session task done <task_id> [--note ...]` — marca task como DONE + emite checkpoint vinculado.
    - `cortex session task skip <task_id> --reason ...`
    - `cortex session task block <task_id> --reason ...`
11. **MCP tools nuevas** equivalentes:
    - `cortex_session_task_list`
    - `cortex_session_task_update` (genérico: cambia status + checkpoint_index).
12. **SDDwork emite tasks descompuestos** en Deep Track (opt-in con flag `--with-tasks` en `cortex create-spec`). Después del designer, el orquestador emite `cortex_session_task_update(...)` por cada task identificada.
13. **Documenter reporta `% completion` en el summary del session note**: "Completed 4/5 tasks (1 skipped)".

**Lo que NO se hace en esta fase (en ninguna sub-fase):**

- ❌ NO se cambia el flow de Fast Track. Tasks granulares son sólo Deep Track + opt-in.
- ❌ NO se eliminan ni cambian comportamiento de los subagents existentes (`cortex-code-explorer`, `cortex-code-implementer`). Sólo se agrega el `cortex-code-designer` entre ellos.
- ❌ NO se hace análogo a la "TUI muestra tasks" — eso es mejora post-Fase 06 (la TUI v1 muestra `mode` y `checkpoints` solo). Sumar tasks display sería una iteración 06.1 separada.
- ❌ NO se introduce el step `sync` de openspec (handoff intermedio explícito). Los checkpoints ya cubren el patrón funcionalmente — no vale la pena agregar surface CLI nueva.
- ❌ NO se agregan `auto-checkpoint per task` con triggers automáticos. La descomposición es informativa; el agente sigue decidiendo cuándo emitir checkpoint global.

---

## 3. Decisiones de diseño clave

### 3.1 ¿Proposal step es obligatorio?

**Decisión:** **opcional por default**. Modos disponibles:
- `optional` (default): sync emite el proposal pero no espera confirmación explícita. Procede a spec a menos que el usuario interrumpa.
- `required`: sync espera respuesta `[y]` antes de spec.
- `skip`: sync omite el proposal (modo legacy / Fast tasks).

Razón: hacer required de entrada agregaría fricción para tareas chicas. Permitir configuración respeta la diversidad de usuarios.

### 3.2 ¿El design doc lo escribe el subagent designer o el SDDwork?

**Decisión:** **el subagent designer** lo escribe usando la MCP tool `write_design_note_canonical` (nueva, análoga a `write_session_note_canonical`). El SDDwork sólo orquesta — no escribe diseño.

Razón: separation of concerns. SDDwork orquesta, subagents producen entregables.

### 3.3 ¿Tasks viven en `SessionRecord` o en archivo separado?

**Decisión:** dentro del `SessionRecord` (`tasks: list[Task]`). Razones:
- Una sesión tiene unidad atómica de persistencia (`.cortex/sessions/<id>.yaml`). Sacar tasks a archivo separado fragmenta la atomicidad.
- Los checkpoints ya viven en el SessionRecord. Tasks son del mismo orden de granularidad.
- El YAML resultante crece poco (~50 bytes por task).

Trade-off: el SessionRecord crece. Para spec con 10 tasks, ~500 bytes extra. Despreciable.

### 3.4 ¿Tasks granulares son aditivas o sustituyen los checkpoints?

**Decisión:** **aditivas**. Los checkpoints siguen existiendo y siguen siendo el contrato inter-agente. Los tasks son un layer **descriptivo + de tracking** que se vincula a checkpoints opcionalmente vía `checkpoint_index`.

Razón: si forzáramos task-per-checkpoint, romperíamos la regla "1-3 checkpoints ricos" de Fase 02. Y rompería compatibilidad con Fast Track (que tiene UN checkpoint y N tasks no aplica).

### 3.5 ¿El designer es obligatorio en Deep Track o opcional?

**Decisión:** **obligatorio en Deep Track**. Razón: el valor del design step es justamente prevenir decisiones inline; hacerlo opcional dejaría una escape hatch que la mayoría tomaría por inercia. Si el spec es realmente trivial pero cae en Deep Track por scope: el designer puede emitir un design corto (3-5 líneas) y eso ya es disciplina suficiente.

Excepción: si el `task_type` detectado es `docs-only`, designer puede skipear automáticamente. El skill lo guía.

### 3.6 ¿Coordinación con Fase 07 Nivel 3 (review sessions)?

**Decisión:** **sin coordinación necesaria**. Fase 07 N3 agrega `CheckpointSource.CI_BOT` y `SessionMode.CI_REVIEW` — ambos son valores nuevos del enum, sin conflicto con `SessionRecord.tasks`. Las review sessions de CI pueden o no tener tasks; el comportamiento por default (lista vacía) es razonable para ambos casos.

### 3.7 ¿Coordinación con Fase 08 (Quality Gates)?

**Decisión:** **Fase 08 debe ir antes**. Si Fase 09 va primero:
- 09.B agrega el step `designer` al SDDwork prompt. Fase 08 después agrega el two-stage review entre cada subagent. El review automático en Fase 08 se aplica al designer también — sin conflicto, sólo coordinación de orden.
- 09.C extiende el documenter para reportar % completion. Fase 08 agrega self-review al documenter. Ambos cambios al mismo archivo (`persistence.py`) — Fase 08 primero evita merge manual.

Si Fase 08 ya fue ejecutada al iniciar Fase 09: el ejecutor de 09 absorbe los cambios sin esfuerzo extra.

---

## 4. Task Breakdown

### Sub-fase 09.A — Proposal step

#### T9.A.1 — Skill `cortex-sync.md` extendido con proposal

**Archivos a modificar:**
- `.cortex/skills/cortex-sync.md` — agregar sección "Proposal step (Fase 09.A)" antes del paso 4 (cortex_create_spec).
- `cortex/setup/cortex_workspace.py` — renderer sincronizado.

**Contenido a agregar al prompt:**

> ### 3.5 — Proposal step (Fase 09.A)
>
> Después de exploración (paso 3) y antes de `cortex_create_spec` (paso 4), **emití al usuario** un proposal corto en lenguaje natural:
>
> > "Propongo: [resumen ejecutivo de la implementación, 2-3 líneas].
> > Alternativas consideradas: [A — descartada porque...; B — descartada porque...; C — la elegida].
> > Riesgos principales: [scope drift / cambio de API / migración de datos / etc.].
> > ¿Procedo a spec? [y / edit / cancel]"
>
> - Si la respuesta es `y` o silencio: proceder a paso 4.
> - Si es `edit`: aceptar input del usuario y re-emitir el proposal hasta confirmación.
> - Si es `cancel`: parar; no crear spec.
>
> **Modo opcional vs required:** mirá el flag `proposal_mode` en `cortex_create_spec`. Si es `required`: NO procedés sin confirmación explícita. Si es `optional` (default): podés proceder en silencio después de emitir.

**Tests:** este es prompt only — los tests existentes del subagent (`test_canonical_subagent_files_in_disk_match_renders`) verifican que el hash entre el `.md` y el renderer coincide.

**Definition of Done T9.A.1:** skill actualizado, renderer sincronizado, hash test verde.

---

#### T9.A.2 — Flag `--proposal-mode` en `cortex_create_spec`

**Archivos a modificar:**
- `cortex/cli/main.py::create_spec` — agregar flag `--proposal-mode required|optional|skip` (default `optional`).
- `cortex/mcp/server.py::_create_spec_text` — aceptar `proposal_mode` en arguments.
- `cortex/services/spec_service.py::SpecService.create` — propagar `proposal_mode` y, si es `required`, validar que el caller provea evidencia de proposal (campo opcional `proposal_confirmed: bool = False`).

**Comportamiento:**

```bash
cortex create-spec --title X --goal Y --verification-hook ... \
    --proposal-mode required
# Si proposal_confirmed no se setea en el call siguiente, falla con:
# "✗ proposal_mode is 'required' but proposal was not confirmed; re-run cortex-sync to emit and confirm."
```

**Tests:**
- `test_create_spec_proposal_mode_optional_default` — default es optional.
- `test_create_spec_proposal_mode_required_fails_without_confirmation`.
- `test_create_spec_proposal_mode_skip_bypasses_check`.

**Definition of Done T9.A.2:** tests verdes; CLI + MCP signature consistentes.

---

#### T9.A.3 — Tests E2E del proposal flow

**Archivos a crear:**
- `tests/e2e/test_proposal_flow.py`

**Escenarios:**

```python
@pytest.mark.e2e
class TestProposalFlow:
    def test_proposal_optional_creates_spec_without_confirmation(tmp_repo):
        """Default optional mode: cortex create-spec procede aunque no haya proposal."""

    def test_proposal_required_blocks_without_confirmation(tmp_repo):
        """Required mode: falla con error claro cuando proposal_confirmed=False."""

    def test_proposal_required_succeeds_with_confirmation(tmp_repo):
        """Required mode + proposal_confirmed=True: crea spec normal."""
```

**Definition of Done T9.A.3:** 3 escenarios verdes.

---

#### Cierre Sub-fase 09.A — Completion Verification

```bash
pytest tests/unit/services/test_spec_service.py \
       tests/e2e/test_proposal_flow.py \
       tests/unit/ide/test_adapters_phase4.py --no-cov -v
# expected: all green

# Smoke: en un repo con cortex
cortex create-spec --title "test" --goal "..." \
    --verification-hook 'name=t;command=true' \
    --proposal-mode required
# expected: falla con mensaje claro
```

---

### Sub-fase 09.B — Design step

#### T9.B.1 — Nuevo subagent `cortex-code-designer.md`

**Archivos a crear:**
- `.cortex/subagents/cortex-code-designer.md`
- `cortex-pi/.pi/agents/cortex-code-designer.md`
- Entrada en `cortex/setup/cortex_workspace.py::render_subagent_designer()`.

**Estructura del prompt (esqueleto):**

```markdown
---
name: cortex-code-designer
description: Cortex DESIGN PHASE (Pluggable Middle Fase 09.B). Produce design.md before implementation. READ + write design doc only.
tools: read_file, glob, grep, write_design_note_canonical, cortex_session_checkpoint
---

# Cortex Code Designer — Fase de Diseño (Deep Track)

## Misión

Producir un design document estructurado a partir del spec, **antes** de
que el implementer escriba código. Tu output es un `vault/designs/<session_id>.md`
con secciones obligatorias.

## Pre-flight

- Confirmar sesión OPEN (`cortex_session_status`).
- Leer el spec (path en `session.spec_path`).
- Si el spec marca `task_type: docs-only`: emití un design mínimo (1-2 líneas justificando que no hay decisiones de arquitectura) y skipea a checkpoint.

## Flujo

1. Leer el spec completo + el checkpoint del explorer (si existió).
2. Decidir las 4 dimensiones del design:
   - Architecture decision (capas afectadas + por qué)
   - Data model changes (schemas/migrations/validators)
   - API contracts (signatures de funciones nuevas/cambiadas)
   - Test plan (qué tests escribir, en qué orden)
3. Invocar `write_design_note_canonical(...)` para persistir.
4. Emitir checkpoint con `source="cortex-code-designer"`.

## Anti-rationalization

| Pensamiento | Realidad | Acción |
|---|---|---|
| "Diseño obvio, no hace falta" | Si está obvio, escribilo en 5 líneas. La obviedad se rompe al codear. | Escribilo. |
| "Lo decide el implementer" | No. El implementer ejecuta el diseño. | Decidí vos. |
| "Skippeo el test plan" | El implementer va a improvisar tests. | Definí qué tests. |

## Output

Después del checkpoint, devolver control al SDDwork con:

> ✅ Design completado. Path: `vault/designs/<session_id>.md`. Checkpoint emitido. SDDwork: invoca al implementer.
```

**Definition of Done T9.B.1:** archivo creado, renderer sincronizado, hash test verde.

---

#### T9.B.2 — Nuevo `doc_type="design"`

**Archivos a crear:**
- `cortex/documentation/schemas/design.py` — Pydantic schema `DesignDocFrontmatter`.
- `cortex/documentation/templates/design.md.j2` — template Jinja2.

**Archivos a modificar:**
- `cortex/documentation/data.py` — agregar `DesignDocData` dataclass.
- `cortex/documentation/doc_type.py` — agregar `"design"` al enum.
- `cortex/documentation/writers.py` — agregar `write_design_note` + `write_design_note_canonical` (MCP-callable).
- `cortex/documentation/routing.py` — agregar entrada en la tabla canónica de routing.
- `cortex/mcp/server.py` — registrar `write_design_note_canonical` como MCP tool.
- `cortex/ide/canonical_tools.py` — agregar al vocabulario canónico.

**Schema esperado (`DesignDocData`):**

```python
@dataclass
class DesignDocData:
    title: str
    session_id: str       # link back al SessionRecord
    spec_path: str        # link back al spec
    tags: list[str]
    status: Literal["draft", "approved", "superseded"] = "draft"

    architecture_decision: str            # markdown body
    data_model_changes: list[str] = field(default_factory=list)
    api_contracts: list[str] = field(default_factory=list)
    test_plan: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
```

**Template (`design.md.j2`):**

```jinja2
---
title: "{{ title }}"
date: {{ date }}
tags: [design, {{ tags | join(", ") }}]
status: {{ status }}
session_id: {{ session_id }}
spec_path: {{ spec_path }}
doc_type: design
schema_version: 1
---

# {{ title }}

## Architecture decision
{{ architecture_decision }}

{% if data_model_changes %}
## Data model changes
{% for change in data_model_changes %}
- {{ change }}
{% endfor %}
{% endif %}

{% if api_contracts %}
## API contracts
{% for contract in api_contracts %}
- {{ contract }}
{% endfor %}
{% endif %}

{% if test_plan %}
## Test plan
{% for test in test_plan %}
- {{ test }}
{% endfor %}
{% endif %}

{% if risks %}
## Risks
{% for risk in risks %}
- {{ risk }}
{% endfor %}
{% endif %}

---
*Generated by cortex-code-designer subagent (Pluggable Middle Fase 09.B).*
```

**Tests obligatorios:**
- `test_design_doc_data_validation`
- `test_write_design_note_persists_to_vault_designs`
- `test_design_template_renders_all_sections`
- `test_design_template_omits_empty_sections`
- Test del routing canónico.

**Definition of Done T9.B.2:** 5+ tests verdes; MCP tool registrada.

---

#### T9.B.3 — Update SDDwork prompt (Deep Track: 4 pasos)

**Archivos a modificar:**
- `.cortex/skills/cortex-SDDwork.md` — Deep Track ahora es 4 pasos.
- `cortex/setup/cortex_workspace.py` — renderer sincronizado.

**Cambio al prompt:**

> ### 🔴 DEEP TRACK (4 pasos desde Fase 09.B)
>
> 1. Lee la spec.
> 2. Delega a `cortex-code-explorer`. Emite checkpoint.
> 3. **(NUEVO Fase 09.B)** Delega a `cortex-code-designer`. Emite checkpoint + persiste `vault/designs/<id>.md`. Excepción: si `task_type` es `docs-only`, el designer puede skipear con un design mínimo de 1 línea.
> 4. Delega a `cortex-code-implementer`. **El implementer recibe el path del design** (campo `design_path` en el contexto o referencia en el spec) y debe seguirlo. Emite checkpoint.
> 5. Emitís TU checkpoint final resumiendo los 3 anteriores.
> 6. Decile al usuario que corra `cortex finish-session`.

**Coordinación con Fase 08:** si Fase 08 ya está aplicada, el two-stage review se invoca **después de cada checkpoint** del designer también. Sin conflicto.

**Definition of Done T9.B.3:** skill + renderer sincronizados; hash test verde.

---

#### T9.B.4 — Tests E2E del Deep Track con designer

**Archivos a crear:**
- `tests/e2e/test_deep_track_with_designer.py`

**Escenarios:**

```python
@pytest.mark.e2e
class TestDeepTrackDesigner:
    def test_designer_produces_design_doc(tmp_repo_with_session):
        """Simula el flujo: explorer checkpoint, designer checkpoint + design doc, implementer checkpoint, finish."""

    def test_design_doc_persisted_to_vault_designs(tmp_repo_with_session):
        """vault/designs/<session_id>.md existe tras el flow."""

    def test_session_note_references_design_doc(tmp_repo_with_session):
        """El session note final tiene un link al design doc."""

    def test_docs_only_task_allows_minimal_design(tmp_repo_with_session):
        """task_type=docs-only: design doc puede ser corto, no falla."""
```

**Definition of Done T9.B.4:** 4 escenarios verdes.

---

#### T9.B.5 — Docs sub-fase 09.B

**Archivos a modificar:**
- `README.md` — agregar `cortex-code-designer` a la lista de subagents.
- `docs/architecture/session-primitive.md` — agregar sección "Design documents (Fase 09.B)".
- `docs/architecture/pluggable-middle-overview.md` §5 — agregar el designer al ecosistema.

**Definition of Done T9.B.5:** docs actualizadas.

---

#### Cierre Sub-fase 09.B — Completion Verification

```bash
pytest tests/unit/documentation/test_schemas.py \
       tests/unit/documentation/test_writers.py \
       tests/unit/ide/test_adapters_phase4.py \
       tests/e2e/test_deep_track_with_designer.py --no-cov -v
# expected: all green

# Smoke
cortex doctor   # should mention designer subagent available
ls .cortex/subagents/
# expected: cortex-code-designer.md present
```

---

### Sub-fase 09.C — Tasks granular

#### T9.C.1 — Modelo `Task` + extensión de `SessionRecord`

**Archivos a modificar:**
- `cortex/session/models.py` — agregar `TaskStatus` enum y `Task` model; extender `SessionRecord.tasks: list[Task] = Field(default_factory=list)`.
- `cortex/session/__init__.py` — exportar `Task`, `TaskStatus`.

**Modelo:**

```python
class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^T\d+(\.\d+)*$")  # e.g. T1, T1.1, T1.2.3
    description: str = Field(min_length=1)
    files_in_scope: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    completed_at: datetime | None = None
    checkpoint_index: int | None = None  # link to Session.checkpoints[i]
    note: str = ""  # short status note
```

**Tests obligatorios:**
- `test_task_id_pattern_validation`
- `test_task_default_status_pending`
- `test_session_record_tasks_default_empty`
- `test_session_record_loads_session_without_tasks_field` (compat con sessions viejas).
- `test_task_completed_at_required_when_done`.

**Definition of Done T9.C.1:** modelo extendido, 5+ tests verdes, sin regresiones en tests existentes de `SessionRecord`.

---

#### T9.C.2 — API en `SessionService` + CLI

**Archivos a modificar:**
- `cortex/session/service.py::SessionService` — agregar métodos:
  - `add_task(session_id, task) -> SessionRecord`
  - `update_task_status(session_id, task_id, status, *, note="", checkpoint_index=None) -> SessionRecord`
  - `list_tasks(session_id, status=None) -> list[Task]`
- `cortex/cli/session.py` — nuevo subapp `task` con commands `list / done / skip / block / in-progress`.

**CLI surface:**

```bash
cortex session task list [--session ID] [--status pending|done|...]
cortex session task done <task_id> [--note ...]
cortex session task in-progress <task_id> [--note ...]
cortex session task skip <task_id> --reason ...
cortex session task block <task_id> --reason ...
```

**Tests:**
- Unit tests del SessionService (5 tests).
- CliRunner tests del subapp (5 tests).

**Definition of Done T9.C.2:** API funcional, CLI funcional, 10+ tests verdes.

---

#### T9.C.3 — MCP tools `cortex_session_task_*`

**Archivos a modificar:**
- `cortex/mcp/server.py` — registrar `cortex_session_task_list` y `cortex_session_task_update`.
- `cortex/ide/canonical_tools.py` — vocabulario canónico.

**Tests:** 4 tests E2E del MCP.

**Definition of Done T9.C.3:** tools registradas, vocabulario actualizado, tests verdes.

---

#### T9.C.4 — SDDwork emite descomposición opt-in

**Archivos a modificar:**
- `cortex/cli/main.py::create_spec` — nuevo flag `--with-tasks` (default `False`).
- `cortex/services/spec_service.py` — propagar el flag al frontmatter del spec (`tasks_required: true`).
- `.cortex/skills/cortex-SDDwork.md` — si `spec.frontmatter.tasks_required`, después del designer (Deep Track), emitir `cortex_session_task_*` para cada task identificada.

**Skill prompt addendum:**

> ### Tasks granulares (Fase 09.C, opt-in)
>
> Si la spec marca `tasks_required: true` en frontmatter:
> 1. Después del designer (o post-explorer en Fast Track), identificá las tasks atómicas (1 task ≈ 1 archivo o 1 grupo coherente de cambios).
> 2. Por cada task, llamá `cortex_session_task_update(task_id=..., status="pending", description=..., files_in_scope=...)`.
> 3. Durante implementación, actualizá `status="in-progress"` al empezar y `status="done"` al completar (con `checkpoint_index` si corresponde).
>
> **Granularidad:** 3-10 tasks típicamente. Más de 15 es ruido. Si la spec lo justifica, anidá con dot-notation (T1, T1.1, T1.2).

**Definition of Done T9.C.4:** skill actualizado; renderer sincronizado.

---

#### T9.C.5 — Documenter reporta % completion

**Archivos a modificar:**
- `cortex/documenter/persistence.py::DocumenterPersister._write_session_note` — calcular `task_completion_percent` y agregarlo al summary del note.
- `cortex/documentation/templates/session.md.j2` — bloque condicional para mostrar el resumen de tasks si hay.

**Cambio al template:**

```jinja2
{% if tasks %}
## Tasks ({{ tasks_done }}/{{ tasks_total }} completed)
{% for task in tasks %}
- {{ task.id }} — {{ task.description }} `[{{ task.status }}]`
{% endfor %}
{% endif %}
```

**Tests:**
- `test_documenter_reports_task_completion_when_present`
- `test_documenter_omits_tasks_section_when_empty`
- `test_session_note_includes_skipped_count`

**Definition of Done T9.C.5:** 3 tests verdes; smoke con sesión que tiene 3 tasks done + 1 skipped renderiza correctamente.

---

#### T9.C.6 — Tests E2E completos sub-fase 09.C

**Archivos a crear:**
- `tests/e2e/test_tasks_granular_flow.py`

**Escenarios:**

```python
@pytest.mark.e2e
class TestTasksGranularFlow:
    def test_create_spec_with_tasks_flag_enables_tasks(tmp_repo):
        """--with-tasks marca el spec; SessionRecord tiene tasks: []."""

    def test_sddwork_emits_tasks_after_designer(tmp_repo):
        """Simula el flow Deep Track + tasks; tasks aparecen en SessionRecord."""

    def test_task_done_command_updates_status_and_emits_checkpoint(tmp_repo):
        """cortex session task done T1.1 → status=done + checkpoint linked."""

    def test_finish_session_reports_task_completion(tmp_repo):
        """Session note final tiene la sección Tasks con %."""

    def test_session_without_tasks_works_as_before(tmp_repo):
        """Compat: sessions sin --with-tasks NO tienen sección de tasks."""
```

**Definition of Done T9.C.6:** 5 escenarios verdes.

---

#### T9.C.7 — Docs sub-fase 09.C

**Archivos a modificar:**
- `README.md` — agregar comandos `cortex session task ...` a la tabla.
- `docs/architecture/session-primitive.md` — agregar sección §tasks-granular.
- `docs/architecture/pluggable-middle-overview.md` — actualizar diagramas.
- `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` — agregar a la tabla "what's new".
- `CHANGELOG.md` — entrada para 09.C.

**Definition of Done T9.C.7:** docs actualizadas.

---

#### Cierre Sub-fase 09.C (= cierre Fase 09)

```bash
pytest tests/unit/session/test_models.py \
       tests/unit/session/test_service.py \
       tests/unit/cli/test_session_cli.py \
       tests/unit/mcp/ \
       tests/e2e/test_tasks_granular_flow.py \
       tests/e2e/test_proposal_flow.py \
       tests/e2e/test_deep_track_with_designer.py --no-cov -v
# expected: all green

# Smoke del ciclo completo
cortex create-spec --title "demo" --goal "..." \
    --verification-hook 'name=t;command=true' \
    --with-tasks --proposal-mode required
# (interactive: confirmar proposal)
# Trabajar...
cortex session task list
cortex session task done T1
cortex finish-session
# Session note debe incluir sección Tasks.

# Full regression
pytest tests/ --no-cov --tb=no
# expected: 0 failed
```

---

## 5. Cross-cutting concerns

### 5.1 Compatibilidad

- `SessionRecord.tasks` con default `[]` — sessions YAML viejas cargan sin modificación.
- Nuevo `doc_type="design"` aditivo — no rompe routing existente.
- Nuevos subcomandos `cortex session task ...` no chocan con comandos existentes.
- Nuevas MCP tools aditivas.
- Nuevo subagent en disco — los IDEs que no lo conozcan simplemente no lo invocan.

### 5.2 Coordinación con otras fases

| Fase | Conflicto | Resolución |
|---|---|---|
| Fase 07 N3 (review sessions) | Ambas extienden enums/modelos | Aditivo. Cualquier orden. Pero si 07 N3 va antes, los tests de Fase 09 deben asumir presencia de `CheckpointSource.CI_BOT` (cero acción específica requerida). |
| Fase 08 (quality gates) | Ambas tocan SDDwork prompt + documenter persistence | **Fase 08 PRIMERO.** Fase 09 absorbe los cambios sin merge manual. |
| Fase 06 (TUI) | TUI no muestra tasks ni design docs | Fase 06 explícitamente fuera de scope. Iteración 06.1 post-MVP puede sumar paneles. |
| Fase 05 (opencode adapter) | Sin conflicto | Independiente. |

### 5.3 Performance

- `SessionRecord.tasks` con ~10 tasks agrega ~500 bytes al YAML. Serialize/deserialize <1ms. Despreciable.
- Designer subagent es 1 LLM call más por Deep Track. Costo aceptado: el design step justifica su costo en re-trabajo evitado.
- `cortex session task list` lee el YAML una vez y filtra in-memory. <10ms.

### 5.4 Observabilidad

- `cortex doctor` no necesita cambios obligatorios — la presencia del designer subagent es detectable por el check de skills existente (Fase 04 `pm_documenter_*`).
- Opcional: agregar al doctor un check `pm_designer_subagent_present` si el ejecutor lo considera útil.

### 5.5 Reglas anti-error preservadas

- Skill prompts cambiados → renderer sincronizado → hash test verde. Si rompe el hash, releé el handoff de Fase 02 para el procedimiento.
- Nuevos subagents: agregar tools al frontmatter (`tools: read_file, write_design_note_canonical, cortex_session_checkpoint`).
- Nueva MCP tool: registrar en vocabulary canónico + tests del adapter por IDE.

---

## 6. Completion Verification Commands

### 6.1 Cierre de Sub-fase 09.A

```bash
pytest tests/unit/services/test_spec_service.py tests/e2e/test_proposal_flow.py --no-cov -v
pytest tests/unit/ide/test_adapters_phase4.py --no-cov -q   # hash de skills
```

### 6.2 Cierre de Sub-fase 09.B

```bash
pytest tests/unit/documentation/test_writers.py tests/e2e/test_deep_track_with_designer.py --no-cov -v
ls .cortex/subagents/cortex-code-designer.md
ls cortex/documentation/templates/design.md.j2
```

### 6.3 Cierre de Sub-fase 09.C (= cierre Fase 09)

```bash
pytest tests/ --no-cov --tb=no
# expected: 0 failed; +20-30 tests netos vs baseline pre-Fase 09

mypy --strict --follow-imports=silent cortex/session/models.py cortex/session/service.py
ruff check cortex/
# expected: clean
```

---

## 7. Handoff to next phase

Al cerrar Fase 09 (las 3 sub-fases):

### Artefactos producidos

| Artefacto | Path |
|---|---|
| `Task` model + extensión `SessionRecord.tasks` | `cortex/session/models.py` |
| Task CRUD API | `cortex/session/service.py` |
| CLI subapp `task` | `cortex/cli/session.py` |
| MCP tools `cortex_session_task_*` | `cortex/mcp/server.py` |
| Nuevo subagent designer | `.cortex/subagents/cortex-code-designer.md` + Pi version |
| Nuevo `doc_type="design"` | `cortex/documentation/{schemas,data,doc_type,writers,routing,templates}.py` |
| MCP tool `write_design_note_canonical` | `cortex/mcp/server.py` |
| Skill cortex-sync con proposal | `.cortex/skills/cortex-sync.md` |
| Skill cortex-SDDwork con designer + tasks | `.cortex/skills/cortex-SDDwork.md` |
| Tests | `tests/{unit,e2e}/test_proposal_flow.py`, `test_deep_track_with_designer.py`, `test_tasks_granular_flow.py` |
| Docs actualizadas | README, session-primitive.md, overview, MIGRATION |

### Lo que el ecosistema gana

- **SDD profundo**: workflow openspec-style cubierto ~90% (faltan sync/archive explícitos, marginales).
- **Trazabilidad granular**: cada task es un commit semántico identificable.
- **Mejor session notes**: % completion + design doc linkeado = audit trail completo.
- **Menos re-trabajo**: design step previene decisiones inline en Deep Track.

---

## 8. Progress Log

### Sub-fase 09.A — Proposal step
- [x] T9.A.1 — Skill cortex-sync extendido con proposal (2026-05-17)
- [x] T9.A.2 — Flag `--proposal-mode` en `cortex_create_spec` (2026-05-17) — CLI + MCP + `SpecService.create` validan los 3 modos.
- [x] T9.A.3 — Tests E2E del proposal flow (2026-05-17) — 6 escenarios en `tests/e2e/test_proposal_flow.py` + 6 unit tests en `test_spec_service_proposal_mode.py`.
- [x] Completion Verification 09.A pasa (2026-05-17)

### Sub-fase 09.B — Design step
- [x] T9.B.1 — Nuevo subagent `cortex-code-designer` (2026-05-17) — `.cortex/subagents/` + `cortex-pi/.pi/agents/` + renderer sincronizado.
- [x] T9.B.2 — Nuevo `doc_type="design"` (2026-05-17) — `DesignDocData`, `DesignFrontmatter`, `design.md.j2`, routing, `write_design_note` + alias.
- [x] T9.B.3 — Update SDDwork Deep Track a 4 pasos (2026-05-17) — incluye review checkpoint del designer (coordinación Fase 08).
- [x] T9.B.4 — Tests E2E del Deep Track con designer (2026-05-17) — 15 tests en `test_design_doc.py` + 4 en `test_write_design_note_tool.py`.
- [x] T9.B.5 — Docs sub-fase 09.B (2026-05-17) — README + session-primitive.md + overview + MIGRATION.
- [x] Completion Verification 09.B pasa (2026-05-17)

### Sub-fase 09.C — Tasks granular
- [x] T9.C.1 — `Task` model + extensión `SessionRecord.tasks` (2026-05-17) — `TaskStatus`, `Task` con id pattern `T<n>(.<n>)*`, invariantes status/completed_at.
- [x] T9.C.2 — API `SessionService` + CLI `cortex session task` (2026-05-17) — add_task / update_task_status / list_tasks + subapp `list/done/in-progress/skip/block`.
- [x] T9.C.3 — MCP tools `cortex_session_task_*` (2026-05-17) — list + update (create-or-update). Canonical_tools actualizado.
- [x] T9.C.4 — SDDwork emite descomposición opt-in (2026-05-17) — `--with-tasks` agrega tag `tasks-required`; skill addendum guía la emisión.
- [x] T9.C.5 — Documenter reporta % completion (2026-05-17) — `tasks: X/Y done (Z skipped)` en summary + bloque `## Tasks` en session.md.j2.
- [x] T9.C.6 — Tests E2E completos sub-fase 09.C (2026-05-17) — 22 unit (model+service) + 9 CLI + 5 MCP + 2 persister.
- [x] T9.C.7 — Docs sub-fase 09.C (2026-05-17) — CHANGELOG + README + session-primitive.md + MIGRATION.

### Cierre Fase 09
- [x] Completion Verification 09.C (= cierre fase) pasa (2026-05-17)
- [x] Tabla `../README.md` actualizada ✅ (2026-05-17)
- [ ] Commit final (pendiente — esperando autorización del usuario al cierre de todas las fases)

---

## 9. Notas para el agente ejecutor

- **Ejecutá nivel-por-nivel.** Cada sub-fase cierra completa antes de la siguiente. 09.A es trivial (3 días), 09.B es media (1 semana), 09.C es la más grande (1.5 semanas). Mergeable de a uno.
- **Coordinación Fase 08:** verificá `08-MANAGED-QUALITY-GATES.md` antes de tocar el SDDwork prompt. Si Fase 08 ya se aplicó: el two-stage review se invoca después de **cada** subagent (explorer / designer / implementer). Mantené esa secuencia.
- **Coordinación Fase 07 N3:** si la review-session feature ya existe, validá que tu test de `cortex session task list` también funcione sobre review-sessions (no es esperable que las tengan, pero no debe romperse).
- **Naming de tasks:** seguí `T1`, `T1.1`, `T1.2.3`. El regex en el modelo lo enforza. No inventes `task-1`, `t1`, etc.
- **Designer NO improvisa.** El subagent debe seguir el template exacto (4 secciones obligatorias). Si en el prompt te tienta dar libertad creativa: no. La rigidez es el feature.
- **Tasks granulares son OPT-IN.** Fast Track jamás emite tasks. Deep Track sin `--with-tasks` tampoco. Default = ningún task. Esto evita que usuarios de tareas chicas se vean forzados a la complejidad.
- **Sin keyboard interactivo en la TUI para tasks.** Si te tienta agregar `t` para marcar task done en la TUI: NO. Es scope de iteración post-MVP de Fase 06.
- **Renderer del session.md.j2** ya tiene branchs condicionales por Fase 08. Asegurate de no romper esos branchs al agregar el bloque de tasks.
