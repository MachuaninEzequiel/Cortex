
# Review — `cortex.documenter`, `cortex.workitems` y servicios (`note_service`, `pr_service`, `spec_service`)

Repo: `/home/chucho/Cortex` (paquete `cortex-memory`). Solo lectura; ninguna línea del repo fue modificada.
Verificación: `uv run pytest tests/unit/documenter tests/unit/services --no-cov -q` → **113 passed**.

---

## 1. Propósito y arquitectura interna

### 1.1 `cortex.documenter` — Documenter Reconstruction Mode

Implementa el algoritmo de 8 pasos de `docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md` §7.2:
dado un `SessionRecord` (típicamente OPEN, a punto de cerrarse), reconstruye qué se hizo, verifica,
detecta contradicciones, sintetiza un handoff y persiste la nota de sesión + ADRs candidatos.

| Módulo | Responsabilidad |
|---|---|
| `reconstruction.py` (486 l) | Orquestador `Reconstructor.reconstruct()` — sin estado, read-only. Produce `ReconstructionOutput` inmutable (frozen dataclass, reconstructor.py:72-113). |
| `persistence.py` (482 l) | `DocumenterPersister.finalize()` — único punto side-effecting: escribe nota vía `NoteService`, escribe ADRs vía `write_adr_note`, cierra la sesión vía `SessionService.close`. Idempotente (persistence.py:144-160). Incluye self-review informativo del draft (Phase 08/T8.3). |
| `spec_loader.py` (132 l) | Lee frontmatter YAML del spec → `LoadedSpec` typed. Lenient: hooks inválidos se saltean con warning (spec_loader.py:87-105); fallback a sección `## Goal` del body para specs legacy (spec_loader.py:108-129). |
| `diff_parser.py` (76 l) | Parsea `git diff --name-status`. Lenient por diseño: status desconocido → `"modified"`, línea malformada → skip (diff_parser.py:56-62). |
| `adr_evaluator.py` (114 l) | Heurística keyword-based sobre notas de checkpoints → `ADRSuggestion` con confidence high/low (≥2 keywords vs 1) (adr_evaluator.py:83-103). `diff_text` aceptado pero ignorado (`noqa: ARG001`, adr_evaluator.py:65). |
| `contradiction_detector.py` (92 l) | Protocolo pluggeable `ContradictionDetector`; default `NoOpContradictionDetector` para no cargar ChromaDB/ONNX en el path CLI (contradiction_detector.py:9-18). |
| `interactive.py` (346 l) | UX de prompt interactivo (`finish-session --interactive`) con `rich`. State machine testeable vía `input_provider`/`editor` inyectables (interactive.py:170-180). Produce `InteractiveResult` que el CLI traduce a `FinishOverrides`. |

Decisiones de diseño clave:
- **Read model vs write model estrictos**: `Reconstructor` no muta nada; solo `DocumenterPersister` cierra. Esto hace al algoritmo re-ejecutable y testeable.
- **Inyección de dependencias**: `Reconstructor(session_service, verification_runner, repo_root, contradiction_detector)` (reconstruction.py:130-142).
- **Gitless mode** (reconstruction.py:165-171): sin git, `files_touched` sale de `Checkpoint.artifacts_touched`; se marca `gitless=True` y tag `gitless`.
- **Procedencia de archivos** (Phase 09.A+, reconstruction.py:103-113, 184-199): separa `files_verified_by_git` (✓) de `files_declared_only` (◌); la nota muestra el marcador y un next-step explícito (persistence.py:206-244).
- **Self-review no bloqueante** (persistence.py:44-70, 329-359): escanea placeholders, archivos no mencionados y claims de éxito sin evidencia; agrega `[self-review]` a next_steps y tag `auto-draft`. Comentario explica por qué no bloquea (evita loops infinitos en flujo agéntico).

### 1.2 `cortex.services` — servicios de dominio extraídos de `AgentMemory`

