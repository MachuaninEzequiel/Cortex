# Fase 08 — Managed Quality Gates restaurados

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 04 cerrada · **Coordina con:** Fase 09 (debe ejecutarse ANTES) · **Esfuerzo estimado:** ~1.5 semanas

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 08 |
| Nombre | Managed Quality Gates restaurados |
| Versión del plan | 1.0 |
| Dependencias | Fase 04 cerrada (Sessions, documenter, hooks, doctor completos). |
| Output principal | Restaura 5 mecanismos de calidad que la migración Pluggable Middle eliminó/dejó sin wiring. Cubre deuda silenciosa identificada en el análisis crítico post-Fase 04. |
| Breaking changes | Ninguno. Cero cambios al modelo de datos. Sólo agrega validaciones, rollback transaccional, y wiring perdido. |

---

## 0.1 Origen de esta fase

Esta fase **no está en el roadmap original de Pluggable Middle**. Nace del análisis crítico post-Fase 04 que identificó 5 piezas eliminadas en Fase 03 cuyo valor conceptual no fue plenamente trasladado a la nueva arquitectura. **No reintroduce los archivos viejos en su path original** — porta la lógica a los nuevos owners (documenter, SDDwork, context_enricher).

Documento de origen: ver el análisis "Pregunta 1 — Archivos eliminados que podrían ser útiles para Managed" en la conversación post-Fase 04.

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md) §10.5 (Autopilot fusion) — para entender por qué los archivos se eliminaron originalmente.
- [`fases/_internal/autopilot-audit.md`](_internal/autopilot-audit.md) — la auditoría de Fase 03 que documentó cada eliminación y su razón.
- [`fases/03-AUTOPILOT-FUSION.md`](03-AUTOPILOT-FUSION.md) §11 — decisiones abiertas que generaron las eliminaciones (`§11.2 delegation.py`, `§11.4 build_context`, etc.).

### 1.2 Código que vas a tocar

Leé enteros:

- `cortex/documenter/persistence.py` — donde se restaura el `self_review` y se verifica el rollback transaccional.
- `cortex/documenter/reconstruction.py` — para entender qué quality data ya está disponible en la `ReconstructionOutput`.
- `cortex/services/note_service.py::NoteService.create` — el método que persiste + indexa. Acá hay que confirmar si el rollback existe.
- `.cortex/skills/cortex-SDDwork.md` y su renderer en `cortex/setup/cortex_workspace.py` — donde se agrega el two-stage review al flow de Deep Track.
- `cortex/context_enricher/enricher.py` — para entender la API `enrich(top_k=...)` y wirearla al SDDwork.
- `cortex/documentation/templates/session.md.j2` — donde se agrega rendering condicional por `task_type`.
- `cortex/autopilot/detectors/` — los detectors que ya están vivos y se usan para clasificar task_type (input para el budget profile selection).

Leé bajo demanda:

- Git history del archivo `cortex/autopilot/delegation.py` antes de su eliminación en Fase 03 — el código sirve como referencia conceptual para la nueva implementación. **NO restaurar el archivo en su path original**; portar la lógica.
- Git history de `cortex/autopilot/session_builder.py::self_review` y `cortex/autopilot/session_writer.py::IndexingSessionWriter`.

### 1.3 Documentación externa

- No hay dependencias externas nuevas. Toda la fase usa librerías ya presentes (Pydantic v2, Jinja2, subprocess).

---

## 2. Goal

Al finalizar esta fase:

