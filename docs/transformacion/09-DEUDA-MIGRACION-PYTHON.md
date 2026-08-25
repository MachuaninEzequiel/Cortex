# 09 — DEUDA DE MIGRACIÓN Python→Rust (estado post P0–P11)

> Fecha: 2026-08-24. Stream A, verificación integral de cierre del
> dual-stream. Complementa `08-MIGRACION-TOTAL-RUST.md`: este documento
> responde **exactamente** qué funciona hoy nativo, qué sigue dependiendo de
> Python y qué hay que portear para declarar la Obra 07 completa (P12).

## 1. Respuesta corta

**NO: todavía no es "todo Rust".** Los *motores* de memoria/recuperación/
sesiones/documenter/actions/contexto/setup están nativos y gateados byte-a-byte
(P0–P11). Pero:

1. El comando `cortex` que usa el usuario **sigue siendo el CLI Python**:
   `cortex-cli` (Rust) es una fachada passthrough decidida en G6
   (2026-08-24b) que reenvía argv con stdio heredado.
2. El servidor MCP nativo tiene catálogo+ruteo completos y transporte rmcp,
   pero los handlers de herramientas devuelven fallo explícito "backend aún
   no nativo" (solo `cortex_ping` ejecuta).
3. Quedan ~22k líneas Python en dominios sin porte (detalle §3).

## 2. Cobertura por fase (gate commiteado)

| Fase | Motor nativo | Gate byte-a-byte | Evidencia |
|---|---|---|---|
| P0 | harness parity | doctor.txt · next_stats.json | capture_golden --verify PASS |
| P1 | cortex-config | dumps config ×2 fixtures | capture_config_golden --verify |
| P2 | semantic+embed+hybrid | BM25 100/100 · semántico 100/100 rankings | search_golden recapturado idéntico |
| P3 | store episódico lectura | entries/vector/keyword/export idénticos mod-ids/ts | episodic_golden build |
| P4 | sessions/storage/verification/gates | 4 YAMLs + verification + gates | session_golden normalizado OK |
| P5 | documenter+persister | dump/note_body/create_args/summary 8/8 | documenter+persister_golden |
| P6 | cortex-actions | 16/16 salidas `next` | actions_golden verify |
| P7 | context (enricher+budget) | 3 bundles --json | context_golden verify |
| P8 | setup/templates+11 IDE+hooks | YAML 138/138+fuzz · renders/writers/ide 33/hooks 38 recapturados idénticos + 4 suites Rust | p8_*_golden + tests |
| P9 | cortex-mcp catálogo/ruteo/rmcp | list_tools byte-a-byte + ping golden | mcp_golden_contract + p9_ping |
| P10 | branding+tui | snapshot render <50ms · 27 tests | cargo test -p ambos |
| P11-ci | ci plugin (+SessionService) | 23/23 comandos `cortex ci` | ci_golden_p11 verify |

Verificación global al cierre: workspace 219 tests · clippy/fmt limpios ·
suite Python oráculo 2455 passed.

## 3. Deuda detallada por dominio (~22.1k líneas)

Ordenadas por tamaño. "Bloquea" indica qué se desbloquea al portear.

### 3.1 cli/main.py + subapps comunes — 2 995 líneas
El Typer monolítico (`main.py` 1 931) + common/_filters/_setup_helpers/
_unicode_fallback/session_tui parcial. **Hoy todo comando llega a Python.**
Porteo requerido: binario clap nivel-1 con subcomandos nativos que consuman
los crates existentes; los motores ya están, falta la capa de presentación.
Bloquea: cold start <100ms real, eliminar pipx.

### 3.2 review_knowledge + enterprise/ — 2 441 líneas
promotion_doctype (448), knowledge_promotion (338), retrieval_service (221),
reporting (218), config/governance/models/sources (~900) + CLI (215).
Dependencias entre sí + doctor + DocValidator. Spec: tests/unit/cli parciales.
Sugerido: crate `cortex-enterprise`, después de doctor (usa DoctorReport).