| Servicio | Responsabilidad |
|---|---|
| `note_service.py` (244 l) | Crea notas de sesión en `vault/sessions/` vía `write_session_note_canonical`, indexa selectivamente en el store semántico, guarda resumen episódico. **Transaccional**: si falla indexado/episodic tras escribir el archivo, lo unlink y propaga (note_service.py:174-207) — restaura la invariante "archivo en disco ⇒ archivo indexado". |
| `spec_service.py` (297 l) | Crea specs en `vault/specs/`, normaliza `verification_hooks` (rechaza duplicados por nombre, spec_service.py:254-275), abre automáticamente un `SessionRecord` (fallo de sesión NO bloquea creación, spec_service.py:224-237), gate `proposal_mode` optional/required/skip (spec_service.py:168-178). Orden deliberado: escribir+indexar → abrir sesión → episodic, para que un embedder lento nunca retrase el puntero de sesión activo (spec_service.py:214-223). |
| `pr_service.py` (178 l) | Workflow DevSecDocOps: enriquece `PRContext` con resultados de pipeline y lo guarda episódicamente (`store_pr_context`), genera docs fallback (`generate_pr_docs`), los escribe + indexa (`write_pr_docs`). Imports lazy de `pr_capture`/`DocGenerator` dentro de los métodos (pr_service.py:84,133,152). |

### 1.3 `cortex.workitems` — integración opcional de work items externos

- `models.py`: `TrackedItem` (pydantic) como representación canónica; `WorkItemSource` hoy solo `JIRA`.
- `providers/base.py`: ABC `WorkItemProvider` read-only (`source_name`, `is_configured`, `get_item`).
- `providers/jira.py` (166 l): REST Jira con Basic Auth (email+token desde env configurables), parseo de descripción ADF (`_flatten_adf`, recursivo sobre paragraph/heading/text/bulletList), extracción heurística de acceptance criteria (bullets), mapeo issue-type→kind.
- `service.py` (152 l): `import_item` = fetch → escribir nota HU canónica (`HU-{external_id}.md`) → indexar semántico → episodic opcional.

---

## 2. Flujo de datos / puntos de entrada y salida

```
CLI cortex finish-session (cli/main.py:1080-1180)
MCP server (mcp/server.py:2548, 2810)
Autopilot service.finish(auto=True) (autopilot/service.py:350+)
        │
        ▼
Reconstructor ──lee──► SessionService.get, load_spec, git.diff/diff_name_status, VerificationRunner
        │             └─(plug)─► ContradictionDetector (NoOp en CLI)
        ▼
ReconstructionOutput ──► DocumenterPersister.finalize()
                              ├─► NoteService.create ─► vault/sessions/*.md + VaultReader.index_file + EpisodicMemoryStore.add
                              ├─► write_adr_note(vault=_VaultPathOnly) ─► ADR-*.md
                              └─► SessionService.close(status, session_note_path, adrs_created)

SpecService ◄── AgentMemory façade (core.py:288) ◄── CLI/MCP create-spec
WorkItemService ◄── AgentMemory lazy (core.py:876-881) ◄── MCP tool import-work-item (server.py:2810), CLI (--provider jira, main.py:2014)
PRService ◄── AgentMemory (core.py:301) ◄── workflow PR DevSecDocOps

Consumidores indirectos: cortex/ci/validator.py reusa `_scope_cross_check` y `load_spec`
(documenter importados como librería — acoplamiento a helpers privados, ver §4).
```

---

## 3. Invariantes importantes

