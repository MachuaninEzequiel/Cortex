# Progreso STREAM A — Obra 07 · P12 (contenido-y-escritura)

> Stream A del dual-stream P12 (reglas §7 de `09-DEUDA-MIGRACION-PYTHON.md`).
> Este archivo es el único registro de progreso de este stream: NO actualiza
> ESTADO-ACTUAL.md ni HANDOFF.md ni el doc 09.
>
> Territorio: `rust/crates/cortex-app/` (extensiones episodic.append, semantic
> reindex, workitems, pr, context extras, documenter/interactive),
> `rust/crates/cortex-mcp/src/server.rs` handlers, NUEVO
> `rust/crates/cortex-services/`, gates `bench/parity/*p12a*`.

## P12A-1 — prereq escrituras: episodic.append + semantic.index_file + security

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Qué se portó:

- **`cortex-app/src/security.rs`** (nuevo): puerto completo de
  `cortex/security/paths.py` — `resolve_safe`, `validate_under_root`,
  `PathSecurityError`, con mensajes de error idénticos y un
  `resolve_lenient` que replica el `Path.resolve()` no estricto de Python
  (canonicaliza el ancestro existente más profundo). Tests propios.
- **`cortex-app/src/episodic/entities.rs`** (nuevo): puerto 1:1 de
  `_extract_entities` — los 8 patrones regex por categoría, orden de
  inserción estable, dedup primera aparición, tupla → primer grupo no-vacío,
  cap 15. Expectativas de tests validadas CONTRA EL ORÁCULO Python
  (`"función"` no matchea; `"importar os"` no matchea dependency).
- **`cortex-app/src/episodic/mod.rs`**: `NativeEpisodicStore::append`
  (puerto de `EpisodicMemoryStore.add`): genera `mem_{hex8}` +
  `datetime.now(UTC).isoformat()` con microsegundos, mergea entidades sobre
  extra_metadata (pisa `"entities"` como Python), serializa la meta
  flattenada con el mismo orden de claves de `_serialize_metadata`
  (`serialize_metadata`) y escribe la fila al JSONL en modo append-only
  (líneas previas byte-idénticas) + insert ordenado por id en el vec
  in-memory. Serializador compacto estilo CPython (`json.dumps(...,
  ensure_ascii=False)`: floats repr shortest, `\b`/`\f` nombrados).
- **`cortex-app/src/semantic/mod.rs`**: `SemanticIndex::index_file` (puerto
  de `VaultReader.index_file`): upsert preservando posición de inserción,
  purga+regeneración de chunks del padre vía `chunks_for_doc` (compartido
  con sync), recalculo completo BM25 (`recompute_stats`, refactor compartido
  con build), embed batch inyectado. Archivo inexistente ⇒ `Ok(false)` como
  Python; otros errores ⇒ `Err(msg)` (divergencia documentada, estrictamente
  más informativa).

Gate: `bench/parity/p12a1_golden.py` (build/verify) +
`rust/crates/cortex-app/examples/p12a1_check.rs`:

- episódico: store real Python (chroma + ONNX real) con las 12 memorias del
  golden P3 + 4 appends vía `store.add`; Rust carga el export base y appendea
  con ort real. Resultado: entries after 16/16 idénticas (claveadas por
  document), rankings vectoriales post-append exactos por ORDEN (6 queries),
  keyword bypass idéntico, filas JSONL con meta byte-parity.
- semántico: R1 (sync) y R2 (modificación de specs/2026-06-01_gate.md +
  index_file incremental) idénticos al oráculo + contrato interno
  incremental==full-rebuild.
- Normalizaciones pactadas documentadas en el header: ids/timestamps
  aleatorios ⇒ comparación claveada por document / `{{TS}}`; embeddings con
  tolerancia ≤1e-4 (el contrato conductual son los rankings exactos); orden
  de claves dentro de meta no es contrato (chroma no lo garantiza); keyword
  hits ordenados.

Verificación: `cargo test -p cortex-app` 58 passed · clippy `-D warnings`
limpio · fmt limpio · suite Python **2455 passed, 18 skipped**.

Lecciones del gate (bugs atrapados antes del commit):

1. El gate original capturaba R2 sin escribir la modificación en disco antes
   de `index_file` — el drift era del oráculo, no del porte.