### 3.3 webgraph server — 2 202 líneas
relation_builder (488), service Flask→axum (288), federation (270), templates.
El **cálculo** del grafo ya es nativo (cortex-core::webgraph, medido 9.2× en
n=1000); falta exponerlo como servidor HTTP axum mínimo + endpoints de
federación. Bloquea: baja del runtime web Python.

### 3.4 mcp/tools handlers — 2 056 líneas
sessions (522), documenter (414), search (238), workspace (203) + server.py
(491) + _subprocess.py (188). El catálogo/ruteo ya está congelado (P9); cada
handler debe pasar de delegar por subprocess a llamar cortex-app in-process.
La mayoría de los backends YA existen nativos (search/sessions/documenter):
es trabajo de pegamento + wire-format exacto (nulls vs omisión rmcp, decisión
pendiente del dueño registrada por stream B). Bloquea: MCP 100% nativo.

### 3.5 context observer/telemetry/domain_detector/filters/presenter-text — 1 902 líneas
Fuera de alcance P7 por diseño (el oráculo usa observer=None y filters=None).
Entrar cuando exista el Observer nativo (requiere git watcher + telemetría
JSONL compatible) y cuando el CLI/MCP exponga filtros estructurales (Fase 08
del propio Python). async_enricher no se porta: finalize es fuente única V3.

### 3.6 autopilot/ — 1 902 líneas
service (444), policies (373), detectors/default (297), cli (354),
doctor (175), mcp_tools (181). Orquestación de alto nivel sobre sessions+
actions+context: sus dependencias ya son nativas. Spec: tests/unit/autopilot.
Sugerido: crate `cortex-autopilot` tras el CLI nativo (su CLI es sub-app).

### 3.7 pipeline/ (SDDwork runners/stages) — 1 708 líneas
runners/github (332), stages test/documentation/etc., domain/types. Ejecuta
pipelines DevSecDocOps sobre GitHub API → requiere cliente HTTP (reqwest, sin
ADR aún) o shell-out a gh. Sugerido: última ola P12.

### 3.8 tui rich vieja + session_tui — 1 081 líneas
La TUI Home nueva es ratatui (P10 ✅); queda la pantalla de sesiones rich
(session_tui 734) y tui/core (325) legados. Decisión sugerida: NO portear,
reemplazar por pantallas ratatui sobre session service nativo (ya existe).

### 3.9 workspace/layout + misc — 1 076 líneas
layout.py (564) — discovery de workspace legacy/nuevo, lo consumen tutor/
review_knowledge/CLI. Más handoff (121), git_policy (111), skills (98),
runtime_context (58), feedback_store (84 — solo escritura JSONL ya cubierta
por actions store; esta variante de lectura es chica). Portear layout temprano:
desbloquea tutor/review_knowledge/CI-commands.

### 3.10 doctor — 925 líneas
Checks pm_*/webgraph_*/enterprise/sessions sobre servicios varios. El golden
P0 congela su SALIDA pero el motor es Python. Depende de: enterprise,
webgraph-service. Sugerido: después de esos dos.

### 3.11 workitems/hu — 685 líneas
models/providers/service + CLI hu (50, Jira read-only). Depende de writers
canónicos (✅ nativos desde P8b vía cortex-setup::writers::build_note),
resolve_safe (trivial) y episodic.add — **el store nativo hoy es read-only**;
hace falta `append` (fila export + embedding ort) y reindex semántico.
Spec fina (87 líneas) pero naming canónico HU-{id}.md ya congelado.

### 3.12 pr_context + pr_capture + services/pr — 623 líneas
capture (env/git), enrich, docs generation vía PRService (episódica +
GeneratedDoc). La mejor spec de la cola (320 líneas). No depende de nada no
nativo salvo doc_generator (179, jinja ya disponible). Candidato inmediato
de portería con patrón P11-ci.

### 3.13 doc_generator/doc_validator/doc_verifier — 590 líneas
Generación/validación de docs sobre routing+jinja (ya nativo). Validator lo
consume action_engine catalog (acción quality.run_gates declarada fail
explícito hasta acá — ver decisiones P6).

### 3.14 documentation/migration (docs-migrate) — 565 líneas
Migrador de bóvedas legacy→canónicas. Solo se invoca una vez por vault;
prioridad baja.

