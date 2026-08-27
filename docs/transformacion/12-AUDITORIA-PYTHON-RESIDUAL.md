# 12 — AUDITORÍA PYTHON RESIDUAL

> Fecha: 2026-08-25. **RE-AUDITADO post-cierre P12** (ver §9): P12A-9,
> P12B-7 y P12B-8 commiteados (`42eedd8` · `0e6b936`+`600cc04` · `2f8a64b`).
> **DEPRECIACIÓN EJECUTADA el 2026-08-25**: cortex/brain Python,
> embedders/openai.py, hooks/agent_hooks.py (docstrings+warning),
> MagicMock/ ELIMINADO (~20 MB). Ver §9 para el registro oficial.
> Auditoría exhaustiva línea-por-línea del árbol `cortex/` (51 404 LOC
> Python totales) cruzada contra los crates Rust y los gates P0–P12.
> Propósito: mapa EXACTO de lo que falta para declarar la baja definitiva
> de Python, y decisiones que el dueño debe tomar al respecto.
> Complementa (y ACTUALIZA) `09-DEUDA-MIGRACION-PYTHON.md`, escrito al
> cierre de P11 cuando quedaban ~22k LOC; los streams P12 redujeron eso
> drásticamente.

## 1. Resumen ejecutivo

| Categoría | LOC py aprox | Situación |
|---|---|---|
| **Portado CON GATE byte-a-byte** (P0–P11 + P12A-2..8 + P12B-1..6) | **~43 000** | ✅ motores nativos verificados |
| En curso AHORA mismo (streams activos) | ~2 900 | P12A-9 mcp handlers · P12B-8 CLI clap |
| **Residual real tras cerrar P12** | **~5 300** | detalle §3 |
| Decisión del dueño pendiente (porte/baja/reemplazo) | ~1 400 | detalle §4 |
| Infraestructura que NO se migra (oráculo/herramientas) | ~1 800 | detalle §5 |

La respuesta a "¿qué Python queda?" después de P12: **~6 700 LOC**, de las
cuales solo ~5 300 son porte mecánico directo y ~1 400 son decisiones de
producto, no de migración.

## 2. Matriz de cobertura por dominio (verificada contra código real)