2. Los flags `entity_*` van normalizados a minúsculas por
   `_entity_filter_key` (validado contra Python).

## P12A-2 — workitems/hu: WorkItemService nativo

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Recuperación del WIP de la sesión muerta: triage completo antes de escribir
nada nuevo. El WIP compilaba y estaba estructuralmente fiel al oráculo; se
CONTINUÓ (no reiniciado) corrigiendo 4 defectos de paridad detectados en el
triage:

1. `has_provider` normalizaba case/trim — Python hace lookup DIRECTO
   (`golden S05: FAKE_normaliza=False`); la normalización vive sólo en
   `import_item`/_provider.
2. Edge `status=""`: Python (`item.status or "imported"`) cae al default;
   Rust sólo trataba None.
3. Checker: título S02 con llaves cuádruples, copia de fixture no recursiva
   (fallaba con vault/hu/) y formato repr Python (comillas simples,
   True/False, KeyError con repr citado).
4. **synced_at / str(datetime)**: HUData es dataclass ⇒ el servicio Python
   pasa OBJETOS datetime; el body los renderiza como `str(dt)`
   ("2026-08-22 14:03:00+00:00") mientras el frontmatter serializa
   pydantic/RFC3339 ("...T14:03:00Z"). El writer nativo usa el mismo campo
   para ambos (body raw, frontmatter opt_dt): se pasa la forma str(dt) y
   `normalize_pydantic_datetime` (cortex-setup) aprende a aceptar separador
   espacio (reintento T-form). Inputs Z-form intactos — gates P8 verdes
   (cargo test -p cortex-setup 16 passed post-cambio).

Qué se portó:

- **`cortex-app/src/workitems.rs`** (nuevo, ~740 líneas): models
  (TrackedItem/WorkItemSource/WorkItemKind), trait WorkItemProvider,
  WorkItemService con import_item (KeyError/RuntimeError con mensajes de
  Python), get_item_note (naming canónico HU-{id} + fallback slug legacy),
  list_item_notes, has_provider; escritura vía writer canónico
  `build_note("hu")` (API estable P8b) + semántica de duplicados por
  fingerprint (no-op idempotente / DuplicateDocumentError mensaje exacto);
  resumen episódico (_store_episodic: truncado 300 chars, 5 criterios) y
  reindex semántico tras traits inyectables SemanticIndexer/EpisodicSink
  con adapters live sobre semantic.index_file + episodic.append (P12A-1).
  7 tests unitarios espejando tests/unit/workitems.
- **`bench/parity/p12a2_golden.py`**: oráculo determinista S01–S09
  (fakes espejo del test_service.py; synced_at FIJO ⇒ todo lo demás
  determinista; normalizaciones {{ROOT}}/{{TS}} pactadas).
- **`rust/crates/cortex-app/examples/p12a2_check.rs`**: checker Rust que
  reproduce S01–S09 y compara byte-a-byte contra golden_p12a2.txt.