1. **Idempotencia de finalize**: sesión ya no-OPEN ⇒ devuelve paths existentes sin reescribir (persistence.py:147-160). El CLI también pre-chequea (main.py:1090-1098).
2. **File-on-disk ⇒ indexed** (NoteService only): rollback con unlink (note_service.py:181-207).
3. **El documenter nunca auto-sugiere ABANDONED**: sólo CLOSED/HANDOFF; ABANDONED requiere flag explícito (reconstruction.py:362-378).
4. **`_is_required` siempre True** (reconstruction.py:399-406): todo hook cuenta como requerido hasta que `VerificationHookResult` lleve el flag — decisión explícita para no bajar la barra.
5. **Frontmatter gana sobre body** en specs legacy (spec_loader.py:50-53).
6. **Self-review informa, no bloquea** (persistence.py:19-24).
7. **Spec creation nunca falla por fallo de apertura de sesión** (spec_service.py:232-237), y la sesión se abre ANTES del episodic (razón de incidente documentada, spec_service.py:214-223).
8. **Proveedores work-items son read-only** (base.py:15) — Cortex no escribe de vuelta a Jira.

---

## 4. Bugs potenciales (con evidencia)

### B1 — `WorkItemService.get_item_note` nunca encuentra lo que `import_item` escribió (ALTO)
`service.py:81-85` busca `hu/{slug(item_id)}.md` (ej. `hu/proj-123.md`), pero el writer canónico
resuelve la ruta con el template de routing: `filename_template="HU-{external_id}.md"`
(`cortex/documentation/routing.py:290`, subfolder `hu`). El archivo real es `hu/HU-PROJ-123.md`;
el slug en minúsculas jamás coincide con `HU-<ID>` case-sensitive. `get_item_note` está roto para
todo item importado por esta misma clase. No hay ningún test de workitems que lo detecte (ver §7).

### B2 — Docstring del Reconstructor promete algo que no cumple: errores de git SÍ lanzan excepción
`reconstruction.py:148-151` dice "git errors … are surfaced as fields on the output, not as
exceptions", pero `git_module.diff/diff_name_status` (reconstruction.py:174-177) delegan en
`_run` que lanza `GitError` ante ref inválida o repo roto. Un `start_commit` corrupto rompe
`finish-session` con traceback en vez de degradar el output.

### B3 — `FinishOverrides.forced_reason` es write-only (dead field)
Se setea en 6 sitios (cli/main.py:1113,1131; autopilot/service.py:380; mcp/server.py:2548;
interactive.py:66,204,222) pero **nadie lo lee**: `finalize()` nunca lo usa ni lo persiste en la
nota. La razón de handoff que el usuario tipea en modo interactivo se descarta silenciosamente.

### B4 — Jira provider declara soporte "Cloud/Server" pero hardcodea REST v3 + ADF
`jira.py:57` usa `/rest/api/3/issue/...`; Jira Server/Data Center sólo tiene v2 y descripciones en
wiki-markup, no ADF. En Server, `_extract_description` recibiría un string wiki (ok por el branch
`isinstance(str)` de jira.py:114) pero el endpoint v3 daría 404. Además `is_configured` no distingue
Cloud de Server.

### B5 — Invariante transaccional inconsistente entre servicios
- `NoteService.create`: rollback con unlink si falla indexado (note_service.py:200-207).
- `SpecService.create`: `index_file` sin try/except (spec_service.py:209); si falla, el spec queda
  en disco sin indexar y sin rollback — viola exactamente la invariante que NoteService restauró
  en Phase 08 T8.1.
- `PRService.write_pr_docs`: fallo de indexado sólo loguea warning (pr_service.py:169-176); docs
  escritos quedan huérfanos del índice.

### B6 — Nota de sesión lleva un `session_id` aleatorio, no el id de la Session real
`NoteService.create` genera `session_id=uuid.uuid4().hex[:12]` (note_service.py:152). La nota
quedó así desvinculada del `SessionRecord.session_id` que la produjo (el persister sí conoce ese id,
persistence.py:146): rompe trazabilidad note↔session para auditoría/retrieval.

### B7 — Filtro de paths internos de Cortex es una lista de UN elemento
`_CORTEX_INTERNAL_PATHS = frozenset({".cortex/session.lock"})` (reconstruction.py:313). Cualquier
otro artefacto runtime bajo `.cortex/` (locks futuros, caches) volverá a filtrarse como
`out_of_scope` falso. Debería ser prefijo `.cortex/` (con allowlist explícita si hiciera falta).

