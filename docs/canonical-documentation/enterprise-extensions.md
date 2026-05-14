# Enterprise Extensions - Como Enterprise Consume Cada Capa

**Documento:** especificacion de las extensiones enterprise aplicadas a las 6 capas
**Audiencia:** implementadores
**Estado:** especificacion normativa

---

## 1. Principio guia

Enterprise no es un fork ni un modulo paralelo. Es un **modo de operacion ortogonal** que extiende cada capa sin duplicar codigo. La misma funcion `write_adr_note` opera en local y enterprise; cambia el routing y el frontmatter segun `vault_scope`.

Esta filosofia evita los problemas observados en otros sistemas donde "enterprise edition" se vuelve un fork divergente.

---

## 2. Capa 1: DocType - Sin cambios

`DocType` enum es el mismo en local y enterprise. Lista cerrada de 12 tipos.

Razon: no hay "tipos enterprise" inherentes. Una decision es una decision, un runbook es un runbook. Lo que cambia es la metadata de gobierno, no la naturaleza del documento.

---

## 3. Capa 2: Frontmatter - `EnterpriseFrontmatter`

### 3.1 Extension del schema

`CommonFrontmatter` es la base. `EnterpriseFrontmatter` agrega 5 campos:

```python
class EnterpriseFrontmatter(CommonFrontmatter):
    owner: str                    # email obligatorio
    team: str                      # slug obligatorio
    classification: str = "internal"   # public | internal | confidential
    retention_days: int = 0        # 0 = sin limite
    audit_trail: list[AuditEvent] = Field(default_factory=list)
```

### 3.2 Validador escala segun `vault_scope`

```python
def validate_frontmatter(yaml_str: str) -> CommonFrontmatter:
    raw = yaml.safe_load(yaml_str)
    if raw.get("vault_scope") == "enterprise":
        return EnterpriseFrontmatterFactory.validate(raw)
    return CommonFrontmatterFactory.validate(raw)
```

### 3.3 Politicas por preset

| Preset | Campos enterprise requeridos |
|---|---|
| `single-user` | ninguno (todo es local) |
| `small-company` | `owner` (no team, sin classification, sin retention) |
| `multi-project-team` | `owner, team` (sin classification, sin retention) |
| `regulated-organization` | `owner, team, classification, retention_days, audit_trail` |

Detectado por `org.yaml` y aplicado por el validador.

### 3.4 Campos sensibles

`audit_trail` es append-only. Nunca se borra una entrada; nuevas entradas se agregan.

`classification: confidential` bloquea promotion a vault publico (si existe distincion en el futuro).

---

## 4. Capa 3: Routing - `enterprise_subfolder`

### 4.1 Namespacing por proyecto

Cada `RouteSpec` tiene un `enterprise_subfolder` con placeholder `{project_id}`:

```python
DocType.ADR: RouteSpec(
    subfolder="decisions",                            # local
    enterprise_subfolder="decisions/{project_id}",     # enterprise
    ...
)
```

Local:
```
vault/decisions/ADR-007-foo.md
```

Enterprise:
```
vault-enterprise/decisions/mi-proyecto/ADR-007-foo.md
vault-enterprise/decisions/otro-proyecto/ADR-007-foo.md  # NO COLISIONA
```

### 4.2 Resolucion de path

```python
def resolve_target_path(
    spec: RouteSpec,
    context: dict,
    vault_root: Path,
    vault_scope: str = "local",
    project_id: str | None = None,
) -> Path:
    if vault_scope == "enterprise":
        if not spec.enterprise_subfolder:
            raise RoutingError(f"{spec.doc_type} not promotable")
        if "{project_id}" in spec.enterprise_subfolder and not project_id:
            raise RoutingError("project_id required for enterprise scope")
        subfolder = spec.enterprise_subfolder.format(project_id=project_id or "")
    else:
        subfolder = spec.subfolder

    filename = render_filename(spec, context)
    return vault_root / subfolder / filename
```

### 4.3 Casos especiales

- **`GLOSSARY` no se namespace.** Su `enterprise_subfolder = "glossary"` (sin placeholder). Razon: terminos del ubiquitous language son globales en la organizacion.
- **`HU` no es promotable.** Su `enterprise_subfolder = None`. Ratio: work items son operativos, no conocimiento.

---

## 5. Capa 4: Writers - Diferenciacion por `vault_scope`

### 5.1 Mismo writer, dos modos