Verificación: gate verify PASS (oráculo determinista) + checker PARIDAD
COMPLETA · cargo test -p cortex-app 65 passed · clippy/fmt limpios ·
suite Python oráculo completa verde (--no-cov).

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| P12A-1 episodic.append + semantic.index_file + resolve_safe | ✅ | `bench/parity/p12a1_golden.py` verify PASS + `p12a1_check` PARIDAD COMPLETA (16/16 entries · 6 rankings exactos · R1/R2 idénticos · incremental==rebuild); suite Python 2455 passed | `c9b62ab` |
| P12A-2 workitems/hu WorkItemService | ✅ | `bench/parity/p12a2_golden.py` verify PASS + `p12a2_check` S01–S09 PARIDAD COMPLETA byte-a-byte; suite oráculo verde | `e587d2a` |
| P12A-3 pr_context: PRContext + pr_capture + PRService.store | ✅ | `bench/parity/p12a3_golden.py` verify PASS + `p12a3_check` S01–S12 PARIDAD COMPLETA byte-a-byte (JSON pydantic idéntico, payload de store exacto); suite oráculo verde | `8e90ee6` |
| P12A-4 doc_generator/doc_validator/doc_verifier | ✅ | `bench/parity/p12a4_golden.py` verify PASS + `p12a4_check` S01–S14 PARIDAD COMPLETA byte-a-byte (contenido/filenames, issues, clasificación y JSON); suite oráculo verde | `d682bee` |
| P12A-5 cortex-services: SpecService + NoteService | ✅ | `bench/parity/p12a5_golden.py` verify PASS + `p12a5_check` S01–S10 PARIDAD COMPLETA byte-a-byte (contenido, payloads, proposal/hooks/session y rollback); suite oráculo verde | `fffc4cd` |
| P12A-6 documentation/migration (docs-migrate) | ✅ | `bench/parity/p12a6_golden.py` verify PASS + `p12a6_check` S01–S12 PARIDAD COMPLETA byte-a-byte (dry-run/apply/idempotencia/force/inferencia/report/legacy/backups/status/validate/títulos/fechas); suite oráculo verde | `bc9d218` |
| P12A-7 context extras (filters/domain/observer/telemetry/presenter) | ✅ | `bench/parity/p12a7_golden.py` verify PASS + `p12a7_check` S01–S27 PARIDAD COMPLETA byte-a-byte (filtros, presentadores ×5, detector reglas+embedding a 6 decimales, observer files/pr/git, telemetría JSONL/aggregate/citas); suite oráculo verde | `34b9064` |
| P12A-8 documenter/interactive | ✅ | `bench/parity/p12a8_golden.py` verify PASS + `p12a8_check` S01–S19 PARIDAD COMPLETA byte-a-byte (máquina de estados con I/O stubbed: approve/cancel/handoff/edit/ADRs/seed/agotamiento); suite oráculo verde | `08ae11f` |
| P12A-9 mcp handlers in-process (familia sesiones) | ✅ | `bench/parity/p12a9_golden.py` verify PASS + `p12a9_check` S01–S22 PARIDAD COMPLETA byte-a-byte (payloads JSON orden-pydantic, errores ❌, quality-gates, handoff YAML, claims vs repo temporal); resto de rutas mantiene fallo explícito §7.1.4; suite oráculo verde | `42eedd8` |

## Micro-ADR: toque quirúrgico en cortex-setup::writers (normalize_pydantic_datetime)

- **Decisión**: aceptar además la forma `str(datetime)` de Python
  ("2026-08-22 14:03:00+00:00", separador espacio) con reintento T-form
  dentro de `normalize_pydantic_datetime`, para que un único valor alimente
  body (raw = str(dt)) y frontmatter (normalizado pydantic) en paridad.
- **Justificación**: el servicio workitems recibe datetimes reales de los
  providers (pydantic TrackedItem); HUData es dataclass y el template hu
  renderiza `{{ synced_at }}` directo. Sin esto, body o frontmatter
  divergen siempre. Cambio aditivo: inputs RFC3339/Z-form toman el camino
  original (gates P8 verdes post-cambio, 16 tests cortex-setup).
- **Alternativas descartadas**: duplicar la lógica del writer en
  cortex-app (pierde garantías P8b), cambiar el oráculo/golden (el golden
  ES el comportamiento Python real), tocar template_vars por doc-type
  (más invasivo).

## ADR chico: dependencia uuid en cortex-app

- **Decisión**: agregar `uuid = { version = "1", default-features = false,
  features = ["v4"] }` a cortex-app para generar ids `mem_{hex8}` fieles a
  `f"mem_{uuid4().hex[:8]}"` de MemoryEntry.
- **Justificación**: paridad de formato de ids sin inventar un generador
  propio; `uuid 1.25.0` ya estaba en `Cargo.lock` (transitivo) y v4 usa
  getrandom ya presente ⇒ cero paquetes nuevos en el lock (diff verificado:
  solo la línea `uuid` en deps de cortex-app).
- **Alternativas descartadas**: hex derivado de timestamp/pid (no es v4,
  colisiones triviales en batch), dep nueva `rand` directo (innecesaria).

## P12A-3 — pr_context: PRContext + pr_capture + PRService.store

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Qué se portó (`cortex-app/src/pr.rs`, nuevo):