1. **Rollback transaccional verificado o restaurado** en la pipeline de persistencia del documenter. Invariante garantizada: **"file en disco ⇒ file indexado en memoria semántica + episódica"**. Si el indexing falla post-write, el file persistido se elimina y la excepción propaga.
2. **Two-stage review automático** corre entre subagents en Deep Track del SDDwork. Después de que `cortex-code-explorer` o `cortex-code-implementer` emiten su checkpoint, SDDwork valida (a) spec compliance — files dentro de scope, status no fallido; (b) quality — claims verificadas. Si falla stage 1: SDDwork pide re-delegate. Si falla stage 2: el checkpoint del SDDwork lo marca con `unverified_claims` para que el documenter lo surface.
3. **Self-review del draft de session note** antes de persistir. Scan automático de:
   - Placeholders (`TODO`, `FIXME`, `XXX`, `[pendiente]`, `???`, `TBD`, `fill me`).
   - Consistencia: cada archivo en `changed_files` aparece referenciado en el body del note.
   - Evidencia: si el body declara "tests pass" / "build successful" / "lint clean" pero ningún `verification_results.passed` está `True`, downgrade la `confidence` del note a `auto-draft` y agrega warning.
4. **Budget profile wiring** entre SDDwork y `cortex.context_enricher`. Cuando el SDDwork llama a `cortex_context` (vía MCP) o equivalente, pasa el `top_k` y `max_chars` derivados del `task_type` detectado por el `AutopilotDetector` pipeline. Hoy usa default sin profile.
5. **Renderer condicional por `task_type` en `session.md.j2`**. Reusa la información del `DetectionResult` para producir secciones diferenciadas:
   - `question-only` / `docs-only` → template minimal (sin secciones de "Files Changed" / "Tests").
   - `fast-code` / `deep-code` → template completo (current).
   - `security` → template completo + sección destacada "Security review" con verified_claims relevantes.
6. **Tests + docs** que cubren los 5 puntos. Coverage > 85% en código nuevo. Documentación actualizada en `docs/architecture/session-primitive.md` §quality-gates y en el subagent prompt del SDDwork.

**Lo que NO se hace en esta fase:**

- ❌ NO se reintroduce `cortex/autopilot/{delegation,session_builder,session_writer,context,budget_profiles,context_budget}.py` en su path original. La lógica se porta a los nuevos owners.
- ❌ NO se reintroduce el módulo `cortex/autopilot/renderers/` — el rendering vive en el template Jinja2 del documenter (`cortex/documentation/templates/session.md.j2`).
- ❌ NO se agregan campos al `SessionRecord` (eso es Fase 09).
- ❌ NO se agregan steps nuevos al workflow SDD (proposal / design / tasks granular) — eso es Fase 09.
- ❌ NO se cambia la API pública de la `SessionService`, `DocumenterPersister`, `Reconstructor`, ni MCP tools. Cero breaking changes.

---

## 3. Decisiones de diseño clave

### 3.1 ¿Por qué portar la lógica en lugar de reintroducir los archivos?

**Decisión:** portar. Los archivos viejos vivían dentro del módulo `cortex/autopilot/` cuando Autopilot era una capa paralela. Post-Fase 03, Autopilot es un wrapper delgado y el dueño real de la pipeline de persistencia es el **documenter**, y el dueño de la pipeline de orquestación es el **SDDwork skill prompt** (no código Python). Reintroducir los archivos en `cortex/autopilot/` rompería la cleanness arquitectural lograda en Fase 03.

### 3.2 ¿Two-stage review como código Python o como instrucción en el prompt?

**Decisión:** **híbrido**. La lógica de validación es una **función pura** en `cortex/session/quality_gates.py` (nuevo módulo) que toma un `Checkpoint` + `LoadedSpec` y retorna un `ReviewVerdict`. El SDDwork prompt instruye al subagent orquestador a llamar a esa función vía una nueva MCP tool `cortex_review_checkpoint` (también nueva).

Razones:
- La lógica de validación es determinística: no hay razón para que el LLM la haga.
- Exponerla como MCP tool permite que cualquier orquestador (SDDwork, futuros agentes custom) la use.
- El skill prompt se mantiene corto: una línea "después del checkpoint del subagent, llamá `cortex_review_checkpoint`".

### 3.3 ¿Dónde vive el self-review del documenter?