```python
def write_adr_note(
    data: ADRData,
    *,
    vault: VaultReader,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
) -> Path:
    # 1. Validar
    if vault_scope == "enterprise":
        if not data.owner or not data.team:
            raise SchemaValidationError("owner and team required for enterprise")

    # 2. Resolver routing
    route = resolve_route(DocType.ADR)

    # 3. Renderizar
    body = render_template(route.template_path, data.__dict__)

    # 4. Fingerprint
    fingerprint = sha256(body)

    # 5. Construir frontmatter
    if vault_scope == "enterprise":
        frontmatter = build_enterprise_frontmatter(data, fingerprint, project_id)
    else:
        frontmatter = build_common_frontmatter(data, fingerprint)

    # 6. Path
    path = resolve_target_path(route, ctx, vault.path, vault_scope, project_id)

    # 7. Persist
    path.write_text(frontmatter_yaml + body)

    # 8. Index
    vault.index_file(rel_path)

    # 9. Audit trail si enterprise
    if vault_scope == "enterprise":
        append_audit_event(path, actor or "unknown", "created", reason=None)

    return path
```

### 5.2 Audit trail al modificar

```python
def update_adr_note(
    path: Path,
    new_data: ADRData,
    *,
    actor: str,
    reason: str | None = None,
) -> Path:
    """Update existing ADR. Appends audit event."""
    # Read existing frontmatter
    existing = parse_frontmatter(path)
    if existing.vault_scope == "enterprise":
        append_audit_event(existing, actor, "updated", reason)
    # ... resto del update
```

### 5.3 Helper: `append_audit_event`

```python
def append_audit_event(
    path: Path,
    actor: str,
    action: str,
    reason: str | None = None,
) -> None:
    """Append a new audit_trail entry. Never overwrites existing entries."""
    fm = parse_frontmatter(path)
    if not isinstance(fm, EnterpriseFrontmatter):
        raise ValueError("Audit trail only for enterprise notes")
    new_event = AuditEvent(
        actor=actor,
        action=action,
        timestamp=datetime.now(UTC),
        reason=reason,
    )
    fm.audit_trail.append(new_event)
    write_frontmatter(path, fm)
```

---

## 6. Capa 5: Vectorizacion - Sync por `fingerprint`

### 6.1 Cache compartido

Vault local y enterprise pueden compartir el cache de vectores (`VectorCache`) si viven en el mismo host:

```python
# config.yaml
vectorization:
  cache:
    path: ~/.cortex-global-vectors/    # compartido entre todos los vaults
```

### 6.2 Sync via promotion

Al promover de local a enterprise:

```python
def promote_note(local_path: str, project_id: str, actor: str) -> Path:
    local_doc = local_vault.get(local_path)
    fp = local_doc.frontmatter.fingerprint

    # Determinar destino enterprise
    enterprise_path = resolve_target_path(
        resolve_route(local_doc.doc_type),
        ctx,
        enterprise_vault.path,
        vault_scope="enterprise",
        project_id=project_id,
    )

    # Copiar contenido con frontmatter enterprise
    enterprise_fm = EnterpriseFrontmatter(
        **local_doc.frontmatter.model_dump(),
        owner=actor,
        team=infer_team(actor, project_id),
        classification=infer_classification(local_doc),
        retention_days=default_retention(local_doc.doc_type),
        audit_trail=[AuditEvent(actor=actor, action="promoted", timestamp=now())],
    )
    write_with_frontmatter(enterprise_path, enterprise_fm, local_doc.body)

    # Reuse vector si esta en cache
    cached_vec = vector_cache.get(fp)
    if cached_vec is not None:
        enterprise_vault._embeddings[enterprise_path] = cached_vec
    else:
        enterprise_vault.index_file(enterprise_path)

    return enterprise_path
```

### 6.3 Beneficio

Promotion bulk de 100 ADRs no re-embedea ninguno. Ahorra ~5s y garantiza consistencia.

---

## 7. Capa 6: Retrieval con scope y permisos

### 7.1 Filtros enterprise

`EnrichmentFilters` ya tiene:

```python
vault_scope: str = "all"       # "local" | "enterprise" | "all"
project_ids: list[str] | None  # filtrar por proyecto
```

### 7.2 Filtros adicionales por classification

```python
class EnrichmentFilters(BaseModel):
    # ... existentes
    classifications_allowed: list[str] | None = None
    teams_allowed: list[str] | None = None
```

Aplicacion:
- Si user es de `team-A`, filtros default `teams_allowed=[team-A]`.
- Si user es admin, sin restriccion.
- `classification=confidential` solo visible para teams autorizados (config-driven).

### 7.3 Telemetria diferenciada

```yaml
# config.yaml
retrieval:
  telemetry:
    enabled_local: true
    enabled_enterprise: false     # privacidad
```

Razon: en enterprise multi-tenant no se quiere telemetria cross-org sin consentimiento.

Si esta habilitada en enterprise, scopear por proyecto:
- Eventos de `project-a` solo visibles para team-a.
- Aggregate global solo para admins.

---

## 8. Promotion DocType-aware

### 8.1 Modos de promotion por tipo

Hoy la promotion es uniforme. Diferenciar segun `RouteSpec.promotion_mode`:

