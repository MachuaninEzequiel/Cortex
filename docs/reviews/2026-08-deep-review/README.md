# Deep Review Cortex — 2026-08 (exhaustivo, 12 subsistemas)

Revisión profunda del repo completo: ~48k LOC Python (paquete `cortex-memory` v0.5.0) + plugin TS `cortex-pi`.
Método: 12 revisores en paralelo con scopes disjuntos; cada uno leyó todos los archivos de su scope;
los hallazgos críticos fueron verificados por el orquestador (marcados ✅ abajo).
Informes completos por subsistema en este directorio (`<n>-<area>.md`, citas file:line).

## Línea base de gates (al momento del review)

| Gate | Resultado |
|---|---|
| Tests (unit+integration) | 70 failed + 16 errors (~86) |
| Causa dominante | `mcp>=2.0.0` instalado sin pinning; código usa API 1.x (`@server.list_tools()`) — 77 fallos de un solo bug sistémico |
| Fallos reales restantes | ~9 distribuidos en cli/session, documentation, ide, webgraph, mcp/create-spec |
| Cobertura global | 75% — pero **cero tests** para pipeline/, hooks/, feedback_loop, memory_decay, pr_capture, tutor/, frontend webgraph |

## Mapa de salud por subsistema

| # | Subsistema | Salud | Informe |
|---|---|---|---|
| 1 | core/entrypoints/pipeline/hooks | MEDIA | [1-core-entrypoints.md](1-core-entrypoints.md) |
| 2 | cli | BUENA | [2-cli.md](2-cli.md) |
| 3 | session | 7/10 | [3-session.md](3-session.md) |
| 4 | documentation | 7/10 | [4-documentation.md](4-documentation.md) |
| 5 | documenter/services/workitems | 7/10 | [5-documenter-services.md](5-documenter-services.md) |
| 6 | semantic/retrieval/embedders/episodic/security | 7/10 (bugs silenciosos graves) | [6-semantic-retrieval.md](6-semantic-retrieval.md) |
| 7 | context_enricher | MEDIA | [7-context-enricher.md](7-context-enricher.md) |
| 8 | autopilot/ci | 7/10 | [8-autopilot-ci.md](8-autopilot-ci.md) |
| 9 | webgraph/tutor/skills | 6.5/10 | [9-webgraph-tutor.md](9-webgraph-tutor.md) |
| 10 | enterprise/ide/mcp | MEDIA-ALTA (server.py monolítico) | [10-enterprise-ide-mcp.md](10-enterprise-ide-mcp.md) |
| 11 | setup/workspace/infra | 7/10 | [11-setup-workspace-infra.md](11-setup-workspace-infra.md) |
| 12 | cortex-pi/docs/vision | 🟡 perímetro deteriorado | [12-pi-docs-vision.md](12-pi-docs-vision.md) |

## Top bugs verificados / de mayor severidad

1. ✅ **MCP roto contra mcp 2.x** — `cortex/mcp/server.py:314` usa `@server.list_tools()` (API 1.x). Sin pinning en pyproject. 77 tests caídos.
2. ✅ **Búsqueda semántica devuelve vacío silenciosamente** si VectorCache falla a mitad del batch; `VECTOR_DIM=384` hardcodeado (vector_cache.py:41) rompe con backends no-MiniLM.
3. ✅ **`pi.uninstall()` borra AGENTS.md/README.md/justfile** del proyecto sin marcadores ni backup (ide/adapters/pi.py:243-249). codex demuestra el patrón correcto de marcadores que nadie más adoptó.
4. ✅ **`--dry-run` ignorado** en `setup agent/pipeline/full` (cli/main.py:684 hardcodea dry_run=False); solo enterprise lo implementa.
5. **Caché webgraph por scope corrupta** — store_snapshot guarda post-filtro y la clave omite scope (webgraph/service.py:59-87).
6. **Lost-update en checkpoints de Session** — read-modify-write sin lock alrededor del ciclo (session/service.py); dos workers MCP pierden checkpoints.
7. **CI generado roto out-of-the-box** — coverage gate lee /tmp/test-output.txt que nadie escribe (pipeline/runners/github.py:271-276); security gate neutralizado por `pip-audit || true`.
8. **tar slip** en restore_backup (documentation/backup.py:71-77): extractall sin filter="data".
9. **memory_decay ignora decay_rate configurado** (memory_decay.py:56-60): decay_rate=1.0 produce ~0.996; 0 → default.
10. **WorkItemService.get_item_note nunca encuentra notas** — mismatch de naming hu/{slug}.md vs HU-{external_id}.md (workitems/service.py:81-85 vs routing.py:290).

## Deudas estructurales principales

- `mcp/server.py`: 2.977 líneas monolíticas (schemas inline + dispatcher if-chain ~35 ramas).
- `cli/main.py`: 2.277 líneas, 19 call sites de _load_memory; doble sistema --json/--format.
- Duplicación sync/async del ContextEnricher (~140 líneas ya drift-eadas).
- Doble stack de embedders (episodic/embedder vs embedders/*).
- Schemas Pydantic Local/Enterprise duplicados × 13 tipos documentales.
- Dependencia circular session ↔ documenter a nivel de paquete.
- cortex-pi: ~1300 líneas muertas/rotas; manifiestos plugin apuntando a directorios eliminados.
- Skills/subagents embebidos como strings en cortex_workspace.py (1670 l) sin test de sincronía.

## Orden recomendado para el gran cambio (pre-requisitos)

1. Pin de dependencias (mcp<2 o migración) → suite verde como línea base.
2. Tests de caracterización para pipeline/ + golden tests de scoring del enricher.
3. Partir server.py y main.py en módulos; APIs públicas para las fronteras privadas (validator→_scope_cross_check, etc.).
4. Corregir los 10 bugs top antes de cualquier refactor grande.