**Decisión:** en `cortex/documenter/persistence.py::DocumenterPersister._self_review_draft()` (método privado nuevo). Se invoca dentro de `_write_session_note` justo antes del `note_service.create(...)`. Si encuentra issues:
- Agrega `extra_warnings` al note (visible en el frontmatter `tags: [..., auto-draft]`).
- Si hay >3 placeholders o falla evidencia: downgrade del `confidence` field del note metadata.
- NO bloquea la persistencia — siempre escribe; el quality gate es informativo, no terminal.

Razón: ya bloqueamos en otros puntos (verification hooks fallidos → HANDOFF). Otro bloqueo aquí causaría loops infinitos en el flujo. La señal "auto-draft" es suficiente para que el usuario sepa que el note merece revisión.

### 3.4 ¿Cómo decide el SDDwork qué budget profile usar?

**Decisión:** la decisión vive en `cortex/context_enricher/budget_resolver.py` (nuevo, ~30 LOC). Función pura `resolve_budget_profile(task_type: str | None, complexity: str | None) -> dict[str, int]` que mapea:

| task_type | complexity | top_k | max_chars |
|---|---|---|---|
| `question-only` | * | 0 | 0 |
| `docs-only` | * | 3 | 1200 |
| `fast-code` | `fast` | 5 | 2000 |
| `deep-code` | `deep` | 8 | 3500 |
| `security` | * | 8 | 3500 |
| `ambiguous` / `noop` / None | * | 3 | 1500 |

Estos valores **provienen de los profiles eliminados** (`cortex/autopilot/context_budget.py::BUDGET_PROFILES`). Se restauran exactos. La función pura es testeable y reusable por cualquier caller del context_enricher.

### 3.5 ¿Cómo se logra rendering condicional sin proliferar templates?

**Decisión:** un solo `session.md.j2` con bloques `{% if task_type == "..." %}...{% endif %}`. NO se restauran los 5 renderers eliminados. La lógica adicional dentro del template es ~30 líneas Jinja2.

Variable pasada al template: `task_type` (string) — el documenter ya lo tiene en `reconstruction.spec.frontmatter.get("task_type")` o lo calcula vía detectors si falta.

### 3.6 ¿`cortex_review_checkpoint` es MCP tool nueva — rompe stability?

**Decisión:** agregarla NO es breaking — los MCP tools son aditivos. Pero hay que registrarla en `cortex/ide/canonical_tools.py` y validar que ningún test asume "exactly N tools". Bajo riesgo.

---

## 4. Task Breakdown

### T8.1 — Auditoría del rollback transaccional (investigación + posible fix)

**Objetivo:** confirmar si el invariante "file en disco ⇒ file indexado" se preserva post-Fase 03, o si la migración lo rompió.

**Acción:**
1. Leer `cortex/services/note_service.py::NoteService.create` y `cortex/documenter/persistence.py::DocumenterPersister.finalize`.
2. Trazar el flow: ¿qué pasa si el `note_service.create` escribe el file y el step de indexing falla? ¿Hay rollback?
3. Si NO hay rollback: documentar el caso y **portar la lógica del eliminado `IndexingSessionWriter` al `NoteService` o al `DocumenterPersister`** (la decisión depende de la arquitectura real — el ejecutor decide al ver el código).
4. Si SÍ hay rollback: documentar la evidencia y cerrar T8.1 sin código.

**Tests obligatorios (si se restaura rollback):**

- `test_indexing_failure_unlinks_persisted_file` — mock del semantic index para que falle; verifica que el `.md` no queda huérfano.
- `test_indexing_failure_propagates_exception` — el caller recibe la excepción, no un éxito silencioso.
- `test_indexing_success_preserves_file` — happy path no toca el file.

**Definition of Done T8.1:**
- Documento corto (`docs/pluggable-middle/fases/_internal/rollback-audit-fase08.md`) con el hallazgo: "presente" o "ausente + restaurado en X".
- Si se restauró: 3 tests verdes.

---

### T8.2 — Two-stage review entre subagents (Deep Track)

**Objetivo:** cada subagent que emite un checkpoint en Deep Track del SDDwork dispara una validación automática de spec compliance + quality.