- **PRContext** con orden de declaración pydantic como contrato JSON:
  serializador propio estilo `model_dump_json(indent=2)` (nulls explícitos,
  UTF-8 crudo) y parser tolerante con required title/author/source_branch/
  commit_sha. Métodos `hu_references` (4 patrones IGNORECASE en orden,
  prefijos por patrón, dedup por conjunto — el ORDEN no es contrato porque
  Python hace `list(set(refs))`), has_db_changes / has_api_changes /
  has_adr_label fieles al spec.
- **pr_capture**: run_git (stdout strip, errores ⇒ vacío),
  get_files_changed con fallback origin/base, diff_summary --stat,
  detectores db/api con indicadores lowercase, capture_manual (+ variante
  `_in` con cwd inyectable), capture_from_github con getenv inyectable,
  save_context/capture_from_json byte-parity, enrich_with_pipeline que
  devuelve copia sin mutar el original.
- **PRService.store_pr_context**: enrich local + resumen multilínea EXACTO
  (summary / Description[:500] con \\n inicial / Diff:\\n{stat} / Lint-Audit-
  Tests con "n/a" default — los saltos dobles del join son parte del
  contrato), tags `[pr, author]+labels`, files truncado a 20,
  context_metadata, sobre el trait EpisodicSink de P12A-2.
- generate_pr_docs/write_pr_docs quedan para P12A-4 junto al porte de
  doc_generator (dependencia declarada del servicio).
- La presentación typer (`cli/pr_context.py`) la wirea el CLI nativo de B
  (§7.1.3); acá vive la capa de servicio.

Gate: `bench/parity/p12a3_golden.py` (build/verify) +
`examples/p12a3_check.rs`: S01–S12 sobre cwd tmp SIN repo git (la ruta git
queda determinista-vacía en ambos lados; misma ruta de código), JSON
pydantic byte-a-byte (incluye unicode/saltos), payload del sink con
json.dumps(indent=1, sort_keys) espejando p12a2, roundtrip save→load→save
idéntico.

Verificación: gate verify PASS + checker PARIDAD COMPLETA · cargo test -p
cortex-app 73 passed · clippy/fmt limpios · suite Python oráculo completa
verde.

Observación para el dueño/oráculo: el test
`tests/unit/ide/test_contract_git_dirs.py::TestUninstallIdempotency[...]`
es FLAKY dependiente de orden bajo pytest-randomly (falló en runs completos
dos veces, pasa aislado y con `-p no:randomly`). No relacionado con P12A
(no se tocó código Python). Queda registrado acá porque la suite es el
oráculo compartido.

## P12A-4 — doc_generator + doc_validator + doc_verifier

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Qué se portó:

- **`doc_generator.rs`**: `GeneratedDoc`/DocTypeGen y generador fallback de
  UNA nota session; template por replace simple + placeholder restante→N/A
  (no jinja), body[:300], files[:20], labels[:5], resultados pipeline/default
  "not run", safe_filename fiel (incluye trailing dash si los símbolos dejan
  espacio final), generate_all/skip_types, write_docs/generate_and_write.
  El reloj es explícito (patrón P8/workitems); el oráculo congela datetime con
  monkeypatch `_patch_now` de P8.
- **`doc_validator.rs`**: frontmatter YAML por delimitadores, checks title y
  date/created, extracción wikilinks sin embeds, limpieza |/#/^, embeds
  rotos con lookup con/sin .md, batch y to_dict. El texto específico de YAML
  inválido NO es contrato (PyYAML vs serde_yaml) y se normaliza a
  `{{YAML_ERR}}`; field/severity/is_valid sí son contrato.
- **`doc_verifier.rs`**: verify_from_list y git diff --name-status; filtro
  único vault/.md; unión vault_files + particiones exclusivas new/modified/
  deleted, has_agent_docs sólo new|modified, métricas, error git EXACTO
  `git status failed: None` (Python no captura stderr), error vault relativo
  fuera de root, to_json(indent=2) manual para preservar ORDEN Python de
  claves (serde_json default ordena alfabético).
- **PRService completado**: generate_pr_docs y write_pr_docs sobre
  DocGenerator + index_file semántico selectivo; fallo de index o doc fuera
  del vault no aborta (Python loguea warning).

Gate: `bench/parity/p12a4_golden.py` + `examples/p12a4_check.rs`, S01–S14:
session completa/vacía, safe_filename, skip/write, validator inexistente/
sin-fm/válida/embed roto/YAML inválido/parcial, verifier from_list/git
nonrepo/vault fuera, contenido e JSON byte-a-byte.

