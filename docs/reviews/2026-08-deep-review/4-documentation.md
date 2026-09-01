# Revisión: `cortex/documentation` — Sistema de documentación canónica

**Scope:** `cortex/documentation/**` (audit, backup, common, data, doc_type, errors, inventory, migration, routing, schemas/*, templates/*, templates_engine.py, validation.py, writers.py). ~3.600 líneas Python + 14 plantillas Jinja2.

---

## 1. Propósito y arquitectura interna

Este paquete es el **subsistema de documentación canónica** de Cortex: define los 13 tipos de documento (DocType), sus schemas de frontmatter (Pydantic), la tabla de ruteo (dónde vive cada nota y cómo se nombra), las plantillas del cuerpo (Jinja2), los escritores canónicos, el validador público, el inventario/migración de vaults legacy y backups.

### Capas (de abajo hacia arriba)

| Módulo | Responsabilidad |
|---|---|
| `errors.py` | Jerarquía de excepciones (`DocumentationError` base + 5 subclases). |
| `common.py` | Helpers puros: `slugify`, `compute_fingerprint` (SHA-256), `yaml_dump_safe`/`yaml_load_safe`, `split_frontmatter_and_body`, `parse_frontmatter_lenient`. |
| `doc_type.py` | `DocType(str, Enum)` con 13 valores (12 "canónicos" + `DESIGN`), `VALID_STATUSES` por tipo, `_PROMOTABLE`, inferencia `doc_type_from_path` / `infer_doc_type_from_path` (fuente única de verdad, Fase 13). |
| `inventory.py` | Escaneo read-only del vault (`VaultInventory`, `classify_path`, `inventory_vault`) para migración y `cortex docs status`. |
| `data.py` | Dataclasses de *entrada* para writers (`SessionData`, `SpecData`, `ADRData`, …, todos heredan `CommonWriteData`). Sin validación Pydantic aquí. |
| `schemas/` | Modelos Pydantic de frontmatter: `CommonFrontmatter` base + par Local/Enterprise por cada DocType; mapas `SCHEMA_BY_TYPE` y `SCHEMA_BY_TYPE_ENTERPRISE`. |
| `validation.py` | Validador público: YAML → schema correcto según `doc_type` + `vault_scope` (`validate_frontmatter`, `validate_path_frontmatter`). |
| `routing.py` | `DOC_TYPE_ROUTING: dict[DocType, RouteSpec]` — fuente única para subfolder, filename_template, template, writer, promotable/promotion_mode, boosts de retrieval, chunking, estilo webgraph, expiración. Funciones `resolve_route`, `render_filename`, `resolve_target_path`. |
| `templates_engine.py` | Environment Jinja2 único (`_env` global) + `render_template(name, data)`. Autoescape deshabilitado para `.md.j2`; `trim_blocks`/`lstrip_blocks`. |
| `audit.py` | `append_audit_event`: append-only funcional sobre `EnterpriseFrontmatter` (re-valida con `model_validate`). |
| `backup.py` | Snapshots tar.gz del vault (`create_backup`, `restore_backup`, `list_backups`) en `<vault>/../.cortex/backups/`. |
| `migration.py` | Backfill de vault legacy al schema v1: dry-run por defecto (`migrate_vault(apply=False)`), diff por nota (`NoteDiff`), backup antes de aplicar, idempotente vía `schema_version=1`, `validate_vault`, `format_report`. |
| `writers.py` | 15 funciones públicas `write_*` que comparten `_write_canonical`: template body → fingerprint → frontmatter validado → path resuelto → write atómico-ish → index. |
| `__init__.py` | Fachada pública + **binding mutante**: tras importar writers, reemplaza cada `RouteSpec` de `DOC_TYPE_ROUTING` vía `dataclasses.replace(..., writer=...)` para los 13 tipos. |

### Decisiones de diseño clave

1. **Tabla de ruteo como single source of truth** (`routing.py:74-344`): storage + naming + retrieval + webgraph + lifecycle en un solo lugar. Consumidores (chunker, style, promotion) leen la misma tabla.
2. **Dos mundos de datos**: dataclasses laxos para construir (entrada del agente) vs Pydantic frozen para persistir (salida validada). La validación ocurre recién en `_build_frontmatter` (`writers.py:327-352`).
3. **Idempotencia por fingerprint** (`writers.py:367-382`): si el archivo existe pero su frontmatter tiene el mismo fingerprint SHA-256 del body, la escritura es no-op exitosa. Diseñado explícitamente contra retries de MCP (incidente `2026-05-22_appfutbol-mcp-duplicate-loop` citado en `routing.py:82` y `writers.py:374-375`).
4. **Fallo blando del indexador** (`writers.py:391-397`): un error de `vault.index_file` nunca aborta la escritura.
5. **Migración segura**: dry-run default, backup tar.gz obligatorio antes de apply (`migration.py:204-205`), skip por `schema_version==1`, preservación de campos legacy bajo prefijo `legacy_<name>` (`migration.py:379-384`).
6. **Audit trail append-only e inmutable**: modelos frozen + reconstrucción funcional (`audit.py:39-44`).
7. **HANDOFF y DESIGN son local-only** (`enforce_local_scope=True`, `writers.py:620/758`); HU y HANDOFF no promovibles (`doc_type.py:86-99`).
8. Inferencia doc_type centralizada en `doc_type_from_path` (`doc_type.py:149-189`): primer segmento de carpeta conocido; `decisions/ADR-*` → ADR, resto → DECISION.

## 2. Flujo de datos / entradas y salidas

**Entradas:** dataclasses de `data.py` construidos por servicios/agentes; archivos `.md` legacy (inventory/migration); YAML frontmatter (validation).

**Salidas:** notas Markdown con frontmatter YAML en disco; `Path` del destino; reportes (`MigrationResult`, `VaultInventory`, dict de `validate_vault`).

**Quién llama a este subsistema** (grep repo):
- `services/note_service.py`, `services/spec_service.py` → `write_session_note_canonical` / `write_spec_note_canonical`.
- `documenter/persistence.py` → `write_adr_note`; `documenter/spec_loader.py` relee frontmatter SPEC.
- `mcp/server.py` (9 referencias) → expone writers como tools MCP, incluida `write_design_note_canonical`.
- `enterprise/promotion_doctype.py`, `enterprise/maintenance.py` → `resolve_route`, promoción local→enterprise.
- `semantic/vault_reader.py`, `semantic/chunker.py` → `classify_path`, `DocType`, config de chunking desde RouteSpec.
- `webgraph/style.py`, `webgraph/semantic_source.py` → colores/formas por DocType.
- `context_enricher/enricher.py`, `filters.py` → clasificación doc_type.
- `cli/docs_migrate.py`, `cli/docs_subcommand.py` → migration/backup/inventory.
- `workitems/service.py` → HU.

**Dependencia externa notable:** `data.py:18-19` y `schemas/spec.py:9` importan `cortex.session.models.VerificationHook` (acoplamiento inverso documentation→session, solo TYPE_CHECKING en data.py pero real en runtime en spec.py).

## 3. Bugs potenciales y riesgos (con evidencia)

1. **Race condition en numeración secuencial ADR/INC** — `writers.py:112-137`: `_next_number` escanea el folder sin lock; dos writers concurrentes pueden elegir el mismo número y luego chocar en `DuplicateDocumentError` (o peor, escribir con overwrite=True pisando). Riesgo real con MCP multi-cliente.
2. **`restore_backup` usa `extractall` sin filtrar members** — `backup.py:71-77`: vulnerable a path traversal (tar slip) si el tar.gz fue manipulado; además calcula `top` desde `members[0]` pero extrae TODO el archivo, así que si el orden cambia devuelve un path incorrecto. Python ≥3.12 acepta `filter="data"` — debería usarse.
3. **`create_backup` incluye `.cortex/backups` dentro del snapshot** — `backup.py:54-55` archivea el vault entero; los backups previos viven en `<parent>/.cortex/backups`, fuera del vault, así que OK por defecto, pero si alguien pasa `backups_dir` adentro del vault se produce crecimiento anidado. Menor.
4. **Mutación silenciosa de tabla global en import** — `__init__.py:73-109`: `DOC_TYPE_ROUTING` es un dict global mutable que se parchea al importar la fachada. Si un consumidor importa `cortex.documentation.routing` directamente, ve `writer=None` para todos los tipos. Cualquier código que confíe en `spec.writer` depende de que alguien haya importado el paquete padre primero. Frágil y difícil de testear.
5. **Fingerprint solo cubre el body, no el frontmatter** — `writers.py:428`: `compute_fingerprint(body)`. Dos llamadas con distinto `tags`/`status` pero mismo body son tratadas como no-op idempotente y **descartan silenciosamente** la actualización. El comentario dice "same SHA-256 fingerprint" del body, pero semánticamente un update legítimo se pierde sin aviso.
6. **`_default_status` elige alfabéticamente** — `writers.py:96-98`: `next(iter(sorted(...)))` da `"accepted"` para ADR y `"active"` para DECISION aunque el caller mande status vacío o inválido; para SESSION daría "auto-draft" (alfabético) en vez de "draft". `DesignDocData` lo esquiva con default propio (`data.py:106-110`) — reconocimiento implícito del problema. Coerción silenciosa: un typo de status no falla, se reemplaza.
7. **`validate_vault` cuenta mal `no_frontmatter`** — `migration.py:253`: `no_frontmatter = total - valid - invalid`, pero `invalid` incluye también notas CON frontmatter inválido y notas sin frontmatter (que lanzan `SchemaValidationError("No frontmatter")` en `validation.py:89`). El contador mezcla categorías; el valor es siempre 0 salvo errores raros.
8. **Duplicación total de schemas Local/Enterprise** — p.ej. `schemas/incident.py:27-52`: `IncidentFrontmatter` y `IncidentFrontmatterEnterprise` repiten campo por campo y validator por validator (igual en adr, hu, runbook, postmortem, changelog…). Un campo nuevo debe agregarse en 2 lugares × 13 tipos = alto riesgo de divergencia. Ya hay divergencia estructural: session.py define `_SessionFields` muerto (`schemas/session.py:31-40`, nunca usado — las clases duplican los campos inline en :43-58).
9. **Código muerto / casi muerto:**
   - `schemas/base.py:130-135`: `_get_classifications`/`_get_vault_scopes` — funciones privadas sin consumidores ni export en `__all__` ("Re-export raw constants" pero no se re-exportan).
   - `inventory.py:18-30`: `_SUBFOLDER_TO_DOC_TYPE` local ya no se usa para clasificar (`classify_path` delega a `doc_type.py` desde Fase 13, `inventory.py:76-80`); solo queda como duplicación que puede divergir (le falta `"designs"`).
   - `routing.py:104` y comentarios "Fase 03/04 migrates the legacy writer here": obsoletos, el binding ocurre en `__init__.py`.
10. **`_PLACEHOLDER_RE` no valida placeholders con formato** correctamente a medias — `routing.py:351`: captura `{number:03d}` bien (excluye `:`), pero el chequeo de missing usa nombres crudos; ok. En cambio, `render_filename` con contexto extra funciona porque `format(**ctx)` ignora extras… no: `str.format` ignora claves sobrantes, sí. Riesgo menor: placeholder tipográfico en template nuevo falla recién en runtime de escritura.
11. **`migration._type_specific_for` usa `datetime.now(UTC)` inconsistente** — `migration.py:482-484`: para `opened_at` de incidentes ignora el `now` inyectado y llama `datetime.now(UTC)` directo, rompiendo la determinismo de tests/clock injection prometida en `migrate_vault(now=...)` (`migration.py:158,174`).
12. **`_apply_diff` relee el body en vez de usar el ya leído** — `migration.py:361,389-395`: `_build_new_frontmatter` lee el archivo para fingerprint/links, y `_apply_diff` lo vuelve a leer. TOCTOU menor: si el archivo cambió entre dry-run y apply, el diff aplicado no coincide con lo reportado.
13. **`write_glossary_entry` y `write_design_note` mutan el input** — `writers.py:640` (`data.title = data.term`) y `writers.py:749` (`data.title = f"Design for {session_id}"`): efectos secundarios sobre la dataclass del caller; sorpresivo y no documentado.
14. **`slugify("")` → ""** manejado con fallback `"untitled"` solo en filename context (`writers.py:159`), pero `GlossaryEntryData.term` vacío llega a `slugify(data.term)` en `writers.py:196` después del guard de term — ok ahí, aunque `render_filename` recibiría `term_slug=""` si el guard cambiara. Frágil por orden de guards.
15. **Templates asumen campos que pueden faltar** — los writers pasan `asdict(data)` completo (`writers.py:426`), así que hoy está bien; pero cualquier llamada directa a `render_template` con dict parcial produce `UndefinedError` envuelto en `TemplateRenderError`. `session.md.j2` accede a ~20 variables condicionales; agregar un campo a `SessionData` requiere tocar template + quizá frontmatter — acople alto.
16. **`auto_expire_days` declarado pero sin implementación en el scope** — `routing.py:67` define 14 días para HANDOFF y 180 para RUNBOOK, pero ningún módulo de este paquete expira nada (quizás lo haga enterprise/maintenance fuera del scope). Declarativo sin enforcement visible aquí.
17. **`extra="allow"` en CommonFrontmatter** — `schemas/base.py:32`: acepta campos arbitrarios en frontmatter; combinado con `legacy_*` de migración está bien, pero debilita la garantía de schema canónico y permite typos silenciosos en notas escritas a mano.

## 4. Deudas y oportunidades de refactor

1. **Eliminar la duplicación Local/Enterprise de schemas** mediante mixin(s) de campos tipo-específico (`class _ADRFields(BaseModel)` + dos subclases finas), como ya hace `session.py` conceptualmente (pero allí quedó sin usar). Ahorra ~400 líneas y elimina el riesgo de divergencia.
2. **Binding de writers sin mutación global**: mover `writer` a un registro construido explícitamente (`get_route(doc_type) -> RouteSpec with writer`), o registrar los writers directamente en `routing.py` con lazy import para evitar ciclo. Elimina la trampa de import-order de `__init__.py`.
3. **Unificar inventario**: borrar `_SUBFOLDER_TO_DOC_TYPE` y `_ADR_FILENAME_RE` de `inventory.py` (ya delegados) y el `_SessionFields` muerto de `session.py`.
4. **Extraer la lógica común de los 15 writers**: ya existe `_write_canonical`; los wrappers son casi idénticos — una tabla `(validator_pre, doc_type, enforce_local_scope)` reduciría writers.py a ~150 líneas. Los guards específicos (postmortem/changelog/handoff/hu/design/glossary) pueden declararse en RouteSpec.
5. **Clock injection consistente en migration** (pasar `now` hasta `_type_specific_for`).
6. **Backup seguro**: `tar.extractall(target_parent, filter="data")`.
7. **Fingerprint de nota completa** (body+frontmatter estable) o un campo `updated_at` check para distinguir retry de update.

## 5. Preparación para un cambio grande

**Qué tocaría primero:**
1. Consolidar schemas (refactor #1) — es el mayor multiplicador de costo: cualquier cambio de frontmatter hoy toca 2 clases por tipo.
2. Des-mutar `DOC_TYPE_ROUTING` (#2): un cambio grande en routing/writers va a tropezar con el binding en `__init__.py`.
3. Agregar tests de contrato entre `filename_template` ↔ `_build_filename_context` ↔ `_type_specific_fields`: hoy la coherencia entre el nombre de archivo y el frontmatter se mantiene a mano por convención (p.ej. `_adr_number` viaja por `filename_ctx`, `writers.py:167,237`).

**Qué es frágil:**
- El pipeline filename↔frontmatter vía `filename_ctx` con claves privadas (`_adr_number`, `_incident_number`) es frágil y poco tipado.
- Los templates Jinja2 dependen de `asdict(data)`: renombrar un campo de dataclass rompe el render en runtime, no en import.
- La coerción silenciosa de status y el extra="allow" hacen que datos malformados entren al vault sin ruido.
- Numeradores secuenciales sin lock bajo concurrencia MCP.

**Fortalezas:** separación de capas clara y bien documentada con fases; validación Pydantic estricta donde importa (fechas tz-aware, fingerprints, statuses); idempotencia pensada para retries reales; migración conservadora (dry-run + backup + preservación legacy); suite de tests unitarios extensa en `tests/unit/documentation/`.

**Salud general:** BUENA (7/10). Arquitectura sólida y testeada; el riesgo principal es mantenibilidad por duplicación de schemas y estado global mutable en el binding de writers, más algunos bugs menores concretos (backup extractall, race en numeración, contadores de validate_vault).