**Archivos a crear:**
- `cortex/session/quality_gates.py` — función pura `review_checkpoint(checkpoint, spec) -> ReviewVerdict`.
- `cortex/mcp/server.py` — registrar la nueva tool `cortex_review_checkpoint` (delegando a la función pura).
- `cortex/ide/canonical_tools.py` — agregar `cortex_review_checkpoint` al vocabulario canónico.
- `tests/unit/session/test_quality_gates.py`.

**Archivos a modificar:**
- `.cortex/skills/cortex-SDDwork.md` — Deep Track sub-flujo: después de cada delegate, instruir al orquestador a llamar `cortex_review_checkpoint`.
- `cortex/setup/cortex_workspace.py` — renderer del skill sincronizado.

**API esperada:**

```python
# cortex/session/quality_gates.py
from dataclasses import dataclass
from typing import Literal
from cortex.session.models import Checkpoint
from cortex.documenter.spec_loader import LoadedSpec


@dataclass(frozen=True)
class ReviewVerdict:
    accepted: bool
    stage_1_passed: bool   # spec compliance
    stage_2_passed: bool   # quality
    reason: str
    action: Literal["accept", "redelegate", "warn"]


def review_checkpoint(checkpoint: Checkpoint, spec: LoadedSpec) -> ReviewVerdict:
    """Two-stage review of a checkpoint emitted by a subagent.

    Stage 1 — spec compliance:
        - artifacts_touched ⊆ spec.files_in_scope (allow empty scope as wildcard).
        - At least one verified_claim OR artifacts_touched not empty.

    Stage 2 — quality:
        - No "TBD"/"FIXME"/"???" in note.
        - If verified_claims mention "tests" or "build", at least one
          verified_claims string is non-trivial (>10 chars).
    """
    # ... implementation per the deleted cortex/autopilot/delegation.py
```

**Tests obligatorios:**
- `test_review_accept_when_compliant_and_quality_ok`
- `test_review_redelegate_when_out_of_scope`
- `test_review_warn_when_tbd_in_note`
- `test_review_warn_when_test_claims_without_evidence`
- `test_review_handles_empty_spec_scope_as_wildcard`

**Skill prompt — change to `.cortex/skills/cortex-SDDwork.md`:**

Después del bloque "Deep Track", agregar:

> 5b. Después de que cada subagent emite su checkpoint, **invocá**
> `cortex_review_checkpoint(checkpoint_index=N)`. Si la respuesta es
> `action: "redelegate"`, repetí la delegación con guidance corregido.
> Si es `action: "warn"`, propagá el reason al campo `unverified_claims`
> de tu propio checkpoint final.

**Definition of Done T8.2:**
- 5 tests verdes; cobertura del módulo nuevo > 90%.
- Skill + renderer sincronizados (hash test verde).
- MCP tool registrada y vocabulario canónico actualizado.

---

### T8.3 — Self-review del documenter

**Objetivo:** scan automático del draft del session note antes de persistir, downgrade de confidence si hay issues.

**Archivos a modificar:**
- `cortex/documenter/persistence.py::DocumenterPersister` — agregar método privado `_self_review_draft(reconstruction, draft_payload) -> list[str]` (retorna warnings).
- `cortex/documenter/persistence.py::DocumenterPersister._write_session_note` — invocar `_self_review_draft` antes del `note_service.create`. Si warnings: agregar `auto-draft` tag, append a `warnings` field del note.

**API esperada:**