| Dominio Python | LOC | Destino Rust | Gate | Estado |
|---|---|---|---|---|
| core.py (config pydantic) | 1 065 | cortex-config | P1 dumps ×2 | ✅ |
| semantic/{vault_reader,chunker,parser,vector_cache} | ~2 500 | cortex-app/semantic + cortex-core + cortex-embed | P2 BM25/sem 100/100 | ✅ |
| episodic/memory_store.py | 469 | cortex-app/episodic (+append P12A-1) | P3 round-trip 12/12 | ✅ |
| session/{service,models,storage} | ~1 350 | cortex-app/session | P4 dumps/gates/infer | ✅ |
| documenter/{reconstruction,persistence} | ~970 | cortex-app/documenter | P5 byte-parity | ✅ |
| action_engine/ + feedback_loop.py | ~1 840 | cortex-actions | P6 next 16/16 | ✅ |
| context_enricher/enricher+budget | ~700 | cortex-app/context | P7 bundles ×3 | ✅ |
| context extras {observer,telemetry,domain_detector,filters,presenter,intent,doc_intent,co_occurrence,decay} | ~2 600 | cortex-app/context/* | P12A-7 | ✅ |
| setup/{templates,orchestrator,cold_start,detector,routing,writers} | ~3 200 | cortex-setup | P8 YAML 138+fuzz | ✅ |
| ide/adapters ×11 + base + registry + canonical_tools + prompts | ~4 230 | cortex-setup/{ide,routing} | P8 ide 33/33 | ✅ |
| hooks/ session-hooks (install) | parte | cortex-setup/session_hooks | P8 hooks 38/38 | ✅ (runtime: §4.5) |
| mcp/{server,schemas,_subprocess} catálogo+ruteo | ~1 800 | cortex-mcp | P9 list_tools byte-a-byte | ✅ |
| tui Home nueva | — | cortex-tui (ratatui) | P10 <50ms | ✅ |
| branding/paleta/wordmark | — | cortex-branding | P10 snapshot | ✅ |
| ci/ completo {result,validator,review_session,session_matcher,diff_io,markdown_formatter} | ~1 300 | cortex-app/ci (1 672 rs) | P11-ci 23/23 | ✅ |
| workitems/hu | 685 | cortex-app/workitems | P12A-2 | ✅ |
| pr_context + pr_capture + pr service | 623 | cortex-app/pr | P12A-3 | ✅ |
| documentation/{routing,doc_generator,validator,verifier} | ~1 000 | cortex-app/{semantic/routing,doc_*} | P12A-4 | ✅ |
| services/{spec_service,note_service} | 541 | cortex-services | P12A-5 | ✅ |
| documentation/migration (docs-migrate) | 565 | cortex-services/migration | P12A-6 | ✅ |
| documenter/interactive | 342 | cortex-app/documenter | P12A-8 | ✅ |
| workspace/{layout,handoff,git_policy,skills,runtime_context} | 952 | cortex-workspace | P12B-1 byte-parity | ✅ |
| webgraph/ (cálculo+server+federation) | ~1 400 | cortex-core::webgraph + cortex-webgraph-server | Obra03 9.2× + P12B-2 | ✅ |
| enterprise/review_knowledge | ~2 440 | cortex-enterprise | P12B-3 byte-parity | ✅ |
| doctor.py | 925 | cortex-doctor | P12B-4 byte-parity | ✅ |
| autopilot/ capa de decisión | ~1 100 | cortex-autopilot | P12B-5 doctor-gate | ⚠️ parcial (§3.4) |
| pipeline/ SDDwork | ~1 700 | cortex-pipeline | P12B-6 byte-parity | ⚠️ parcial (§3.5) |

## 3. Residual REAL tras cerrar P12 (~5 300 LOC)

### 3.1 cli/main.py + subapps comunes — 1 931 + ~1 064 = 2 995 LOC → **P12B-8 (en cola)**

main.py 1 931 · session.py 845 (la PARTE no-TUI) · common/_filters/
_setup_helpers/_unicode_fallback/docs_search/docs_subcommand/
docs_vectorization/embedding/mcp_cmd/next/review_knowledge/ide/cli.
Es EL bloque que desbloquea cold-start <100 ms y la baja de pipx.
Territorio B. Sin este porte, TODO lo demás corre pero solo vía passthrough.

### 3.2 mcp/tools handlers in-process — ~2 056 LOC → **P12A-9 (EN CURSO)**

sessions 522 · documenter 414 · search 238 · workspace 203 · server glue.
**DESBLOQUEADO HOY**: la decisión wire-format §4.8 fue firmada por el dueño
(doc 11 Anexo A / HANDOFF §4.8): omisión rmcp canónica + equivalencia
estructural. Handlers de escritura ya pueden portearse.

### 3.3 TUI rich legada — ~1 081 LOC → decisión ya tomada: REEMPLAZO ratatui

cli/session_tui.py 734 + tui/core.py 325 + tui/__init__. La decisión
registrada en doc 09 §3.8 es NO portear: reemplazar por pantallas ratatui
sobre SessionService nativo (ya existe). **Falta construir el reemplazo**
— no hay tarea abierta para ello. Propuesta: incorporarlo a P13 como
tarea opcional del stream B (pantalla sesiones ratatui), o posponer a P14.

### 3.4 autopilot service/cli/mcp_tools — ~800 LOC faltantes de los 1 902

P12B-5 portó la CAPA DE DECISIÓN (models/policies/detectors/lifecycle,
gateada vía doctor). Quedan service (444) + cli (354) + mcp_tools (181),
que dependen del motor de sesiones nativo expuesto por CLI/servicios.
Orden natural: DESPUÉS de P12B-8. Fallo explícito vigente mientras tanto.

### 3.5 pipeline Documentation stage — stub

P12B-6 portó todo menos la stage Documentation, stub hasta que exista
AgentMemory/documenter expuesto por servicios nativos. Pequeña; se cierra
con el CLI nativo.

## 4. Decisiones del dueño pendientes (NO son porte mecánico)

### 4.1 tutor/ — 862 LOC — ✅ RESUELTO EN P12B-7: SE PORTÓ FIEL

El stream B desmontó el "NO portear ciego" del doc 09: dependencias reales
eran layout + contenido estático. Porte byte-parity commiteado (`0e6b936`,
gate `tutor_golden_p12b.py`). El tutor Python queda como ORÁCULO del gate
(no tocar su runtime); es candidato natural a baja en la limpieza final.

### 4.2 cortex/brain/ Python — 424 LOC — ✅ DEPRECATO (EJECUTADO 2026-08-25)

Docstrings DEPRECATED agregados en __init__/chat/router/tools/cli apuntando
al brain oficial Rust. SIN warning runtime a propósito: main.py lo importa
en cada arranque y el passthrough del CLI nativo debe permanecer byte-idéntico.
Borrado físico: ventana de baja definitiva (es oráculo de tests/unit/brain).

### 4.3 embedders/openai.py — 88 LOC — ✅ DEPRECATO (EJECUTADO 2026-08-25)

Docstring deprecated + `DeprecationWarning` en `OpenAIEmbedder.__init__`
(seguro: ningún golden lo instancia; verificado `tests/unit/embedders` 24
passed post-cambio). Recomendación mantenida: NO migrar; migrar configs a
`embedding.backend: onnx`; baja física con Python.

### 4.4 hooks/agent_hooks.py — 154 LOC — ✅ CONFIRMADO HUÉRFANO Y DEPRECATO

Verificado: cero referencias en templates/, setup/, IDE adapters ni tests.
Docstring deprecated agregado. Los hooks vigentes son cortex/setup/session_hooks
(gate P8 38/38). Baja física con Python.

## 5. Fuera del paquete — NO migrar (infraestructura)

| Elemento | Qué es | Decisión |
|---|---|---|
| bench/parity/*_golden*.py | ORÁCULOS de paridad build/verify | Se mantienen Python hasta la baja final (regla HANDOFF); luego archivar |
| tests/unit + tests/integration | ORÁCULO 2455 passed | Ídem |
| scripts/{build_sandbox,devsecdocops.sh,gen_queries_eval,benchmark_handoff_overhead} | herramientas de desarrollo | Permanecen shell/Python: no son producto |
| eval/retrieval | suite MRR de calidad de embeddings | Permanece (mide calidad, no corre en producción) |
| **MagicMock/mock.workspace_root** (~20 MB) | artefacto basura de tests | ✅ **ELIMINADO físicamente 2026-08-25** (cero referencias verificadas antes del borrado) |
| cortex_memory.egg-info/, uv.lock, progress.md | artefactos de build/scratch | Limpieza de untracked pendiente (HANDOFF §6) |

## 6. Tests rotos PREEXISTENTES del trunk (no culpa de P12, pero es deuda)

32 fallos + 3 errores en e2e (setup/autopilot/tui/artefact_integrity):
el commit de "recatorización" borró módulos que esos tests importan.
**Acción recomendada**: tarea de limpieza post-P12 — actualizar o retirar
esos tests e2e para recuperar el oráculo 100 % verde ANTES de la baja de
Python (un oráculo roto no puede validar la última fase).

## 7. Orden recomendado hasta la baja definitiva

1. **Cerrar P12** (en curso): P12A-9 (desbloqueado hoy) + P12B-7 decisión +
   P12B-8 CLI clap nativo.
2. **P13 Companion Engine** (spec completa: doc 11) — puede correr en
   paralelo con 3/4/5 si el dueño prefiere; no compite por territorios.
3. Limpiezas: MagicMock + untracked + tests e2e rotos (§6) + baja
   cortex/brain Python (§4.2) + deprecación openai backend (§4.3).
4. Reemplazo ratatui de session_tui (+ tutor si se decide) (§3.3/§4.1).
5. autopilot service/cli/mcp_tools + pipeline Documentation stage (§3.4/3.5).
6. **Baja definitiva de Python**: CORTEX_PY=1 pasa a rollback histórico,
   wheels solo-Rust, README a binarios, goldens archivados.

## 8. Nota metodológica

Cada fila de §2 fue verificada contra existencia real del módulo Rust y su
registro de gate. LOC por `wc -l`. Correspondencia funcional 1:1 según
gates byte-parity, no textual.

## 9. RE-AUDITORÍA post-P12 + registro de depreciación ejecutada

### 9.1 Cierre real de P12 (verificado en git log al 2026-08-25)

| Tarea | Commit | Alcance honesto |
|---|---|---|
| P12A-9 mcp handlers | `42eedd8` | SOLO familia sesiones in-process (12 handlers, gate S01–S22 byte-a-byte). Resto de rutas MCP mantiene fallo explícito |
| P12B-7 tutor | `0e6b936` | Porte fiel byte-parity (opción A) |
| P12B-8 CLI clap nativo | `2f8a64b` | 11 subárboles wireados nativos; resto PASSTHROUGH al CLI Python. Cold start medido: 1 ms vs 699 ms (~700×) |

### 9.2 Brecha restante tras P12 (NO deprecable — porte pendiente real)

> **Estado post-cierre (2026-08-26): los ítems 1–6 fueron resueltos por la
> Obra 07 (cierre T1–T7) + RUTA 1 de la baja definitiva (session task/hooks,
> remember/forget, ide, docs validate/restore/list-backups/routing-table).**
> El passthrough de `cortex-cli` quedó reducido al rollback `CORTEX_PY=1` +
> solo leaves "de diseño" documentados (hu import, webgraph serve/doctor,
> autopilot doctor/install/uninstall) — ver §9.4 y
> `PROMPT-BAJA-DEFINITIVA-RUTA1.md`.

1. **Subcomandos CLI no-wireados**: ✅ RESUELTO. Wireados nativos
   (commits T2/T2-cola `c210cef`→`16bb8b7`, gate `cierre_cli_golden`
   39 casos + MCP stdio bounded exchange; RUTA 1 baja: session task ×5 +
   hooks ×4 + remember/forget + ide ×4 + docs validate/restore/
   list-backups/routing-table, gates `cierre_leaves_a_golden` 33 casos +
   `cierre_leaves_b_golden` 26 casos): search/context/stats/reindex/
   next/session ×14/hu ×2/pr-context ×5/docs ×6/ci ×4/setup ×5/mcp-serve/
   ide ×4/remember/forget.
2. **Handlers MCP no-sesión**: ✅ RESUELTO (T1 `21536f5`, gate
   `cierre_mcp_golden` 51 escenarios byte-a-byte).
3. **autopilot service/cli/mcp_tools** (~800): ✅ RESUELTO (T3-paralelo
   `e089a25`, gate `cierre_autopilot_golden` + `cierre_autopilot_check`).
4. **pipeline stage Documentation**: ✅ RESUELTO (T4 `65c5a40`, nativo
   DocVerifier + SessionService + persister; gate `pipeline_golden_p12b`
   3 casos Documentation + flows A–D).
5. **TUI rich vieja**: ✅ RESUELTO. Pantalla ratatui + integración CLI
   `session watch/tui` (T6-paralelo `fa11473` + T6-b `9d4de37`, 5 + 3 tests).
6. **32F+3E tests e2e rotos preexistentes**: ✅ RESUELTO (T5 `f6fb828`,
   oráculo 100% verde: 2552 passed, 0 failed, 0 errors).

### 9.3 Registro oficial de depreciación EJECUTADA (2026-08-25)

| Archivo/módulo | Acción | Seguridad verificada |
|---|---|---|
| `MagicMock/` (~20 MB) | BORRADO físico | cero referencias grep previas |
| `cortex/embedders/openai.py` | docstring deprecated + `DeprecationWarning` en `__init__` | ningún golden lo instancia; tests/unit/embedders 24 passed post-cambio |
| `cortex/hooks/agent_hooks.py` | docstring deprecated (huérfano confirmado) | cero referencias en templates/setup/adapters/tests |
| `cortex/brain/{__init__,chat,router,tools,cli}.py` | docstrings DEPRECATED | SIN warning runtime a propósito (main.py importa al arrancar; passthrough debe seguir byte-idéntico); tests/unit/brain verdes |
| `cortex/tutor/**` | ORACLE-ONLY documental | es oráculo activo del gate P12B-7: NO tocar runtime |

Regla aplicada: depreciación = marcado formal + plan de baja, NUNCA borrado
de código vivo del oráculo. La baja física total es el punto 7 de §7 y
requiere §9.2 resuelto + oráculo 100 % verde.

### 9.4 Resumen oficial de CIERRE OBRA 07 (2026-08-26)

**OBRA 07 — CIERRE COMPLETO.** Los seis ítems de §9.2 fueron resueltos por
el cierre T1–T7; el oráculo quedó 100% verde. Métricas finales:

- Oráculo Python: **2552 passed, 21 skipped, 0 failed, 0 errors** (primera
  vez verde desde la recatorización; T5 `f6fb828`).
- CLI nativo wireado: search, context, stats, reindex, next, session ×9
  (current/checkpoint/switch/diff/abandon/list/show/watch/tui), hu ×2,
  pr-context ×5, docs ×2, ci ×4, setup ×5, mcp-server/mcp-serve
  (`cierre_cli_golden` 39 casos + MCP stdio bounded exchange).
- Familias MCP in-process: search/context/sync_ticket, write_doc ×11 + design
  + HU, spec/proposal/governance/gap, finish/briefing (T1 `21536f5`, 51
  escenarios).
- Autopilot service + cli + tools MCP ×5 (T3-paralelo `e089a25`).
- Pipeline Documentation nativo (T4 `65c5a40`, P5 persister/reconstructor).
- Pantalla sesiones ratatui + `session watch/tui` (T6 `fa11473` + T6-b
  `9d4de37`).
- Cold start release N=20: livianos 2–9 ms (<100 ms); memoria/ONNX
  (pr-context store/search/full) ~308–366 ms (reporte honesto, no
  debilitado). RUTA 1: task list 3.6 ms · hooks list 2.4 ms · ide 2.5–4.2 ms
  · docs 2.6–6.4 ms; remember 186.7 ms / forget 117.4 ms (ONNX honesto).

### 9.5 RUTA 1 de la baja definitiva — wireado leaves "solo alcance" (2026-08-26)

**BAJA DEFINITIVA — RUTA 1 COMPLETA.** Dos mitades en paralelo (A/B) sobre
el mismo árbol, territorios disjuntos (matriz en
`PROMPT-BAJA-DEFINITIVA-RUTA1.md`):

- **MITAD A** (`14bfcfd` + fix `24885b8`): `session task` ×5
  (list/done/in-progress/skip/block, portes `SessionService::list_tasks`/
  `update_task_status`), `session hooks` ×4 (glue `HookInstaller` nativo),
  `remember`/`forget` (portes `NativeEpisodicStore::delete`,
  `ensure_ascii=False` local). Gate `cierre_leaves_a_golden` **33 casos**
  (188 líneas, ≥2 reales por subcomando, non-ASCII incluido).
- **MITAD B** (`ebc0cad` + fix `6934564`): `ide` ×4 (list/setup/remove/
  status sobre `cortex-setup::ide` + HookInstaller), `docs validate`
  (validate_vault nativo), `docs restore`/`list-backups` (portes
  `list_backups`/`restore_backup` tar en migration), `docs routing-table`
  (RouteSpec completo, 13 doc_types). Gate `cierre_leaves_b_golden`
  **26 casos** (554 líneas). Divergencias doc-vs-oráculo resueltas a favor
  del oráculo (setup/remove sin hooks, ide list sin --project-root,
  list-backups sin --json).
- Verificación: fmt/clippy `-D warnings` ✓ · cargo test cortex-cli 73/0 +
  cortex-app 105/0 ✓ · gates A+B build/verify PASS ✓ · oráculo Python
  **2552 passed, 21 skipped, 0F 0E** bajo lock (120 s) ✓.
- Revisión por tarea (spec+quality) y fix rounds: ambas Approved tras ronda
  1/5 (quota de gate y ensure_ascii corregidas).

Passthrough residual AHORA (solo leaves "de diseño", pendientes de ruta 2):
`hu import` (excepción no portable), `webgraph serve/doctor` (server axum),
`autopilot doctor/install/uninstall` (instaladores interactivos). La decisión
de archivo/borrado de Python y goldens queda pendiente del dueño.

Registros del paquete: `progreso-baja-a.md` (mitad A) y
`progreso-baja-b.md` (mitad B). Este archivo debe leerse junto a
`ESTADO-ACTUAL.md` y `HANDOFF.md` (actualizados en T7 y RUTA 1).

### 9.6 RUTA 2 de la baja definitiva — leaves "de diseño" (2026-08-26)

**BAJA DEFINITIVA — RUTA 2 COMPLETA.** Dos mitades en paralelo (A/B) sobre
el mismo árbol, territorios disjuntos (matriz en
`PROMPT-BAJA-DEFINITIVA-RUTA2.md`):

- **MITAD A** (`5ad44ab` + fix `f53bdc6`): `autopilot doctor` nativo (port
  exacto de run_diagnosis: payload {project_root, ok, checks, warnings} en
  orden del oráculo, 6 checks config/sessions_dir/adapters/hooks/
  last_finish/service sobre WorkspaceLayout/SessionStorage/HookInstaller/
  AutopilotService; rc 0 como el oráculo; tie-break de last_finish =
  primer-máximo como max(key=) de Python). `autopilot install/uninstall`:
  ELIMINADOS en Fase 04 del oráculo (cli.py:352) — rechazo nativo
  "No such command" rc=2 SIN Python (centinela CORTEX_BIN probado),
  passthrough intacto para el resto. Gate `cierre_leaves2_a_golden`
  5 casos byte-parity + 2 equivalencias Fase 04 (115 líneas).
  Cold start N=20 avg 2.6 ms.
- **MITAD B** (`b62b0e1`): `webgraph serve` nativo (wrapper `create_app`
  axum P12B-2 + `run_server`; host/port de config, `--no-open` no-op
  documentado; smoke no-terminal P12B-2), `webgraph doctor` (5 checks
  byte-parity + resumen stdout/stderr + rc 1), `hu import` (glue
  `WorkItemService::import_item` + `JiraProvider` port de jira.py con
  fetch `file://` hermético). Gate `cierre_leaves2_b_golden`
  5 casos + smoke serve + 2 equivalencias S19. Cold start N=20:
  doctor 2.0 ms · hu 2.5 ms · serve 55 ms.
- Verificación: fmt/clippy ✓ · cargo test cortex-cli ✓ · gates A+B
  build/verify PASS ✓ · oráculo **2552 passed, 21 skipped, 0F 0E** bajo
  lock ✓. Revisión por tarea + fix round 1/5 (A) — ambas Approved.

**DEUDA DOCUMENTADA (no bloqueante, fuera del alcance del paquete):**
`hu import` con base_url http(s) real NO tiene cliente HTTP nativo (regla
Cargo congelado del paquete) → error equivalente documentado; el gate usa
`file://` hermético. Un servidor Jira real requiere un ADR de dependencias
(cliente HTTP) en una tarea futura. `webgraph_dependencies` del doctor es
no-op "ok" fuera del venv del gate.

**Passthrough de `cortex-cli` AHORA = SOLO rollback `CORTEX_PY=1`.**
La decisión de archivo/borrado de Python y goldens queda pendiente del
dueño (paquete separado). Registros: `progreso-baja-2a.md` y
`progreso-baja-2b.md`.

### 9.7 FASE FÍSICA de la baja definitiva — passthrough eliminado (2026-08-27)

**BAJA DEFINITIVA — FASE FÍSICA COMPLETA.** Paquete `PROMPT-BAJA-FISICA.md`
(commit `a61122c` + `27410dc` + `9611f69`), revisado y Approved:

- **`CORTEX_PY=1` → rollback HISTÓRICO**: main.rs imprime aviso ("CORTEX_PY=1
  es rollback histórico de la migración — el CLI es 100% nativo; eliminá la
  variable") y continúa el flujo nativo. Ya NO delega.
- **Catch-all eliminado**: comando desconocido → `No such command '<cmd>'.`
  rc 2 (contrato Typer). Módulo `fallback.rs` ELIMINADO.
- **`reindex` real → fallo explícito P6/P9** rc 1 (no existe escritor de
  vector-cache persistente nativo); `--dry-run` sigue nativo.
- **`init` → alias nativo** de `setup agent` (único flag `--non-interactive`,
  oráculo main.py:796-806).
- **Subtrees internos**: todos los `=> false` de fall-through eliminados
  (autopilot/webgraph/ide/session/ci/docs/pr-context/setup/memory-report)
  con taxonomía consistente: comando desconocido rc 2 / feature no-wireada
  (reindex real, --telemetry, export federado) rc 1 con mensaje explícito.
- **Goldens ARCHIVADOS**: ~40 `*_golden*.py` + dirs golden*/.p12b-*/.p12-*
  → `bench/parity/archive/` con `README-archivo.md` histórico (qué
  validaban, cómo reactivar). Ningún workflow de CI los corre (re-verificado).
- **README a binarios**: instalación `cargo install --path
  rust/crates/cortex-cli`; wheel Python = legado congelado (oráculo CI vivo,
  no distribución). README.md + README.es.md.
- Verificación: fmt/clippy workspace `-D warnings` ✓ · `cargo test
  --workspace` 83/83 ✓ · oráculo Python **2552 passed, 21 skipped, 0F 0E**
  bajo lock ✓ · smokes manuales (bogus rc 2, CORTEX_PY=1 aviso+nativo,
  reindex rc 1, init help) ✓.
- Revisión del diff: Approved (zero Critical/Important; minors cosméticos
  de mensajes con ruta de revert documentada).

**Resultado: el CLI nativo NO ejerce NINGÚN passthrough a Python.** Queda
solo para el dueño (fuera del repo): decisión de borrado físico de
`cortex/`+`tests/`+`pyproject.toml` (si algún día se quiere — hoy son el
oráculo vivo de CI) y publicación de wheels solo-Rust (release, no repo).
