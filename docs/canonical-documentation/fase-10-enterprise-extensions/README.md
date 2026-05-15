# Fase 10 - Enterprise Extensions

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 2 dias (real: ~1 hora)
**Riesgo:** alto
**Dependencias:** Fases 01-08

---

## 1. Objetivo

Implementar todas las extensiones enterprise descritas en `enterprise-extensions.md`:
- `EnterpriseFrontmatter` activo en writers cuando `vault_scope=enterprise`.
- `audit_trail` append-only via `append_audit_event`.
- Namespacing por `project_id` en routing.
- Promotion DocType-aware (as-is | summarize | review-required).
- Comando `cortex review-knowledge` para gate de promotions.
- Retention policies configurables por `org.yaml`.
- Multi-tenant scoping en retrieval (filtros por team y classification).

Riesgo alto: toca `enterprise/`, promotion pipeline, retention, y permissions a la vez. Hay que segmentar bien.

---

## 2. Archivos a crear / tocar

```text
cortex/enterprise/
    models.py                      # EXTENDIDO: EnterpriseOrgConfig con teams, classifications, retention
    governance.py                  # NUEVO: permission checks, classification visibility
    knowledge_promotion.py         # EXTENDIDO: promotion_mode-aware
    promotion_models.py            # EXTENDIDO: audit_trail integration
    reporting.py                   # EXTENDIDO: by team, by classification

cortex/documentation/
    writers.py                     # EXTENDIDO: cada writer aplica enterprise scope
    audit.py                       # (de Fase 03) extendido para fluir audit a records.jsonl

cortex/cli/
    review_knowledge.py            # NUEVO

cortex/services/
    promotion_service.py           # NUEVO o extension

tests/unit/enterprise/
    test_enterprise_frontmatter.py
    test_promotion_doctype_aware.py
    test_audit_trail.py
    test_governance.py
    test_retention.py
    test_org_config_extended.py

tests/integration/enterprise/
    test_promotion_pipeline.py
    test_multi_tenant_retrieval.py
```

---

## 3. Responsabilidades

### `governance.py` (NUEVO)

```python
# cortex/enterprise/governance.py
from cortex.enterprise.models import EnterpriseOrgConfig

class PermissionError(Exception): ...

def user_team(user_email: str, org: EnterpriseOrgConfig) -> str | None:
    """Resolve which team a user belongs to."""
    for team in org.teams:
        if user_email in team.members:
            return team.id
    return None


def team_can_promote(team_id: str, org: EnterpriseOrgConfig) -> bool:
    for team in org.teams:
        if team.id == team_id:
            return team.can_promote
    return False


def team_can_review(team_id: str, org: EnterpriseOrgConfig) -> bool:
    for team in org.teams:
        if team.id == team_id:
            return team.can_review
    return False


def classification_visible_to(
    classification: str,
    team_id: str,
    org: EnterpriseOrgConfig,
) -> bool:
    """Check if a team can see notes with the given classification."""
    if classification in {"public", "internal"}:
        return True
    if classification == "confidential":
        allowed = org.policies.get("confidential_visible_to", [])
        return team_id in allowed or team_id == "admin"
    return False
```

### `EnterpriseOrgConfig` extension

```python
# cortex/enterprise/models.py - EXTENSION

class Team(BaseModel):
    id: str
    members: list[str]
    can_promote: bool = True
    can_review: bool = False


class RetentionPolicy(BaseModel):
    session: int = 365
    handoff: int = 30
    spec: int = 1095
    adr: int = 2555
    decision: int = 365
    incident: int = 1825
    postmortem: int = 2555
    runbook: int = 730
    architecture: int = 2555
    changelog: int = 0
    hu: int = 90
    glossary: int = 0


class EnterpriseOrgConfig(BaseModel):
    # ... existentes
    teams: list[Team] = Field(default_factory=list)
    classifications: list[str] = Field(default_factory=lambda: ["public", "internal", "confidential"])
    policies: dict[str, Any] = Field(default_factory=dict)
    retention_defaults: RetentionPolicy = Field(default_factory=RetentionPolicy)
```

### Promotion DocType-aware