```python
# Within DocumenterPersister
_PLACEHOLDER_TOKENS = frozenset({
    "tbd", "todo", "fixme", "xxx", "???", "fill me", "[pendiente]",
})
_SUCCESS_CLAIM_PATTERNS = frozenset({
    "tests pass", "test passed", "build exitoso", "build successful",
    "linter clean", "lint passed", "verified", "checks pass", "ci passed",
})


def _self_review_draft(
    self,
    reconstruction: ReconstructionOutput,
    draft_body: str,
) -> list[str]:
    """Run quality scans on the about-to-persist draft.

    Returns a list of warnings. Empty list means clean.
    """
    warnings: list[str] = []
    body_lower = draft_body.lower()

    # 1. Placeholder scan
    found = [t for t in _PLACEHOLDER_TOKENS if t in body_lower]
    if found:
        warnings.append(f"Placeholders detected in draft: {sorted(found)}")

    # 2. File consistency
    body_paths = {p.as_posix() for p in reconstruction.files_touched}
    missing = [p for p in body_paths if p not in draft_body]
    if missing:
        warnings.append(f"Files touched but not mentioned in body: {missing}")

    # 3. Evidence check
    has_claim = any(c in body_lower for c in _SUCCESS_CLAIM_PATTERNS)
    has_verified = any(r.passed for r in reconstruction.verification_results)
    if has_claim and not has_verified:
        warnings.append("Success claim in body without any verified hook result")

    return warnings
```

**Tests obligatorios:**
- `test_self_review_clean_returns_empty_list`
- `test_self_review_detects_placeholders`
- `test_self_review_detects_unreferenced_files`
- `test_self_review_detects_unverified_claims`
- `test_self_review_warnings_propagate_to_note_tags`
- E2E: full BYO flow with a forced TBD in spec → session note tiene tag `auto-draft`.

**Definition of Done T8.3:** tests verdes; el note creado en presencia de warnings tiene `tags: [..., auto-draft]`.

---

### T8.4 — Budget profile wiring SDDwork → context_enricher

**Objetivo:** que el SDDwork pase el budget profile correcto al context_enricher según el task_type detectado.

**Archivos a crear:**
- `cortex/context_enricher/budget_resolver.py` — función pura `resolve_budget_profile(task_type, complexity) -> dict[str, int]`.
- `tests/unit/context_enricher/test_budget_resolver.py`.

**Archivos a modificar:**
- `cortex/mcp/server.py::_context_text` — si el caller pasa `task_type` en arguments, derivar `top_k` automáticamente vía `resolve_budget_profile`. Sin breaking change: si no se pasa, default sigue siendo el actual.
- `.cortex/skills/cortex-SDDwork.md` — Fast/Deep Track: instruir al orquestador a pasar `task_type` cuando invoque `cortex_context`.

**API esperada:**

```python
# cortex/context_enricher/budget_resolver.py

_BUDGET_PROFILES: dict[str, dict[str, int]] = {
    "question-only": {"top_k": 0, "max_chars": 0},
    "docs-only":     {"top_k": 3, "max_chars": 1200},
    "fast-code":     {"top_k": 5, "max_chars": 2000},
    "deep-code":     {"top_k": 8, "max_chars": 3500},
    "security":      {"top_k": 8, "max_chars": 3500},
    "ambiguous":     {"top_k": 3, "max_chars": 1500},
    "noop":          {"top_k": 0, "max_chars": 0},
}

_DEFAULT = {"top_k": 5, "max_chars": 2000}


def resolve_budget_profile(
    task_type: str | None = None,
    complexity: str | None = None,
) -> dict[str, int]:
    """Map a detected task_type to a budget envelope for context retrieval.

    Falls back to the fast-code profile on unknown task_types so we never
    starve the caller of context — but logs a warning at debug level.
    """
    if task_type and task_type in _BUDGET_PROFILES:
        return dict(_BUDGET_PROFILES[task_type])
    return dict(_DEFAULT)
```

**Tests obligatorios:**
- Tests por cada profile.
- Fallback a default si task_type unknown.
- Fallback a default si task_type es None.

**Skill prompt — change to `.cortex/skills/cortex-SDDwork.md`:**

> Cuando invoques `cortex_context` para enriquecer, **pasá** el `task_type`
> que el detector identificó (Fast/Deep/Security/etc.). Esto activa el budget
> profile correcto y ahorra tokens.

**Definition of Done T8.4:** tests verdes; `cortex_context` MCP tool respeta `task_type` cuando se pasa; skill prompt + renderer sincronizados.