| DocType | promotion_mode | Comportamiento |
|---|---|---|
| ADR | `as-is` | Copia integral; mismos campos |
| DECISION | `as-is` | Idem |
| INCIDENT | `as-is` (si severity >= medium) | Idem; severity < medium no se promueve |
| POSTMORTEM | `as-is` | Siempre se promueve |
| RUNBOOK | `review-required` | Requiere review humano antes de publicar |
| ARCHITECTURE | `as-is` | Copia integral |
| CHANGELOG | `as-is` | Copia integral |
| SPEC | `as-is` | Copia integral |
| SESSION | `summarize` | NO se promueve raw; se genera resumen |
| HANDOFF | NO promotable | (`promotable=False`) |
| HU | NO promotable | (`promotable=False`) |
| GLOSSARY | `as-is` | Sin namespacing |

### 8.2 Modo `summarize`

Sessions tienen mucho ruido (debugging, false starts, etc). Promotion como resumen:

```python
def summarize_session_for_enterprise(session_doc: Doc) -> str:
    """Generate enterprise-promotable summary of a session note."""
    # Extrae solo:
    # - Key decisions (con razon)
    # - Verified state
    # - Files touched (de alto valor)
    # NO incluye: changes_made detallado, blockers, suggested_skills
```

### 8.3 Modo `review-required`

Runbooks promovidos requieren `audit_trail` con accion `reviewed`:

```python
def promote_runbook(local_path: str, actor: str, ...) -> None:
    enterprise_path = ...
    enterprise_fm = ...
    enterprise_fm.status = "draft"     # no published hasta review
    enterprise_fm.audit_trail.append(
        AuditEvent(actor=actor, action="promoted", timestamp=now())
    )
    write_with_frontmatter(enterprise_path, enterprise_fm, body)
    # status="published" se setea en review explicito
```

### 8.4 Comando `cortex review-knowledge`

```bash
$ cortex review-knowledge --pending
| Doc Type | Path                                | Promoted By | Days Pending |
|----------|-------------------------------------|-------------|--------------|
| RUNBOOK  | runbooks/RB-deploy-vault.md         | ezequiel    | 3            |
| RUNBOOK  | runbooks/RB-incident-response.md    | ezequiel    | 7            |

$ cortex review-knowledge --approve runbooks/RB-deploy-vault.md \
    --reason "Approved by team lead"
```

---

## 9. Audit trail completo end-to-end

### 9.1 Eventos cubiertos

| Accion | Cuando | Actor |
|---|---|---|
| `created` | Nota se crea | autor (humano o agente) |
| `updated` | Nota se modifica | autor del cambio |
| `promoted` | Promotion local -> enterprise | promotor |
| `reviewed` | Aprobacion post-promotion | reviewer |
| `rejected` | Promotion rechazada | reviewer |
| `classified` | Cambio de `classification` | admin |
| `retention-updated` | Cambio de `retention_days` | admin |
| `deleted` | Soft-delete (mover a `_archived/`) | admin |

### 9.2 Estructura del evento

```yaml
- actor: ezequiel@cortex.ai
  action: promoted
  timestamp: 2026-05-14T10:23:45Z
  reason: "Approved by team-lead for canonical adoption"
```

### 9.3 Inmutabilidad

- Append-only en frontmatter.
- Tambien duplicado en `.cortex/vault-enterprise/promotion/records.jsonl` para queries rapidas.
- Modificar entradas pasadas requiere `cortex audit rewrite` (admin only) y deja meta-evento.

### 9.4 GPG signing (opcional, futuro)

```yaml
audit_trail:
  - actor: ezequiel@cortex.ai
    action: promoted
    timestamp: 2026-05-14T10:23:45Z
    reason: "Approved"
    signature: -----BEGIN PGP SIGNATURE-----
              iQEcBAABAgAGBQJfTGZWAAoJEC...
              -----END PGP SIGNATURE-----
```

No en MVP; reservar el campo para extension futura.

---

## 10. Multi-tenant: scoping y permisos

### 10.1 `org.yaml` extension

```yaml
# org.yaml
org:
  id: acme-corp
  teams:
    - id: api-team
      members:
        - alice@acme.com
        - bob@acme.com
      can_promote: true
      can_review: true
    - id: ml-team
      members:
        - carol@acme.com
      can_promote: true
      can_review: false   # no puede aprobar promociones
  classifications:
    - public
    - internal
    - confidential
  policies:
    confidential_visible_to: [api-team, admin]
```

### 10.2 Aplicacion al retrieval

Cuando un usuario hace `cortex search`:
1. Detectar identidad del usuario (env var, config).
2. Mapear a teams.
3. Inyectar filtros: `classifications_allowed = [public, internal]` + `teams_allowed = [user_teams]`.

### 10.3 Promotion gated