### 3.15 services/spec_service + note_service — 541 líneas
CRUD de specs/notas sobre routing+storage. Lo consume pipeline y MCP tools.

### 3.16 tutor — 459 líneas (+403 datos topics)
engine/hint con salida rich interactiva. P6 ya porta los 7 topics como datos
para learn.topic. El resto es UI educativa: candidata a ratatui o a NO migrar
(baja prioridad, sin spec fuerte).

### 3.17 documenter/interactive — 342 líneas
Flujo interactivo de reconstrucción (rich prompts). El reconstructor no
interactivo ya es nativo (P5).

## 4. Orden de ataque sugerido para cerrar Obra 07 (P12)

1. **episodic.append + semantic.index_file/reindex** (prereq de 3.11/3.12 y
   de MCP handlers de escritura). ~150 líneas + gate round-trip.
2. **workitems/hu** (3.11) y **pr_context** (3.12): specs claras, motores
   listos, patrón P11-ci replicable.
3. **mcp/tools handlers** (3.4): pegamento in-process; wire-format nulls-vs-
   omisión requiere decisión del dueño.
4. **workspace/layout** (3.9) → desbloquea doctor/tutor/review.
5. **webgraph axum** (3.3) + **enterprise** (3.2) + **doctor** (3.10) en ese
   orden (doctor consume ambos).
6. **CLI clap nativo** (3.1): subcomandos sobre crates; flag `CORTEX_PY=1`
   de rollback; aquí se mide el cold start <100ms.
7. **pipeline + autopilot** (3.6/3.7): orquestadores de alto nivel.
8. **Baja de Python**: brain in-process, default Rust, wheels solo-Rust,
   README a binarios. Requiere 1–7 completos.

## 5. Performance medida hasta hoy (motores ya nativos)

| Aspecto | Antes (Python) | Nativo | Ganancia |
|---|---|---|---|
| Scoring path (sub-path) | baseline | suma Neumaier f64 bit-exacta | **27.6×** |
| Ingesta store v3 append-only | baseline | 13.6 ms | **3684×** |
| Cold load store | baseline | 5.0 ms | **6.4×** |
| BM25 p99 (casero ADR-BM25) | — | 1.85 ms (≤2ms) | ranking bit-idéntico 200/200 |
| Webgraph n=1000 | baseline | 255–276 ms aislado | **9.2×** |
| Embeddings ONNX (ort) | onnxruntime | cos=1.00000000 · batch 2.1–2.2× · first_query_cold **20.8×** | paridad 1.0 |
| TUI Home render (ratatui) | rich | <50 ms snapshot | latencia objetivo cumplida |
| Arranque comando | ~900 ms imports Python | fachada nativa + Python debajo | pendiente <100 ms real (requiere 3.1) |