---

### T8.5 — Renderer condicional en `session.md.j2`

**Objetivo:** secciones del session note se incluyen/excluyen según `task_type`.

**Archivos a modificar:**
- `cortex/documentation/templates/session.md.j2` — agregar bloques `{% if %}` por task_type.
- `cortex/documenter/persistence.py` — pasar `task_type` al template via `note_service.create(extra_template_vars={"task_type": ...})` (verificar si existe ese hook; si no, agregar).
- `cortex/services/note_service.py::NoteService.create` — aceptar y propagar `extra_template_vars`.

**Cambios al template (esqueleto):**

```jinja2
{# session.md.j2 #}
---
title: "{{ title }}"
date: {{ date }}
{% if confidence == "auto-draft" %}tags: [{{ tags | join(", ") }}, auto-draft]{% else %}tags: [{{ tags | join(", ") }}]{% endif %}
status: {{ status }}
task_type: {{ task_type | default("unspecified") }}
---

# {{ title }}

## Goal
{{ spec_summary }}

{% if task_type not in ["question-only", "docs-only"] %}
## Changes made
{% for entry in changes_made %}
- {{ entry }}
{% endfor %}

## Files touched
{% for f in files_touched %}
- `{{ f }}`
{% endfor %}
{% endif %}

{% if task_type == "security" %}
## ⚠ Security review notes
{% for claim in verified_state %}
- ✓ {{ claim }}
{% endfor %}
{% for claim in unverified_claims %}
- ⏸ {{ claim }} (unverified)
{% endfor %}
{% endif %}

## Key decisions
{% for d in key_decisions %}
- {{ d }}
{% endfor %}

{# ... resto del template existente ... #}
```

**Tests obligatorios:**
- `test_template_question_only_omits_files_section`
- `test_template_security_adds_security_review_section`
- `test_template_deep_code_includes_all_sections`
- Snapshot tests con casos canónicos.

**Definition of Done T8.5:** rendering condicional funcional; tests verdes; sin regresiones en tests existentes del documenter.

---

### T8.6 — Tests + docs

**Archivos a modificar:**
- `docs/architecture/session-primitive.md` — agregar sección §quality-gates explicando los 5 mecanismos.
- `docs/architecture/pluggable-middle-overview.md` §9 — agregar mención del quality gate.
- `README.md` §"Comandos Sessions" — sin cambios necesarios (los gates son internos).
- `CHANGELOG.md` — entrada nueva.
- `docs/pluggable-middle/README.md` — marcar Fase 08 ✅.
- `docs/pluggable-middle/MIGRATION-FROM-TRIPARTITO.md` §6 — agregar entrada de `cortex_review_checkpoint` MCP tool al mapping de "what's new".

**Definition of Done T8.6:** docs actualizadas; el CHANGELOG documenta los 5 mecanismos restaurados.

---

## 5. Cross-cutting concerns

### 5.1 Compatibilidad

- Cero cambios al modelo de datos. `SessionRecord`, `Checkpoint`, `VerificationHookResult` no se tocan.
- Nueva MCP tool `cortex_review_checkpoint` es aditiva. Consumers viejos siguen funcionando.
- Self-review del documenter es **informativo, no terminal** — no bloquea persistencia, sólo agrega warnings/tags.
- Budget resolver tiene **fallback al default actual** si no se pasa task_type. Sin breaking en consumers que no migraron.

### 5.2 Coordinación con Fase 09

- **Fase 08 debe ejecutarse ANTES que Fase 09.** Razón: Fase 09 sub-fase 09.B agrega el step "design" al Deep Track del SDDwork prompt; Fase 08 ya modifica el mismo prompt para agregar el two-stage review. Si Fase 09 va primero, el ejecutor de Fase 08 tiene que mergear los dos cambios al prompt manualmente.
- El `cortex/documenter/persistence.py` también se toca en ambas fases (Fase 08: self-review; Fase 09 sub-fase 09.C: % tasks completion en summary). Igual: Fase 08 primero, Fase 09 segundo, sin conflicto.