Verificación: gate verify PASS + checker PARIDAD COMPLETA · cargo test -p
cortex-app 76 passed · clippy/fmt limpios · suite Python oráculo completa
verde (`PYTEST_RC=0`).

## P12A-5 — cortex-services: SpecService + NoteService

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Se creó el crate propio **`rust/crates/cortex-services/`** y se agregó como
member quirúrgico del workspace (Cargo.lock: sólo package cortex-services;
regex/uuid ya presentes, cero paquetes nuevos).

Arquitectura:

- Puertos `SemanticPort` (Result en index/sync para rollback),
  `EpisodicPort`, `SessionOpener`; request episódico propio; adapter de
  SessionOpener sobre SessionService nativo de cortex-app.
- Persistencia común sobre `cortex_setup::writers::build_note` con writer
  canónico P8, idempotencia por fingerprint y DuplicateDocumentError exacto.
- **SpecService**: proposal_mode optional|required|skip y errores exactos;
  verification hooks typed o dict (serde defaults, nombres únicos y error de
  duplicados con repr Python); tasks-required opt-in; spec writer draft;
  index selectivo/sync; orden duro write→index→sync→Session→episodic;
  Session best-effort (fallo nunca bloquea), summary goal-or-title;
  memoria spec con requirements[:8].
- **NoteService**: writer session con id uuid4 hex[:12] (reusa decisión uuid
  P12A-1; variante create_with_id sólo para gates), completed/handoff,
  blockers/verified/unverified/skills/telemetry/tasks/gitless; index selectivo,
  sync opcional, memoria session (changes[:8], decisions[:5]); rollback
  transaccional unlink+propagación ante fallo semantic/sync/episodic después
  de persistir; remember=false saltea episódico. Alias SessionNoteService.

Gate `p12a5`: S01–S10 con normalizaciones {{ROOT}}/{{DATE}}/{{TS}}/{{SID}}/
{{FP}} pactadas; compara contenido completo, payloads episódicos, propuesta,
hooks, tasks, orden session, handoff y rollback byte-a-byte.

Verificación: oráculo determinista + checker PARIDAD COMPLETA · cargo test -p
cortex-services 4 passed · clippy/fmt/metadata limpios · suite Python completa
verde (`PYTEST_RC=0`).

## P12A-6 — documentation/migration (docs-migrate)

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Módulo **`rust/crates/cortex-services/src/migration.rs`** (~1400 líneas con
tests) que replica `cortex/documentation/migration.py`:

- `migrate_vault` dry-run/apply con idempotencia (`schema_version=1` +
  `doc_type` string), `force`, exclusión de `.cortex/backups` y `_archived`,
  orden `rglob("*.md") sorted`, backup tar.gz previo al apply.
- Frontmatter canónico: título `str.title()` CPython, fechas ISO (rama string:
  naive ⇒ UTC aware; clamp updated≥created; mtime fallback), tags/status con
  mapeos generated→completed / imported→backlog y default primer status
  ordenado, wikilinks dedup+sort, fingerprint SHA-256 del body, type-specific
  por DocType (ADR/INC/PM desde stem regex, session_id derivado con slug,
  HU/glossary/changelog/runbook/decision/architecture), preservación
  `legacy_*` en orden original del YAML.
- `create_backup`: shell-out a `tar czf` (contenido del archivo NO es
  contrato; sólo existencia/nombre normalizado {{STAMP}}).
- `validate_vault` estructural: errores EXACTOS "No frontmatter in…",
  "doc_type field is required…", "doc_type must be a string, got int",
  "Unknown doc_type: 'x'", "vault_scope must be 'local' or 'enterprise', got
  'cloud'"; fallos de schema pydantic colapsados a {{SCHEMA_ERR}} y YAML
  inválido a {{YAML_ERR}} (volcados internos no contrato), contadores de
  validez idénticos vía campos requeridos por tipo.
- Divergencias documentadas en cabecera del módulo: parser serde_yaml vs
  PyYAML y timestamps planos no resueltos (los fixtures citan fechas, ambos
  lados van por la rama string).