```python
def promote(path: str, actor: str, ...) -> None:
    user_team = resolve_team(actor)
    if not org.team_can_promote(user_team):
        raise PermissionError(f"{user_team} cannot promote")
    # ...
```

---

## 11. Retention policy

### 11.1 Politicas por tipo (defaults en `org.yaml`)

```yaml
retention_defaults:
  session: 365         # 1 ano
  handoff: 30          # 1 mes
  spec: 1095           # 3 anos
  adr: 2555            # 7 anos (decisiones permanentes)
  decision: 365
  incident: 1825       # 5 anos (compliance)
  postmortem: 2555     # 7 anos
  runbook: 730         # 2 anos (con re-verificacion)
  architecture: 2555
  changelog: 0         # sin limite
  hu: 90
  glossary: 0          # sin limite
```

### 11.2 Maintenance job

```bash
$ cortex docs maintenance
> Scanning vault-enterprise/...
> 12 notas con retention_days expirado:
>   - sessions/2024-04-15_old-session.md (expirado 30d hace)
>   ...
> Archive (mover a _archived/)? [y/N]
```

No borra; mueve a `_archived/`. Retention legal preservada para auditoria.

---

## 12. Diferencias clave: resumen

| Aspecto | Local | Enterprise |
|---|---|---|
| Frontmatter | `CommonFrontmatter` | `EnterpriseFrontmatter` (owner/team/classification/retention/audit) |
| Carpetas | `decisions/`, `runbooks/`, ... | `decisions/{project_id}/`, ... |
| Promotion | N/A | DocType-aware (as-is/summarize/review-required) |
| Audit trail | No | Si, embebido + jsonl |
| Multi-tenant | No | Si (teams, classifications) |
| Retention | No | Si (policies por tipo) |
| Telemetria | Habilitada default | Deshabilitada default (privacidad) |
| Vector cache | Local del proyecto | Compartido global (opcional) |
| GPG sign | No | Reservado (futuro) |

---

## 13. Cambios en `cortex/enterprise/`

### 13.1 Modulos a tocar

```text
cortex/enterprise/
    models.py                    # extension EnterpriseOrgConfig con teams/classifications
    knowledge_promotion.py       # promotion DocType-aware
    promotion_models.py          # AuditEvent + retention metadata
    reporting.py                  # extender memory-report con scope by team
    governance.py                # NUEVO: classifications, permissions
```

### 13.2 Tests

```text
tests/unit/enterprise/
    test_enterprise_frontmatter.py    # NUEVO
    test_promotion_doctype_aware.py    # NUEVO
    test_audit_trail.py                # NUEVO
    test_governance.py                  # NUEVO
    test_retention.py                   # NUEVO
```

---

## 14. Backwards compatibility

### 14.1 Vault local pre-existente

No requiere migracion enterprise. Sigue funcionando con `CommonFrontmatter`.

### 14.2 Promotions previas

`PromotionRecord` ya existente (`records.jsonl`) sigue funcionando. Nuevos campos enterprise se backfilllean al re-leer.

### 14.3 Preset `single-user`

No cambia. No requiere campos enterprise.

---

## 15. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Owner/team obligatorios bloquean creacion para nuevos usuarios | Setup interactivo guia; default a env vars |
| Multi-tenant complica retrieval | Filtros default por team; admin override |
| Audit trail crece sin limite en frontmatter | Rotacion: solo ultimos N eventos en frontmatter; resto en jsonl |
| Retention policy borra docs en uso | Move a _archived/, no delete; aviso 30d antes |
| Promotion summarize pierde info | Mantener link al original en metadata |
| Multi-team conflicts en promotion | First-wins con audit_trail visible |
| GPG signing complica MVP | Fuera de scope; campo reservado |

---

## 16. Roadmap de adopcion enterprise

| Fase | Que se habilita |
|---|---|
| Fase 10 (este plan) | Frontmatter enterprise + audit trail + namespacing + promotion DocType-aware |
| Post-MVP | Multi-tenant strict permissions |
| Post-MVP | Retention enforcement automatico |
| Post-MVP | GPG signing |
| Roadmap | Vault Git-like nativo (Fase 2-4 del Proposal Enterprise) |

---

## 17. Decisiones clave

1. **Enterprise es extension, no fork:** mismo codigo, ramita condicional por `vault_scope`.
2. **Frontmatter enterprise extiende, no reemplaza:** consumidores que solo conocen `CommonFrontmatter` siguen funcionando.
3. **Promotion DocType-aware:** sessions se resumen; runbooks requieren review; ADRs van as-is.
4. **Audit trail embebido + jsonl duplicado:** redundancia controlada para query rapida.
5. **Telemetria default OFF en enterprise:** privacidad first.
6. **Vector cache compartido:** ahorro masivo en promotions bulk.
7. **Retention policies con defaults por tipo:** se overridean per-nota.