### B8 — `diff_parser`: statuses desconocidos con 3 campos toman el path viejo
`parse_name_status` (diff_parser.py:60-72): para un status desconocido con formato
`X\told\tnew` cae al else y usa `parts[1]` (old path) como path actual. Caso raro pero posible con
versiones futuras de git; el fallback declarado ("modified") silencia la ambigüedad.

### B9 — `_extract_acceptance_criteria` convierte TODO bullet en criterio de aceptación
`jira.py:146-153`: cualquier línea `- `, `* ` o `[ ] ` de la descripción pasa a AC. Descripciones
Jira con bullets contextuales inflan las AC de la nota HU y del resumen episódico (que además las
trunca a 5, service.py:140).

Riesgos menores:
- `_scope_cross_check` compara por igualdad exacta posix (reconstruction.py:343-359): un
  `files_in_scope` con directorios (`src/`) o globs nunca matchea ⇒ falsos out_of_scope/unimplemented.
- Self-review placeholder scan incluye tokens genéricos `"???"`, `"xxx"` (persistence.py:49-51) —
  falsos positivos posibles (informativo, riesgo bajo).
- `interactive.py`: si el usuario cancela en el confirm post-EDIT (línea 213-214), las ediciones de
  título/body ya tipeadas se pierden sin aviso.
- `jira.py:_request_json` sin reintentos ni backoff (timeout fijo 15s, jira.py:71); un 429 de Jira
  sube como RuntimeError crudo al MCP.

## 5. Código muerto / duplicación

- **`_PathOnlyVault` duplicada 4 veces**: `note_service.py:41`, `spec_service.py:53`,
  `workitems/service.py:27`, `persistence.py:104` (como `_VaultPathOnly`). Mismo código copy-paste;
  debería vivir una sola vez junto a `VaultLike` en `cortex.documentation.writers` (que ya define un
  protocolo en writers.py:83).
- **`InteractiveResult.extra_notes`** (interactive.py:67): declarada, nunca escrita ni leída en todo
  el repo.
- **Doble cálculo de `_decide_status`** en `reconstruct()` (reconstruction.py:253-256 y 260-263):
  mismo resultado computado dos veces en la misma llamada; el segundo pisa al primero.
- **`InteractiveAction.HANDOFF` vs flag `--handoff` del CLI**: dos caminos que producen lo mismo;
  el CLI mezcla ambos con `verdict.forced_status or forced_status` (main.py:1128-1133). Funcional
  pero redundante.
- **ADR candidates nunca se indexan semánticamente**: `DocumenterPersister._write_adrs` usa
  `_VaultPathOnly.index_file → False` (persistence.py:104-115) y el writer trata False como no-op
  (writers.py:391-401). Las ADRs auto-generadas quedan fuera del retrieval hasta un sync manual —
  contrasta con la invariante #2 de NoteService.
- Alias deprecated `SessionService = NoteService` (services/__init__.py:30, services/session_service.py):
  deuda anunciada, con test que la vigila — correcto, pero lista para removerse en próxima major.
- Duplicación conceptual: `_STATUS_MAP` de workitems/service.py:41-44 y los mapas de acción en
  diff_parser.py:19-26 vs reconstruction.py:383-391 son tres tablas de traducción de vocabularios
  similares en el mismo subsistema.

## 6. Deudas y oportunidades de refactor

1. **Unificar el adaptador vault-path-only** (ver §5) en `cortex.documentation.writers` y exportarlo.
   Es el refactor más barato y de mayor alcance del scope.
2. **`NoteService.create` tiene 22 parámetros keyword** (note_service.py:92-116) y crece por fase
   (task_type, tasks*, gitless…). Ya existe `SessionData`: aceptarla directamente (o un
   `SessionNoteDraft`) eliminaría la capa de re-mapeo campo a campo en persistence.py:306-327.