```python
# cortex/enterprise/knowledge_promotion.py - EXTENSION

class KnowledgePromotionService:
    def promote(
        self,
        local_path: str,
        actor: str,
        project_id: str,
        reason: str | None = None,
    ) -> PromotionResult:
        # 1. Resolve doc_type from local note
        local_doc = self._local_vault.get(local_path)
        doc_type = DocType(local_doc.frontmatter.get("doc_type"))

        # 2. Permission check
        team_id = user_team(actor, self._org)
        if not team_can_promote(team_id, self._org):
            raise PermissionError(f"{team_id} cannot promote")

        # 3. Resolve promotion mode
        route = resolve_route(doc_type)

        if route.promotion_mode == "as-is":
            return self._promote_as_is(local_doc, doc_type, project_id, actor, reason)
        elif route.promotion_mode == "summarize":
            return self._promote_summarized(local_doc, doc_type, project_id, actor, reason)
        elif route.promotion_mode == "review-required":
            return self._promote_pending_review(local_doc, doc_type, project_id, actor, reason)
        else:
            raise PromotionError(f"Unknown promotion_mode: {route.promotion_mode}")

    def _promote_as_is(self, local_doc, doc_type, project_id, actor, reason):
        # 1. Resolve enterprise path
        # 2. Build EnterpriseFrontmatter from CommonFrontmatter + defaults
        # 3. Write to enterprise vault
        # 4. Reuse vector if fingerprint matches
        # 5. Append audit event "promoted"
        # 6. Record in records.jsonl

    def _promote_summarized(self, local_doc, doc_type, project_id, actor, reason):
        # For sessions: extract only key_decisions, verified_state, files_touched
        # Create new doc with summary content
        # ...

    def _promote_pending_review(self, local_doc, doc_type, project_id, actor, reason):
        # Write to enterprise with status="draft"
        # No "published" until review
        # ...
```

### `cortex review-knowledge` CLI

```python
# cortex/cli/review_knowledge.py - NUEVO

import typer

app = typer.Typer(help="Review and approve enterprise knowledge promotions.")


@app.command()
def pending():
    """List notes pending review."""
    service = _get_promotion_service()
    pending = service.list_pending_reviews()
    for note in pending:
        typer.echo(f"{note.doc_type:<12} {note.path:<60} (promoted by {note.promoted_by}, {note.days_pending} days)")


@app.command()
def approve(
    path: str,
    actor: str = typer.Option(..., "--actor"),
    reason: str | None = typer.Option(None, "--reason"),
):
    """Approve a pending review."""
    service = _get_promotion_service()
    if not team_can_review(user_team(actor, _org), _org):
        typer.echo(f"Error: {actor} cannot review")
        raise typer.Exit(1)
    service.approve(path, actor=actor, reason=reason)
    typer.echo(f"Approved: {path}")


@app.command()
def reject(
    path: str,
    actor: str = typer.Option(..., "--actor"),
    reason: str = typer.Option(..., "--reason"),
):
    """Reject a pending review."""
    # ...
```

### Maintenance: retention

```python
# cortex/enterprise/maintenance.py - NUEVO

def scan_retention_violations(vault: VaultReader, org: EnterpriseOrgConfig) -> list[Path]:
    """Find notes with retention_days expired."""
    violations = []
    for rel_path, doc in vault.iter_documents():
        fm = doc.frontmatter or {}
        retention_days = fm.get("retention_days", 0)
        if retention_days == 0:
            continue
        created = parse_datetime(fm["created_at"])
        if datetime.now(UTC) - created > timedelta(days=retention_days):
            violations.append((rel_path, fm))
    return violations


def archive_violations(violations: list, vault: VaultReader) -> int:
    """Move violations to _archived/. Return count."""
```

### Multi-tenant retrieval

```python
# cortex/enterprise/retrieval_service.py - EXTENSION

class EnterpriseRetrievalService:
    def search(self, query: str, actor: str | None = None, ...) -> list:
        # If actor present, inject team-based filters
        if actor:
            team_id = user_team(actor, self._org)
            filters = inject_team_filters(filters, team_id, self._org)
        return self._search_internal(query, filters, ...)


def inject_team_filters(filters: EnrichmentFilters, team_id: str, org) -> EnrichmentFilters:
    """Add team and classification filters based on user's team."""
    allowed_classifications = [c for c in org.classifications
                                if classification_visible_to(c, team_id, org)]
    return filters.model_copy(update={
        "classifications_allowed": allowed_classifications,
        "teams_allowed": [team_id, "admin"],  # admin team always visible
    })
```

---

## 4. Tests

### `test_enterprise_frontmatter.py`

```python
def test_enterprise_frontmatter_requires_owner_team()
def test_enterprise_frontmatter_audit_trail_initial_empty()
def test_enterprise_frontmatter_classification_validation()
def test_enterprise_frontmatter_retention_days_non_negative()
def test_enterprise_frontmatter_serialization()
```