Gate `p12a6` S01–S12: dry-run, apply, idempotencia, force, matriz de
inferencia (11 carpetas + design), unclassifiable+format_report,
preserve/drop legacy, backups+exclusiones, status mapping, payloads JSON de
validate_vault, títulos/derives y resolución de datetimes (+02:00/Z/clamp/
mtime). Normalizaciones pactadas {{ROOT}}/{{TS}}/{{STAMP}}/{{SCHEMA_ERR}}/
{{YAML_ERR}}; fechas deterministas fijadas además en líneas clave=valor.

Verificación: oráculo determinista + checker PARIDAD COMPLETA · cargo test -p
cortex-services 10 passed · clippy/fmt limpios · suite Python completa verde
(`PYTEST_RC=0`). Nota operativa: se encontró `.cortex/heavy.lock` como archivo
huérfano sin proceso vivo (bloqueaba ambos streams bajo la convención mkdir);
fue eliminado antes del gate.

## P12A-7 — context extras (filters/domain/observer/telemetry/presenter)

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Nuevos módulos en **`cortex-app/src/context/`** completando el enricher P7:

- **`filters.rs`**: `EnrichmentFilters` + `apply_filters(_at)` AND-compuestos
  (doc_types strict/tolerante, statuses in/out, tags AND/OR/exclude,
  vault_scope, max_age con naive⇒UTC y clock inyectable, project_ids);
  default no-op con `vault_scope="all"`.
- **`domain_detector.rs`**: DOMAIN_RULES canónica (12 dominios) + RULE_ORDER;
  scoring 0.6 archivos / 0.4 keywords; fallback embeddings vía
  `cortex_embed` ONNX all-MiniLM-L6-v2 con centroides idénticos al Python —
  confianzas iguales a 6 decimales en todos los casos sub-threshold del gate
  (0.167022 i18n, 0.437747 auth, 0.360362, 0.316439…).
- **`observer.rs`**: `ContextObserver` git_diff/pr/manual; extractores regex
  MULTILINE de imports top-level/functions (filtro if/else/for/while por
  substring como Python)/classes; keywords por frecuencia top-15 estables;
  text_keywords únicos max-10; 4 search queries.
- **`telemetry.rs`**: `PersistentObserver` JSONL append-only con rotación
  5 MB→`.1.jsonl`; iter (rotada primero, malformed skip), events_for_run,
  aggregate (hit rate global y por estrategia en orden de primer
  aparecimiento = Counter, percentiles p50/p95/p99 interpolados),
  `detect_citations` wiki/md con alias/ancla/dedup por orden ofrecido,
  `make_observer` con bloque retrieval.telemetry. Emisión JSONL y payloads
  en orden de dict de Python vía Pj compacto + conversión Value→Pj
  canónica (serde_json ordena claves ⇒ no contrato directo).
- **`presenter.rs`**: markdown/compact/grouped×2 (grupos ordenados por max
  enriched_score desc estable; OTHER al final); excerpt 200/300 chars con
  `…`; labels `_search/_query` stripped.
- **models/pyjson**: `dumps_ascii` (ensure_ascii=True default de json.dumps)
  para presenter.to_json; campo `within_budget_override` (EnrichedContext lo
  trae como campo, no calculado); `Pj: Clone`.

Gate `p12a7` S01–S27 con normalizaciones {{ROOT}}/{{RUN}}/{{TS}}; S19 usa un
repo git temporal + chdir (`_run_git` observa el CWD del proceso, igual que
Python). Verificación: oráculo determinista + checker PARIDAD COMPLETA ·
cargo test -p cortex-app 96 passed · clippy/fmt limpios · suite Python verde
(`PYTEST_RC=0`). Nota operativa: `.cortex/heavy.lock` volvió a aparecer como
archivo huérfano sin proceso vivo; eliminado antes del gate.

## P12A-8 — documenter/interactive

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

**`cortex-app/src/documenter/interactive.rs`** replica la máquina de estados
de `cortex/documenter/interactive.py` (T4.1):

- `InteractiveAction`/`InteractiveResult` (cancelled, forced_status,
  edited_note_title/body, approved_adr_indices) y `InteractiveSession` con
  I/O inyectable (`InputProvider` + `EditorOpener`) para ejercitarla sin
  terminal.