3. **Extraer la política de indexación** (obligatoria+rollback / best-effort+warning / omitida) a una
   estrategia compartida por los tres servicios; hoy cada uno improvisa su propia semántica (B5).
4. **Persistir `forced_reason`** en la nota (campo `handoff_reason` en `SessionData`/template) o
   eliminarlo del contrato.
5. **`suggest_adrs` ignora `diff_text`** desde Phase 01 (adr_evaluator.py:63-71): o implementar las
   heurísticas de diff prometidas o reducir la firma y dejar el parámetro para cuando exista.
6. **workitems**: agregar tests unitarios (hoy cero dedicados; el grep de tests sólo matchea un
   docstring en test_documentation.py) y corregir B1 antes de que alguien use `get_item_note` en
   producción. Considerar `httpx` (ya disponible) en lugar de `urllib.request` para obtener retries
  /timeouts consistentes.
7. **`files_in_scope` con semántica de directorio/glob** en `_scope_cross_check` sería el cambio de
   mayor valor funcional para reducir falsos HANDOFF (hoy cualquier file nuevo fuera de la lista
   literal empuja a HANDOFF vía `_decide_status`).

## 7. Preparación para un cambio grande: qué tocar primero, qué es frágil

**Estado base sólido**: 113 tests unitarios de documenter+services pasan; los módulos son pequeños,
frozen dataclasses en los bordes, dependencias inyectadas, helpers puros a nivel módulo. Se puede
refactorizar con red de protección.

**Orden sugerido para un cambio grande:**
1. Primero consolidar `_PathOnlyVault` y la política de indexación/rollback (§6.1, §6.3): toca los
   tres servicios a la vez pero son cambios mecánicos con tests existentes.
2. Después arreglar los bugs de contrato: B1 (get_item_note), B3 (forced_reason), B6 (session_id),
   B7 (filtro .cortex). Todos son de superficie pequeña.
3. Sólo entonces tocar el algoritmo (`reconstruction.py`): es el archivo más frágil porque
   `ci/validator.py` importa su helper PRIVADO `_scope_cross_check` (validator.py:20) y
   `LoadedSpec`/`load_spec` (validator.py:21) — renombrar o mover esos helpers rompe CI silenciosamente
   si no se actualiza ese import. Convertirlos en API pública documentada antes de cambiarlos.

**Frágil:**
- `persistence._write_session_note` (persistence.py:192-327): 135 líneas que ensamblan ~10 listas
  paralelas (changes_made, files_touched con markers, key_decisions, next_steps, tags…) y luego
  construyen un blob aparte para self-review (`_build_draft_body_for_review`) que DUPLICA la
  composición del cuerpo sin pasar por el template Jinja real (comentario persistence.py:458-464 lo
  admite). Si cambia el template, el self-review revisa un texto que ya no es el que se publica.
- `interactive.prompt` (interactive.py:184-233): el branch EDIT anida cuatro estados en un solo
  while; añadir una acción nueva implica tocar 4 mapas/ramas. Testeable, pero al límite.
- `ReconstructionOutput` acumula 17 campos tras Phase 09; ya convive `files_touched` con la dupla
  verified/declared-only — riesgo de divergencia si otro consumidor usa el campo plano.
- `NoOpContradictionDetector` significa que STEP 5 del algoritmo es hoy un stub en todos los paths:
  el día que se conecte `cortex_search`, el contrato del Protocolo (side-effect-free, sólo lectura,
  contradiction_detector.py:62-64) debe respetarse o la idempotencia de finalize se rompe.

**Salud general: BUENA (7/10)** — arquitectura clara read/write separada, tests decentes en
documenter/services, decisiones documentadas con referencias a incidentes reales. Resta puntos: la
zona workitems (sin tests, bug B1, provider Cloud-only), la inconsistencia transaccional entre
servicios, y el campo `forced_reason`/`extra_notes` muertos que indican wiring incompleto de Phase 04.