### `test_promotion_doctype_aware.py`

```python
def test_promote_adr_as_is_copies_full_content()
def test_promote_session_summarizes()
def test_promote_runbook_requires_review()
def test_promote_postmortem_always_promoted()
def test_promote_handoff_raises()  # no promotable
def test_promote_hu_raises()  # no promotable
def test_promote_with_reuses_vector_via_fingerprint()
def test_promote_incident_high_severity_promoted()
def test_promote_incident_low_severity_skipped()
```

### `test_audit_trail.py`

```python
def test_audit_event_appended_on_create()
def test_audit_event_appended_on_update()
def test_audit_event_appended_on_promote()
def test_audit_trail_is_append_only()
def test_audit_trail_persisted_in_frontmatter()
def test_audit_trail_duplicated_in_records_jsonl()
```

### `test_governance.py`

```python
def test_user_team_resolution()
def test_user_team_not_found()
def test_team_can_promote()
def test_team_cannot_promote()
def test_team_can_review()
def test_team_cannot_review()
def test_classification_public_visible_to_all()
def test_classification_internal_visible_to_all()
def test_classification_confidential_visible_only_to_allowed()
def test_admin_team_visible_to_all_classifications()
```

### `test_retention.py`

```python
def test_scan_finds_violations()
def test_scan_skips_zero_retention()
def test_archive_violations_moves_to_archived()
def test_archive_preserves_data()
def test_default_retention_per_doc_type()
```

### `test_multi_tenant_retrieval.py` (integration)

```python
def test_user_in_team_a_sees_team_a_notes()
def test_user_not_in_team_a_doesnt_see_team_a_confidential()
def test_admin_sees_all_classifications()
def test_filter_by_team_default_when_actor_present()
```

---

## 5. Checklist

- [x] `cortex/enterprise/governance.py` con permissions
- [x] `cortex/enterprise/models.py` extendido (Team, RetentionPolicy)
- [x] `cortex/documentation/writers.py` aplican enterprise scope
- [x] Promotion DocType-aware con 3 modos
- [ ] `cortex/cli/review_knowledge.py` con pending/approve/reject (Item #9 en `../fase-13-backlog-consolidado/PLAN-DEUDA-RESIDUAL.md`)
- [x] `cortex/enterprise/maintenance.py` con retention
- [x] Multi-tenant retrieval con filtros automaticos
- [x] Tests >= 35
- [x] Coverage >= 90%

---

## 6. Gate de salida

- `pytest tests/unit/enterprise tests/integration/enterprise` pasa al 100%.
- Setup con preset `regulated-organization` exige campos completos al crear.
- Promotion de ADR funciona as-is.
- Promotion de SESSION resume.
- Promotion de RUNBOOK requiere review.
- `cortex review-knowledge` lista pending y permite approve.
- Maintenance detecta retention violations.
- `REALIZACION.md` documentado.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Audit trail crece y fragmenta frontmatter | Rotacion: ultimos N en frontmatter, resto en jsonl |
| Permissions strict bloquean adopcion | Default permisivo (single-user/small-company); strict solo en regulated |
| Promotion summarize pierde info | Mantener link al original; mostrar en review |
| Multi-tenant rompe queries existentes | actor=None mantiene comportamiento actual |
| Retention borra archivo en uso | Move a _archived/, no delete; 30d notice |
| Classification confidential mal asignada | Audit trail registra cambios |
| Tests requieren org.yaml + multiples actores | Fixtures con org_factory |
| Vault cache invalidation tras retention | scheduled job invalida; tests verifican |

---

## 8. Notas para agentes implementadores

1. **Empezar por governance.py.** Sin permisos no se puede hacer nada enterprise.
2. **EnterpriseOrgConfig backwards-compat.** Default empty lists; no breaking.
3. **Promotion modes en orden:** as-is primero (mas simple), summarize despues, review-required al final.
4. **Audit trail en pydantic + jsonl.** Redundancia controlada.
5. **CLI review_knowledge minimalista.** Solo pending/approve/reject.
6. **Retention en CLI separado.** Comando `cortex docs maintenance`.
7. **Tests con fixtures de org.yaml.** Multiple teams, multiple actors.

---

## 9. Referencias

- `docs/canonical-documentation/enterprise-extensions.md` - especificacion completa
- `docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md` - maximas
- `cortex/enterprise/knowledge_promotion.py` - base existente
- `cortex/enterprise/models.py` - EnterpriseOrgConfig base