### 5.3 Performance

- `cortex_review_checkpoint` es una llamada MCP por subagent en Deep Track. Latencia esperada <100ms (es cálculo puro en proceso). Despreciable.
- Self-review del documenter: 3 scans textuales sobre el draft body. <10ms para drafts típicos (<10KB).
- Budget resolver: lookup en dict. <0.1ms.
- Rollback transaccional: cero overhead en happy path (sólo se ejecuta el unlink en falla).

### 5.4 Observabilidad

- Cada warning del self-review se loguea a INFO con el `session_id` para diagnóstico.
- Los `ReviewVerdict` con `action="redelegate"` se loguean a WARNING.
- `cortex doctor` no necesita cambios — los quality gates son flujo interno; el doctor ya valida que el documenter sea invocable (Fase 04 `pm_documenter_module`).

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Tests del módulo nuevo + integración
pytest tests/unit/session/test_quality_gates.py \
       tests/unit/context_enricher/test_budget_resolver.py \
       tests/unit/documenter/test_persistence.py \
       tests/unit/services/test_note_service.py \
       --no-cov -v
# expected: all green

# 2. Tests E2E sin regresión
pytest tests/e2e/ --no-cov --tb=no
# expected: 0 failed (baseline pre-Fase 08: 1743 passed)

# 3. mypy strict
mypy --strict --follow-imports=silent \
     cortex/session/quality_gates.py \
     cortex/context_enricher/budget_resolver.py
# expected: clean

# 4. ruff
ruff check cortex/session/quality_gates.py \
           cortex/context_enricher/budget_resolver.py \
           tests/unit/session/test_quality_gates.py \
           tests/unit/context_enricher/test_budget_resolver.py
# expected: clean

# 5. MCP tool registered
python -c "from cortex.mcp.server import CortexMCPServer; \
           assert 'cortex_review_checkpoint' in str(CortexMCPServer)"
# expected: ok