- Flujo fiel: menú A/E/H/C con loop de inválidos; handoff con razón vacía →
  vuelve al menú; EDIT secuencial título→cuerpo→ADRs uno a uno (default Y);
  seed del editor canónico (título + comentario + notas de checkpoints) con
  comparación trimmed para detectar edición real; confirmación post-edición
  A/H/C; CANCEL descarta ediciones; HANDOFF tras edit conserva ediciones y
  razón vacía ⇒ "".
- Divergencia documentada: el rendering rich NO es contrato — se produce un
  transcript de texto plano no gateado. EditorOpener recibe String propio
  para evitar HRTB en stubs.

Gate `p12a8` S01–S19 determinista puro (sin relojes ni UUID): acciones
top-level, case-insensitivity, loop de inválidos, flujo EDIT completo,
review de ADRs (default None=aprobar todos, explícito [], rechazo parcial),
seed del editor y agotamiento de cola (catch_unwind del provider).

Verificación: cargo test -p cortex-app 100 passed · clippy/fmt limpios ·
suite Python completa verde (`PYTEST_RC=0`).

## P12A-9 — mcp handlers in-process (familia sesiones)

Estado: ✅ COMPLETADA dentro del alcance permitido por §7.1.4.

**`cortex-mcp/src/handlers_sessions.rs`**: los 12 handlers de la familia
sesiones/checkpoints/tasks pasan de fallo explícito a llamadas in-process
sobre un `SessionsBackend` inyectable:

- open/checkpoint/close/status/list + task list/update (create-or-update),
  close_session, save_session, review_checkpoint (quality_gates nativo vía
  files_in_scope resuelto por el backend), validate_handoff (serde_yaml con
  defaults pydantic replicados en AgentHandoff/ArtifactProduced) y
  verify_session_claims (heurística git diff portada directa).
- Wire-format exacto: emisor propio con separadores ", "/": " y orden de
  claves = declaración pydantic sobre serde_json/preserve_order; mensajes ❌
  y listas de valores válidos byte-a-byte.
- `server.rs`: campo opcional sessions_backend + SESSION_TOOLS routing;
  sin backend ⇒ se conserva el fallo explícito documentado (patrón P6).
- Alcance honesto restante (fallo explícito vigente): search/context/
  sync_ticket/proposal/autopilot/documenter-briefing/finish/write-doc —
  dependen de la decisión wire-format rmcp (§7.1.4) y del layout workspace
  (stream B); jamás fingir paridad conductual.

Gate `p12a9` S01–S22 determinista con stub backend espejo: payloads,
errores de validación, veredictos accept/redelegate/warn de quality-gates,
handoff YAML happy/mismatch/vacío y claims contra repo temporal.

Verificación: cargo test -p cortex-mcp -p cortex-app verde · clippy/fmt
limpios · suite Python oráculo completa verde (`PYTEST_RC=0`). Nota:
`.cortex/heavy.lock` volvió a quedar como archivo huérfano; eliminado.

## Cola restante (orden de dependencias)

| Tarea | Estado |
|---|---|
| ~~P12A-2 workitems/hu (~685)~~ | ✅ completada |
| ~~P12A-3 pr_context (~623) + gate CliRunner→checker~~ | ✅ completada |
| ~~P12A-4 doc_generator/doc_validator/doc_verifier (~590)~~ | ✅ completada |
| ~~P12A-5 spec_service + note_service (~541)~~ | ✅ completada |
| ~~P12A-6 documentation/migration docs-migrate (~565)~~ | ✅ completada |
| ~~P12A-7 context extras observer/telemetry/domain/filters/presenter (~1902)~~ | ✅ completada |
| ~~P12A-8 documenter/interactive (~342)~~ | ✅ completada |
| ~~P12A-9 mcp handlers in-process (~2056): familia sesiones IN-PROCESS; resto fallo explícito (§7.1.4)~~ | ✅ completada |
Notas de coordinación dual-stream:

- Handlers MCP de ESCRITURA: quedan con fallo explícito actual hasta que
  exista la decisión del dueño sobre wire-format rmcp (HANDOFF §4.8); se
  documentará acá cuando P12A-9 entre.
- Sin toques a territorios de B (crates nuevos, cortex-cli, bench/*p12b*,
  docs de B ni ESTADO-ACTUAL/HANDOFF/doc 09).