Mediciones fuente: COMPARE/evidencias de Obra 03 (G1–G5) y Obra 07
(P2/P10); ver bench/results/*.json.

## 6. Regla vigente

Mientras cualquier componente exista en ambos lados, la suite Python completa
sigue siendo EL ORÁCULO (2455 passed al cierre de esta verificación). Drift
visible ⇒ revert. Ninguna baja de código Python antes del punto 8 de §4.

## 7. Ejecución P12 en DUAL-STREAM (activa 2026-08-24)

Dos agentes en paralelo sobre el MISMO working tree, mismo modelo que §4b
de 08-MIGRACION. Territorios por CRATE (no por archivo suelto):

| Stream | Nombre | Crates/archivos PROPIOS | Contenido (~LOC py) |
---|---|---|---|
| **A** | contenido-y-escritura | `rust/crates/cortex-app/` (extensiones episodic.append, semantic reindex, workitems, pr, context extras, documenter/interactive), `rust/crates/cortex-mcp/src/server.rs` handlers, NUEVO `rust/crates/cortex-services/` | prereq escrituras (~200) · workitems/hu (685) · pr_context+capture+pr_service (623) · doc_generator/validator/verifier (590) · spec/note services (541) · docs-migrate (565) · context observer/telemetry/domain/filters/presenter-text (1902) · documenter/interactive (342) · mcp tools handlers (2056) ≈ **9.5k** |
| **B** | dominios-e-integración | NUEVOS crates: `cortex-workspace`, `cortex-webgraph-server` (axum), `cortex-enterprise`, `cortex-doctor`, `cortex-autopilot`, `cortex-pipeline`; reescritura de `rust/crates/cortex-cli/` | workspace/layout+misc (1076) · webgraph server (2202) · enterprise/review_knowledge (2441) · doctor (925) · autopilot (1902) · pipeline SDDwork (1708) · tutor decisión (862) · CLI clap nativo (2995) ≈ **13k** |

### 7.1 Dependencias cruzadas (quién bloquea a quién)

1. A#1 (episodic.append + semantic.reindex + security::resolve_safe en
   cortex-app) es PREREQ de A#2/#3 y de los handlers MCP de escritura.
   B NO toca cortex-app: consume read-only (dep normal en Cargo).
2. B: layout → {doctor, review_knowledge, tutor}; webgraph-service →
   doctor; enterprise → doctor (DoctorReport). Orden interno B respeta eso.
3. El CLI nativo (B, ÚLTIMO en su orden) wirea subcomandos de AMBOS lados:
   los comandos con motor de A requieren el estado merged del trunk. Es EL
   punto de sincronización final de P12.
4. Los handlers MCP de escritura (A) dependen de la DECISIÓN DEL DUEÑO sobre
   wire-format rmcp (nulls explícitos vs omisión): mientras no llegue,
   A avanza con el resto y deja esos handlers con fallo explícito actual.
5. tutor (B): decisión del dueño pendiente — porte fiel vs reemplazo
   ratatui vs no migrar. Por defecto: NO portear ciego; documentar.

### 7.2 Reglas duras P12 (extienden §R5)

1. Cada stream toca SOLO sus crates. cortex-app lo edita exclusivamente A;
   B lo consume como dependencia. cortex-cli lo edita exclusivamente B.
2. `rust/Cargo.toml` raíz y `Cargo.lock`: compartidos — edits quirúrgicos
   append-only de TU member/deps; tras editar validar
   `cargo metadata -q >/dev/null`. Al commitear, incluirlos SOLO si el diff
   corresponde íntegramente a tus crates; si hay hunks ajenos sin commitear
   del otro stream, no los stages (esperar/reintentar). Ante `index.lock`
   ocupado: esperar 2s y reintentar.
3. Verificación SIEMPRE por crate (`cargo test -p <crate>`); el global se
   corre solo en la integración final. Suite Python completa = ORÁCULO
   compartido y debe seguir verde en cada commit.
4. Un gate byte-a-byte por componente portado (patrón capture_golden/
   *_golden.py + example/checker Rust, normalizaciones pactadas
   {{ROOT}}/{{MS}}/{{TS}}/{{DATE}}). Los scripts nuevos: A usa
   `bench/parity/*p12a*`, B usa `bench/parity/*p12b*`.
5. Commits atómicos prefijados `feat(obra07 P12A…)` / `feat(obra07 P12B…)`,
   un gate por commit, git add SOLO de archivos propios.
6. Progreso: A escribe SOLO `docs/transformacion/progreso-p12a.md`, B SOLO
   `docs/transformacion/progreso-p12b.md`. NINGUNO toca ESTADO-ACTUAL.md ni
   HANDOFF.md ni este documento (integración final posterior).
7. Backends no porteados aún ⇒ fallo EXPLÍCTICO documentado (patrón P6/P9);
   jamás fingir paridad conductual.
8. Sin deps nuevas sin ADR chico (reqwest para pipeline/github queda
   aprobado si B lo necesita; axum ya aprobado).

### 7.3 Criterio de cierre de P12

Ambos streams completos + CLI nativo wireando todos los subcomandos +
suite Python oráculo verde + `cargo test --workspace` verde + medición
cold-start <100ms documentada ⇒ recién ahí procede la baja de código Python
(último paso de §4) y el refresco final de ESTADO-ACTUAL/HANDOFF.