# 6. Hash test del skill sincronizado
pytest tests/unit/ide/test_adapters_phase4.py --no-cov -q
# expected: all green
```

---

## 7. Handoff to next phase

Al cerrar Fase 08:

### Artefactos producidos

| Artefacto | Path |
|---|---|
| Quality gates module | `cortex/session/quality_gates.py` |
| Budget resolver | `cortex/context_enricher/budget_resolver.py` |
| Self-review en documenter | método privado en `cortex/documenter/persistence.py` |
| Rollback transaccional | restaurado en `NoteService` o `DocumenterPersister` |
| Renderer condicional | `cortex/documentation/templates/session.md.j2` extendido |
| Nueva MCP tool | `cortex_review_checkpoint` en `cortex/mcp/server.py` |
| Vocabulario canónico | `cortex_review_checkpoint` en `cortex/ide/canonical_tools.py` |
| Skill SDDwork sincronizado | `.cortex/skills/cortex-SDDwork.md` + renderer |
| Tests | `tests/unit/session/test_quality_gates.py`, `tests/unit/context_enricher/test_budget_resolver.py` |
| Audit doc interno | `docs/pluggable-middle/fases/_internal/rollback-audit-fase08.md` |

### Lo que Fase 09 puede asumir

1. El SDDwork ya tiene quality gates entre subagents — el step "design" que Fase 09 sub-fase 09.B agrega también pasa por el review.
2. El documenter ya hace self-review del draft — el reporting de `% tasks completion` que Fase 09 sub-fase 09.C agrega NO necesita re-implementar scans.
3. El budget profile wiring está vivo — Fase 09 puede confiar en que el SDDwork ya optimiza tokens según task_type.

---

## 8. Progress Log

- [x] T8.1 — Auditoría del rollback transaccional (2026-05-17) — **Ausente, restaurado.** Lógica portada del eliminado `IndexingSessionWriter` a `NoteService.create`. 5 tests verdes. Audit doc: [`_internal/rollback-audit-fase08.md`](_internal/rollback-audit-fase08.md).
- [x] T8.2 — Two-stage review entre subagents (2026-05-17) — Nuevo módulo `cortex/session/quality_gates.py` (función pura). MCP tool `cortex_review_checkpoint` registrada + `canonical_tools.py` actualizado. Skill `cortex-SDDwork.md` + renderer sincronizados (hash test verde). 8 tests cubren ambos stages + edge cases.
- [x] T8.3 — Self-review del documenter (2026-05-17) — `_self_review_draft` staticmethod en `DocumenterPersister`. Scan de placeholders / consistencia de archivos / evidencia. Informativo no bloqueante: agrega tag `auto-draft` + warnings al `next_steps`. 5 tests unitarios + 1 E2E sobre el flujo completo de `finalize`.
- [x] T8.4 — Budget profile wiring SDDwork → context_enricher (2026-05-17) — Nuevo módulo `cortex/context_enricher/budget_resolver.py` (función pura). `cortex_context` MCP tool acepta `task_type` opcional y deriva `top_k`. Skill SDDwork + renderer agregan instrucción de pasar `task_type`. 11 tests cubren los 7 profiles + fallbacks + inmutabilidad.
- [x] T8.5 — Renderer condicional en `session.md.j2` (2026-05-17) — Template extendido con bloques `{% if task_type == "..." %}`. `SessionData.task_type` + `NoteService.create(task_type=...)` propagan el valor. `DocumenterPersister` lo extrae de `spec.raw_frontmatter`. 7 tests cubren question-only, docs-only, security, deep-code, fast-code, unspecified y unknown.
- [x] T8.6 — Tests + docs (2026-05-17) — `docs/architecture/session-primitive.md` §9 (Quality gates) + §10 (What's next). `docs/architecture/pluggable-middle-overview.md` §9 actualizado. CHANGELOG con bloque `[Unreleased] — Phase 08`. `docs/pluggable-middle/README.md` marca Fase 08 ✅. `MIGRATION-FROM-TRIPARTITO.md` §6 con nuevas MCP tools + symbols.
- [x] Completion Verification Commands pasan (2026-05-17) — Suite completa: **1779 passed, 15 skipped, 0 failed** (era 1743; +36 tests netos). mypy strict + ruff clean en módulos nuevos. Hash test del IDE adapter verde. MCP tool registrada (3 menciones en `CortexMCPServer` source).
- [x] Tabla `../README.md` actualizada ✅ (2026-05-17)
- [ ] Commit final (pendiente — esperando autorización del usuario)

---

## 9. Notas para el agente ejecutor

- **T8.1 es investigación.** Empezá leyendo el código existente (`NoteService.create`, `DocumenterPersister.finalize`). Si el rollback existe, T8.1 cierra con un commit de "audit" solo. Si no existe, restaurar agrega ~50 LOC y 3 tests. **Sin asumir** — verificar primero.
- **No reintroduzcas archivos en `cortex/autopilot/`.** La cleanness arquitectural de Fase 03 es valiosa. Toda lógica restaurada vive en el nuevo owner.
- **El skill prompt es contrato con LLMs.** Cualquier cambio al `.cortex/skills/cortex-SDDwork.md` requiere actualizar el renderer en `cortex/setup/cortex_workspace.py` Y correr `pytest tests/unit/ide/test_adapters_phase4.py` para confirmar hash match.
- **Self-review NO bloquea.** Si por algún motivo querés bloquear: parar y discutir. La filosofía es "señalar, no bloquear" — bloquear genera loops infinitos en el flujo agentic.
- **Budget profiles son data, no lógica compleja.** Si te tienta agregar reglas de fallback elaboradas: no. La función pura `resolve_budget_profile` es 20 líneas y se mantiene así.
- **Coordinación con Fase 09:** si Fase 09 ya está en ejecución cuando vas a hacer cambios al SDDwork prompt, leé primero `09-SDD-REFINEMENT.md` para entender qué otros bloques agrega y mergear sin pisarse.
