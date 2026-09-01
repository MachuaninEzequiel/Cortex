# Obra 01 — Podado y limpieza total

> Estado: PLAN COMPLETO · Planificador: plan-cleanup · Fecha: 2026-08-21
> Origen: deep-review 2026-08 (docs/reviews/2026-08-deep-review/) + inventario con vulture/ruff.
> Ejecutable por otro agente sin preguntar nada. Regla de oro: **cada fase = 1 commit separado + suite verde**.

## Criterio de entrada
- [ ] TRAMO 0 completo (ver §3): suite verde, pin mcp resuelto, gates propios en CI.
- [ ] `uv run pytest` sale 0 en el repo tal como está al arrancar la obra.

## Criterio de salida
- [ ] `vulture cortex --min-confidence 80` + `ruff check --select F401,F841`: 0 hallazgos confirmados como muertos (lo restante justificado en este doc).
- [ ] Duplicaciones del review eliminadas: server.py partido, main.py adelgazado, enricher sync/async unificado, embedders en un solo stack, schemas únicos, _PathVault único, devsecdocops x2 → x1, strings embebidos extraídos a archivos con test de sincronía.
- [ ] Bugs top del review corregidos o descartados con razón explícita (tabla §4).
- [ ] Dependencia circular session↔documenter rota.
- [ ] requirements.txt eliminado o regenerado desde pyproject (fuente única).
- [ ] Suite verde + cobertura no menor a la línea base (75%).

## §1 Inventario de código muerto REAL

Herramientas corridas (2026-08-21):
- `uvx vulture cortex --min-confidence 80` → **2 hallazgos**.
- `uvx ruff check --select F401,F841 cortex tests` → **5 hallazgos** (1 en cortex/, 4 en tests/).
- Nota: vulture con `--min-confidence 60` da ~368 líneas pero casi todo son falsos positivos
  (comandos click registrados por decorador, `model_config` de Pydantic, campos de config).
  NO podar por confianza 60 sin verificar caller con grep.

### 1.1 Hallazgos de herramientas → clasificación

| Ítem | Ubicación | Clasificación | Acción |
|---|---|---|---|
| unused var `no_graph` | cortex/cli/main.py:800 | BORRAR SEGURO | quitar asignación; el flag ya no se usa |
| unused var `only_agent` | cortex/setup/orchestrator.py:224 | BORRAR CON TEST | verificar que la opción CLI asociada esté documentada antes de tocar |
| unused var `layout` | cortex/webgraph/cli.py:114 | BORRAR SEGURO | `_discover_layout(root)` se llama solo por side-effect? verificar: si descubre layout y el resultado se necesita abajo, es bug de flujo, no dead code → INVESTIGAR primero |
| F841 `original_config` | tests/e2e/scenarios/test_setup_on_fixtures.py:84 | BORRAR CON TEST | borrar o usar para aserción real |
| F841 `content` | tests/e2e/test_artefact_integrity.py:51 | BORRAR CON TEST | idem |
| F841 `real_resolve` | tests/unit/documentation/test_writers_defensive.py:188 | BORRAR SEGURO | asignación residual de un stub |
| F841 `src` | tests/unit/enterprise/test_maintenance.py:197 | BORRAR CON TEST | probablemente falta aserción sobre `src`; revisar intención del test |

### 1.2 Código muerto confirmado por el review (contraste)

De [1-core-entrypoints.md](../reviews/2026-08-deep-review/1-core-entrypoints.md) §5:

| Ítem | Ubicación | Clasificación | Acción |
|---|---|---|---|
| `is_known_agent` + `_KNOWN_AGENTS` (solo tests) | handoff.py:65-74,136-138 | BORRAR CON TEST | borrar función+constante+su test |
| `_meets_adr_criteria` ("for future use") | doc_generator.py:184-210 | BORRAR SEGURO | declaradamente no usado |
| `FeedbackEnricherIntegration`, `parse_github_reaction` (0 callers en cortex/) | feedback_loop | ~~BORRAR CON TEST~~ SKIP | Reservado: feedback_loop es pieza dormida de Obra 05 (HANDOFF decisión #5) — NO podar |
| `DocVerifier._git_diff_files` | doc_verifier.py:179-186 | BORRAR SEGURO | solo se usa `_git_diff_status` |
| `MemoryDecay.apply_to_hits/get_stats`, `ScoringWithDecay`, `create_decay_config` | memory_decay | PODADO en P2 | Podado en fase P2 (ver §7); se conservó `calculate_decay_factor`. Bug #9 (`__post_init__` ignora decay_rate configurado) sigue pendiente para P6/Obra 04 |
| `DecayConfig.max_multimatch_boost` nunca leído | memory_decay.py:54 | BORRAR SEGURO | boost real hardcodeado en ScoringWithDecay:337-342 |
| `time.monotonic()` descartado + `if TYPE_CHECKING: pass` | pipeline/orchestrator.py:90,29-30 | BORRAR SEGURO | trivial |
| ramas elif muertas en parser git log | setup/cold_start.py:196-235 | BORRAR SEGURO (rama) + BUG aparte | el parser frágil es bug #11-setup, no poda |

De otros informes:

| Ítem | Ubicación | Clasificación | Acción |
|---|---|---|---|
| `NoActiveSession` definida/exportada, nunca levantada | session/errors.py (+__init__) | BORRAR CON TEST | la real es `autopilot.errors.NoActiveSessionError`; borrar clase+export+test_errors |
| `_SessionFields` muerto | documentation/schemas/session.py:31-40 | BORRAR SEGURO | las clases duplican campos inline (se unifica en §2 schemas) |
| `_SUBFOLDER_TO_DOC_TYPE` + `_ADR_FILENAME_RE` obsoletos | documentation/inventory.py:18-30 | BORRAR SEGURO | classify_path delega en doc_type.py desde Fase 13 (nota: le falta "designs" — evidencia de drift) |
| `FinishOverrides.forced_reason` write-only (+`extra_notes`) | documenter/services | BORRAR CON TEST | wiring incompleto Phase 04; borrar campo o conectarlo — decidir en fase de schemas |
| `_load_index_meta()` jamás llamada (persistencia BM25 write-only) | semantic/vault_reader.py:454-466 | INVESTIGAR | o implementar carga en cold-start u omitir el save (`_save_index_meta` L441); decide Obra 04, acá mínimo marcar |
| dead branch en `_resolve_doc_type` + mapping duplicado | vault_reader.py:390-423 | BORRAR CON TEST | borrar rama muerta; el mapping duplicado de classify_path se elimina delegando |
| segundo `re.compile` descartado + require() pattern sin uso | context_enricher/co_occurrence.py:530-532 | BORRAR SEGURO | trivial |
| `build_from_ast`, `get_path`, `get_related`, `get_files_by_type`, `node_count`, `DEFINES/EXTENDS` sin caller | co_occurrence.py | BORRAR CON TEST | solo se usan `build_from_memories` + `calculate_relationship_score` (enricher.py:565,209); grep antes |
| `_build_entity_index` sin caller (haría full-scan costoso) | enricher.py:506-527 | BORRAR SEGURO | grep confirma 0 callers |
| knob `domain_confidence` nunca consultado | ContextObserver observer.py:69 / config.py:22-23 | DEFERIDO a P-bugs | Default del plan: conectar (feature prometida) → pertenece a fase de bugs; NO se saca de config en P2 |
| ADMIN_TEAM checks casi-muertos (solo 2 headers hardcodeados) | enterprise ide adapter l.50,64,96 | INVESTIGAR | gobernanza: decidir en Obra 02, no podar ahora |
| `CORTEX_CONFIG_PATH` variable muerta (0 lecturas en cortex/**.py) | cortex-pi + docs | BORRAR CON TEST | eliminar del plugin TS y docs, o implementar lectura |
| `cortex-pi/extensions/` completo (~muerto/roto), `cortex-subagent-widget.ts`, hooks inexistentes en plugin.json, `handoffRules` muertas | cortex-pi/ | BORRAR SEGURO | review 12: ~1300 líneas muertas; borrar dir + corregir manifiestos + widget + rules |
| inlined `self.memory.sync_vault()` residual | mcp/server.py:1478-1480 | BORRAR SEGURO | trivial |

### 1.3 Comandos de verificación (re-ejecutables)

```bash
uvx vulture cortex --min-confidence 80
uvx ruff check --select F401,F841 cortex tests
# confirmar 0 callers antes de cada borrado:
grep -rn "<simbolo>" cortex/ tests/ scripts/ --include="*.py"
```

## §2 Inventario de "viejo/mal hecho"

Duplicaciones y deudas estructurales a eliminar en esta obra (fuente: review + verificación propia).

| # | Ítem | Evidencia | Obra/fase que lo resuelve |
|---|---|---|---|
| V1 | `cortex/mcp/server.py`: **2977 líneas monolíticas** — schemas inline + dispatcher if-chain (~35 ramas) + `_PathVault` definido 2 veces inline (l.2223, l.2351) | wc -l; review 10 §5 | Fase P3 (partir server.py) |
| V2 | `cortex/cli/main.py`: **2277 líneas**, 19 call sites de `_load_memory`, doble sistema `--json`/`--format`, flags muertos (`--dry-run` fake main.py:684 hardcodea dry_run=False, `all_ides` deprecated) | review 2 | Fase P4 (adelgazar main.py); dry-run fake → bug #4 (§4) |
| V3 | Enricher sync/async duplicado: `ContextEnricher.enrich()` (enricher.py:60) vs `AsyncContextEnricher` (async_enricher.py) — ~140 líneas ya drift-eadas | review 7 | Fase P5 |
| V4 | Doble stack de embedders: `episodic/embedder.py` vs `embedders/*` (base/factory/local/onnx/openai) | ls cortex/ | INVESTIGAR + Fase P6: unificar sobre `embedders/` con factory |
| V5 | Schemas Pydantic Local/Enterprise duplicados × 13 tipos documentales (campo a campo, validator a validator) — p.ej. incident.py:27-52 | review 4 #8 | Fase P6 (mixin de campos) |
| V6 | `_PathVault` copiado 2 veces dentro de server.py (además de monolito V1) | grep PathVault | Fase P3 |
| V7 | devsecdocops ×2: `scripts/devsecdocops.sh` real + copia embebida como string en `cortex/setup/templates.py:1051-…` ("kept as-is") — pueden divergir | grep devsecdocops | Fase P6: generar el .sh desde templates o leer el archivo, nunca dos fuentes |
| V8 | Skills/subagents embebidos como strings en `cortex/setup/cortex_workspace.py` (**1670 l**: render_cortex_sync_skill / _sddwork_skill / _documenter_skill / obsidian) sin test de sincronía | wc -l | Fase P7: extraer a archivos `.md` reales + test que valide que el render == contenido del archivo |
| V9 | Dependencia circular session ↔ documenter a nivel paquete: `session/quality_gates.py:44` importa `cortex.documenter.spec_loader`; documenter/* importa `cortex.session.{models,service,git,verification}` | grep | Fase P8: extraer modelos compartidos (Checkpoint, SessionStatus, Task…) a `cortex/models` o paquete `cortex/session/models` sin imports hacia documenter; quality_gates recibe spec_loader por DI |
| V10 | `requirements.txt` desactualizado vs pyproject.toml: **le falta mcp** (causa raíz del bug #1: nadie que instale por requirements.txt pinnea mcp), le faltan typer extras y deps dev. Fuente única debe ser pyproject | cat requirements.txt | TRAMO 0 / Fase P0: borrar requirements.txt (o regenerar con `uv export`) y actualizar CI/docs que lo referencien |
| V11 | `services/session_service.py` legacy (review 3 #16): migrar a lazy-deprecation PEP 562 o eliminar si no hay consumidores | review 3 | INVESTIGAR: grep consumidores; si 0 → BORRAR CON TEST |
| V12 | Tmp files huérfanos `<id>.yaml.tmp` sin GC en session/storage.py | review 3 #15 | Bug menor → fase de bugs (P-bugs) |

Regla transversal: ninguna eliminación de V* se hace sin suite verde previa (TRAMO 0) ni mezclada
con borrados de §1 en el mismo commit.

## §3 TRAMO 0 — Suite verde (línea base bloqueante)

### 3.1 Decisión: PIN `mcp>=1.2.0,<2` (NO migrar ahora)

Evidencia verificada:
- `pyproject.toml:31` declara `"mcp>=1.2.0"` sin techo → uv resolvió **mcp 2.0.0**.
- Con mcp 2.0 instalado, `Server` ya NO expone `list_tools`/`call_tool` (verificado:
  `dir(Server)` solo ofrece `add_request_handler`, `add_notification_handler`, etc.). El código
  usa la API 1.x: `cortex/mcp/server.py:314` (`@server.list_tools()`) y `:1371` (`@server.call_tool()`).
- server.py es un monolito de 2977 líneas con ~35 ramas de dispatcher. Migrar la API sobre el
  monolito duplica el riesgo y mezcla dos cambios incompatibles en un mismo diff.

Por qué pin y no migración:
1. Es un cambio de 1 línea que apaga **77 de los ~86 fallos** del suite → línea base verde hoy.
2. La migración a la API 2.x (reescribir handlers como request-handlers + cambios de tipos en
   mcp-types) se hace BIEN DESPUÉS de partir server.py en módulos, con tests de contrato MCP propios.
3. La API 1.x sigue funcionando: el pin no bloquea nada de las obras 02-05.

Migración futura queda registrada como tarea de Obra 01 fase P9 (post-split), NO de TRAMO 0.

### 3.2 Tareas exactas de TRAMO 0

- [ ] T0.1 Editar `pyproject.toml`: `"mcp>=1.2.0"` → `"mcp>=1.2.0,<2"`. Regenerar lock: `uv lock && uv sync`.
- [ ] T0.2 Verificar versión instalada: `.venv/bin/python -c "import mcp; print(mcp.__version__)"` → debe imprimir `1.x.y`.
- [ ] T0.3 Correr suite completa: `uv run pytest -x -q` → anotar cuántos fallos quedan (~9 esperados según review).
- [ ] T0.4 Corregir los ~9 fallos reales restantes UNO POR COMMIT (cli/session, documentation, ide, webgraph, mcp/create-spec — ver informes 2,3,4,9,10 para file:line).
- [ ] T0.5 Eliminar `requirements.txt` (V10). Grep previo de consumidores: `grep -rn "requirements.txt" . --exclude-dir=.git --exclude-dir=node_modules`. Actualizar lo que lo referencie (CI, docs) a `uv sync` / `uv pip install -e .`.
- [ ] T0.6 Agregar gate propio en CI: job que corre `uv run pytest -q` + `uvx ruff check cortex` + `uvx vulture cortex --min-confidence 80` y falla si vulture encuentra algo NUEVO (baseline file o umbral).
- [ ] T0.7 Marcar checkbox y actualizar ESTADO-ACTUAL.md.

Gate de salida TRAMO 0: `uv run pytest` sale 0; `uv pip list | grep ^mcp` muestra 1.x;
CI con gates propios en verde.

## §4 Bugs top del review — decisión por bug

Decisión de esta obra: los bugs que tocan código que se va a PODAR se resuelven podando;
los demás se corrijen en fase P-bugs (después del split, antes de cerrar la obra).
Fuente: docs/reviews/2026-08-deep-review/README.md "Top bugs".

| # | Bug | Decisión | Dónde |
|---|---|---|---|
| 1 | MCP roto contra mcp 2.x (server.py:314) | **TRAMO 0**: pin `<2` (§3). Migración real → fase P9 tras split | §3 |
| 2 | Búsqueda semántica vacía silenciosa si VectorCache falla; VECTOR_DIM=384 hardcodeado (vector_cache.py:41) | CORREGIR en Obra 04 (es su scope vectorial); acá solo agregar test de caracterización que documente el fallo silencioso | Obra 04 |
| 3 | `pi.uninstall()` borra AGENTS.md/README.md/justfile sin marcadores (ide/adapters/pi.py:243-249) | CORREGIR en fase P-bugs con patrón de marcadores de codex; es prerequisito directo de Obra 02 | P-bugs + Obra 02 |
| 4 | `--dry-run` ignorado en setup agent/pipeline/full (cli/main.py:684 dry_run=False) | CORREGIR en fase P4 (al tocar main.py) o antes si es trivial: propagar el flag real | P4/P-bugs |
| 5 | Caché webgraph por scope corrupta, clave omite scope (webgraph/service.py:59-87) | CORREGIR en P-bugs (test primero: dos scopes → dos entradas) | P-bugs |
| 6 | Lost-update en checkpoints Session, read-modify-write sin lock (session/service.py) | CORREGIR con helper `mutate(session_id, fn)` propuesto en review 3; P-bugs | P-bugs |
| 7 | CI generado roto: coverage gate lee /tmp/test-output.txt que nadie escribe (runners/github.py:271-276,285-288); security gate neutralizado `pip-audit \|\| true` | CORREGIR templates en P-bugs + test e2e del YAML generado | P-bugs |
| 8 | tar slip en restore_backup sin filter="data" (documentation/backup.py:71-77) | CORREGIR YA en P-bugs (1 línea + test de seguridad, prioridad alta) | P-bugs |
| 9 | memory_decay ignora decay_rate configurado (memory_decay.py:56-60) | Ligado a §1 (ScoringWithDecay muerto): decidir podar rama decorativa Y arreglar __post_init__ del config vivo | Fase P6 + Obra 04 |
| 10 | WorkItemService.get_item_note nunca encuentra notas (hu/{slug}.md vs HU-{external_id}.md, workitems/service.py:81-85 vs routing.py:290) | CORREGIR en P-bugs con test golden de naming | P-bugs |
| 13 | NUEVO (2026-08-23): SetupOrchestrator.run(dry_run=True) crea archivos reales (46 ítems en AGENT); los CLI lo esquivan con early-return pero el orquestador no respeta el flag | CORREGIR en P-bugs: propagar dry_run a los pasos mutadores + test tmp_path | P-bugs |

Regla: ningún bug se marca corregido sin test que falle antes y pase después.

## §5 Orden de podado por fases seguras

Reglas de todas las fases:
- 1 fase = 1 commit (o PR) separado. Mensaje: `chore(prune): fase Px — <resumen>`.
- Gate de cada fase: `uv run pytest -q` sale 0 ANTES de commitear. Si rompe, revertir la fase y dividirla.
- Antes de borrar cualquier símbolo: `grep -rn "<simbolo>" cortex/ tests/ scripts/` → 0 callers fuera de su propio módulo/tests dedicados.
- No mezclar nunca: poda (§1) + refactor estructural (V*) + fix de bug (§4) en el mismo commit.

| Fase | Contenido | Ítems | Riesgo |
|---|---|---|---|
| **TRAMO 0** | pin mcp + suite verde + requirements.txt fuera + gates CI | T0.1-T0.7 | bajo |
| **P1 — trivial seguro** | BORRAR SEGURO de §1.1 y §1.2: `no_graph`, `layout`(tras verificar), `real_resolve`, `_meets_adr_criteria`, `_git_diff_files`, `max_multimatch_boost`, `time.monotonic` descartado, `TYPE_CHECKING: pass`, ramas elif cold_start, re.compile duplicado co_occurrence, inlined sync_vault server.py, `_SUBFOLDER_TO_DOC_TYPE`, `_ADR_FILENAME_RE`, `_SessionFields`, F841 de tests triviales | ~14 ítems | mínimo |
| **P2 — borrar con test** | BORRAR CON TEST de §1: `is_known_agent`+tests, FeedbackEnricherIntegration+parse_github_reaction, `NoActiveSession`+export+test, maquinaria sin caller de co_occurrence, `_build_entity_index`, knob `domain_confidence` (o conectarlo), `forced_reason`/`extra_notes`, `only_agent`, F841 restantes | ~9 ítems | bajo-medio |
| **P3 — partir server.py** | Split de mcp/server.py en paquete `cortex/mcp/`: schemas.py, tools/ (un módulo por dominio), dispatcher con tabla de rutas, vault_adapter.py único (_PathVault ×2→1). Tests de contrato MCP antes del split (golden list_tools/call_tool) | V1, V6 | ALTO |
| **P4 — adelgazar main.py** | Extraer grupos de comandos a cli/submodules; unificar --json/--format; propagar --dry-run real (bug #4); matar flags muertos | V2, bug#4 | MEDIO |
| **P5 — unificar enricher** | AsyncContextEnricher hereda pero drift-ea: extraer núcleo compartido, golden tests de scoring antes de tocar | V3 | MEDIO |
| **P6 — schemas + embedders + templates** | Mixins Local/Enterprise ×13 tipos; decisión embedders (un stack sobre embedders/factory); devsecdocops fuente única; decay: podar ScoringWithDecay o conectarlo + arreglar decay_rate (bug #9) | V4, V5, V7, bug#9 | MEDIO |
| **P7 — workspace strings → archivos** | Extraer skills embebidos de cortex_workspace.py a archivos versionados; test de sincronía render==archivo | V8 | MEDIO |
| **P8 — romper ciclo session↔documenter** | Mover modelos compartidos a paquete sin imports cruzados; DI para spec_loader en quality_gates; resolver `services/session_service.py` legacy (V11); GC tmp files (V12) | V9, V11, V12 | MEDIO |
| **P-bugs (paralelo a P3+, uno por commit)** | Bugs #3,5,6,7,8,10 de §4 (tar slip PRIORIDAD 1) | tabla §4 | medio |
| **P9 — migración mcp 2.x (opcional, post-split)** | Reescribir handlers sobre API nueva SOLO si ya se partió server.py y hay tests de contrato; si no, seguir pinneados | §3.1 | alto |

Orden crítico: P1→P2 pueden correr apenas TRAMO 0 cierre. P3 es prerequisito de P9.
P-bugs puede correr en paralelo con P3-P8 (scopes disjuntos, commits separados).

## §6 Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Borrar algo "muerto" que se usa vía string/dinámico (click por nombre, importlib, entry-points) | runtime break silencioso | grep SIEMPRE incluye `scripts/`, `cortex-pi/`, `pyproject.toml`; suite verde por fase; en duda → INVESTIGAR |
| vulture 60% conf da ~368 líneas: tentación de podar en bloque | borrar comandos click / campos pydantic vivos | Prohibido podar bajo confianza 80 sin verificación manual; registrar cada excepción aquí |
| Split de server.py (P3) rompe contrato MCP para clientes existentes (plugin pi, IDEs) | usuarios cortados | Golden tests de list_tools/call_tool ANTES del split; mismo set de tools tras split (diff de nombres) |
| Pinar mcp<2 congela bugs de seguridad de 1.x | riesgo supply-chain | Revisar advisories al pinnear; migración P9 queda agendada; pin con techo explícito `<2` no `<2.0` |
| requirements.txt borrado rompe flujo de alguien | fricción onboarding | T0.5: grep de consumidores primero; dejar nota en CONTRIBUTING apuntando a uv/pyproject |
| Fases P3-P8 tocan archivos grandes compartidos (server.py, main.py) → conflictos entre obras paralelas | merge hell | Obra 02 y demás NO tocan server.py/main.py hasta que P3/P4 cierren; coordinar en ESTADO-ACTUAL.md |
| Cobertura baja en zonas podadas (pipeline/, hooks/ sin tests) | poda sin red | Antes de podar en módulo sin tests: test de caracterización mínimo (smoke) que ejecute el módulo importable |
| Suite "verde" pero lenta → fases abandonadas a mitad | obra a medio hacer | Cada fase es pequeña y autocontenida; si se aborta, el commit previo queda consistente |

## §7 Registro de ejecución

### 2026-08-23 — Fase P3 (split server.py) — COMPLETA ✅

**Commits**: `ad97caf` (golden contract) → `edfc243` (vault_adapter V6) →
`7050391` (schemas.py) → `8be09b6` (mixins + tabla dispatcher).

Red de seguridad PRIMERO:
- `tests/unit/mcp/test_golden_contract.py` (8 tests): snapshot byte-a-byte de los 32 tools
  anunciados (`golden/list_tools.json`, generado del código pre-split), tabla nombre→handler
  del dispatcher verificada 32/32 con sentinelas, ruta especial `cortex_sync_vault`, mensaje
  de tool desconocida, SERVER_VERSION.

Split en sub-commits atómicos (suite verde en cada uno):
- **V6**: `_PathVault` ×2 inline → `cortex/mcp/vault_adapter.py::PathVault` único.
- **V1 parte 1**: definiciones de tools (~1050 l) → `cortex/mcp/schemas.py::build_tool_definitions()`;
  `_CHECKPOINT_SOURCE_VALUES` viaja con ellas.
- **V1 parte 2**: handlers → mixins por dominio (`tools/search|sessions|documenter|workspace.py`);
  `_serialize_reconstruction` → documenter.py; if-chain del dispatcher → tabla `_TOOL_ROUTES`
  con resolución de atributos (semántica idéntica incl. logging y mensajes).
- Tests que scrapeaban FUENTE con regex (`TestNewMcpToolsRegistered`) convertidos a verificación
  contra el handler real / ruteo conductual — más fieles y sobreviven al split.

Resultado: `server.py` 2977 → **491 líneas** (core: init/logging/run/ping/dispatcher);
paquete `cortex/mcp/` = server + schemas + vault_adapter + tools/{search,sessions,documenter,workspace}.

Gates por cada commit: golden contract 8/8 byte-a-byte ✅ · suite completa 2279 passed ✅ ·
ruff default en cortex/mcp limpio ✅ · vulture80 = 0 ✅.

Notas:
- Candidato de PODA registrado (no mezclado acá): `WorkspaceToolsMixin._sync_vault_text`
  (0 callers en producción, solo test directo).
- El split era prerequisito de P9 (migración mcp 2.x): ahora evaluable con red completa.
  Pin `mcp<2` se mantiene hasta esa decisión.

### 2026-08-23 — Fase P2 (BORRAR CON TEST) — COMPLETA ✅

**Commit**: ver git log `chore(poda P2)`.

Ejecutado:
- Tests de caracterización NUEVOS primero (módulos sin red): `tests/unit/test_memory_decay.py`
  y `tests/unit/context_enricher/test_co_occurrence.py` — fijan la superficie que sobrevive
  (DecayConfig/calculate_decay_factor; build_from_memories/get_strongest_relationship/
  calculate_relationship_score).
- `memory_decay.py` (410→177 l): podados `ScoringWithDecay`, `create_decay_config`,
  `MemoryDecay.apply/apply_to_hits/get_stats`, `TEMPORAL_TYPES`, `EnricherDecayConfig`.
- `handoff.py`: `_KNOWN_AGENTS` + `is_known_agent` + su test.
- `session/errors.py`: `NoActiveSession` + export + test (la real es `autopilot.errors.NoActiveSessionError`).
- `co_occurrence.py` (612→322 l): `build_from_ast` + cadena AST/JS (`_extract_relationships`,
  `_extract_python/js_relationships`, `_find_related_file`), `get_related`, `get_path`,
  `_get_all_outgoing`, `get_files_by_type`, properties `node_count`/`relationship_count`,
  enum+weights `EXTENDS`/`DEFINES`, docstring actualizado.
- `enricher.py`: `_build_entity_index` (rezago P1, 0 callers confirmados).
- Wiring incompleto Phase 04: `FinishOverrides.forced_reason` (write-only),
  `InteractiveResult.forced_reason` + `.extra_notes`; actualizados los 4 sitios de
  construcción (cli/main.py ×2, autopilot/service.py, mcp/server.py) + tests unit/e2e.
  `forced_status` SÍ queda conectado (se lee en persistence.finalize).
- `setup/orchestrator.py`: parámetro muerto `only_agent` (+ call site).
- CLI flag muerto `--no-graph` del comando `context` (rezago P1) + su aserción de firma.
- `webgraph/cli.py serve`: colapsado if/else con `layout` muerto (investigado:
  `_discover_layout` es pura, sin side-effects).
- F841/F401 rezagados: `cli/ide.py run_bulk_uninstall` (root), import `compute_fingerprint`
  en vault_reader, `sys` en test_embedder_delegation, unassign `home`/`report` en
  test_contract_native_config, `original_config`/`content`/`src` en tests e2e/unit.

Desviaciones del plan original (documentadas arriba en §1):
- SKIP: `FeedbackEnricherIntegration`/`parse_github_reaction` → reservado Obra 05.
- DEFERIDO: knob `domain_confidence` → P-bugs (default: conectar).
- Adelantado desde P6: poda de la rama decorativa decay (mandato HANDOFF §5-P2);
  el fix de bug #9 queda en P6.

Gates: `ruff check --select F401,F841 cortex tests` = 0 ✅ ·
`vulture cortex --min-confidence 80` = 0 ✅ ·
`.venv/bin/python -m pytest tests/unit tests/integration` = **2271 passed, 13 skipped, exit 0** ✅

Deudas NUEVAS detectadas durante P2 (preexistentes, no regresiones → P-bugs):
- F821 latente `cortex/cli/main.py:2233`: `cortex_ide` no definido en rama interactiva de
  selección IDE (NameError si se pisa ese camino).
- F821 latente `cortex/context_enricher/enricher.py:65`: anotación `EnrichmentFilters`
  no resuelta en tiempo estático (runtime OK por `from __future__ import annotations`).
