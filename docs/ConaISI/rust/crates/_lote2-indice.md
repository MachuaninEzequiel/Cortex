# Lote 2 — índice y síntesis

Documentación extraída **solo del código** de cinco crates nativos que forman el borde operativo de Cortex: CLI, MCP, setup/escritores, workspace y servicios de dominio.

Árbol generado: un `00-estructura.md` por crate + un `.md` por cada archivo fuente (path relativo con `/` → `--`). Cobertura 1:1 verificada:

| Crate | Archivos fuente | Docs por archivo |
|---|---|---|
| cortex-cli | 50 | 50 |
| cortex-mcp | 21 | 21 |
| cortex-setup | 63 | 63 |
| cortex-workspace | 10 | 10 |
| cortex-services | 7 | 7 |

## Qué es este lote en el sistema

Cortex nativo ya no reenvía al CLI Python (`CORTEX_PY=1` es aviso histórico). El binario `cortex-cli` despacha comandos in-process contra crates de dominio. El mismo binario lanza el servidor MCP (`mcp-server --stdio`) que los 11 adapters IDE configuran.

Flujo de datos típico:

```
Agente IDE  --stdio-->  cortex-cli mcp-server  -->  CortexMcpServer
                                                    | handlers (formato oráculo)
                                                    v
                                              Native*Backend
                                                    |
                    +-------------------------------+------------------+
                    v                 v               v                 v
             SessionService     SemanticIndex    SpecService      AutopilotService
             (cortex-app)       (cortex-app)     (cortex-services) (cortex-autopilot)
                    ^                 ^               ^
                    |                 |               |
             WorkspaceLayout     vault/*.md      writers::build_note
             (cortex-workspace)                  (cortex-setup)
```

CLI humano (`cortex doctor`, `session`, `search`, `setup`, …) usa las mismas librerías, no otro runtime.

## cortex-workspace — mapa de rutas

`WorkspaceLayout::discover` decide layout **nuevo** (todo bajo `.cortex/`) vs **legacy** (`config.yaml` en la raíz). Es la SSoT de paths: vault, memoria, sessions, skills, webgraph, org.yaml, promotion.

También: `AgentHandoff` YAML (legacy entre agentes), gitignore recomendado, `install_skills` Obsidian (5 skills embebidas), namespacing episódico (project/branch/custom) y emisor YAML PyYAML para el handoff.

No duplica `resolve_safe` (eso es cortex-app/security).

## cortex-services — spec, nota, migración

Puertos hexagonales `EpisodicPort` / `SemanticPort` / `SessionOpener`.

- **SpecService**: valida `proposal_mode`, normaliza hooks (nombres únicos), persiste spec canónica, indexa, abre Session best-effort, remember opcional.
- **NoteService**: nota session con rollback (si index/sync/episodic falla, borra el archivo).
- **migration**: vault legacy → schema_version 1; backups `tar czf`.

`persist_note` centraliza idempotencia por fingerprint y el error de duplicado del writer Python.

## cortex-mcp — 32 tools, versión 2.2

Catálogo congelado en `tools_catalog.rs`. Dispatcher en `server.rs`:

- ping completo (starting 2s / degraded 300s / ok)
- `cortex_sync_vault` inline (`MemoryBackend`)
- resto por familia + backends nativos inyectados por CLI

Gobernanza: `cortex_create_spec` exige `cortex_sync_ticket` previo; `cortex_emit_proposal` impone gap 2s antes de confirmar.

Search degrada a keyword si no hay ONNX. Spec backend no indexa incremental (hace falta `cortex reindex`). Finish no re-ejecuta hooks pesados por default.

Lista de tools: ver `cortex-mcp/00-estructura.md`.

## cortex-cli — fachada 100% nativa

Dispatch por primer token; desconocido rc 2. Sin args abre TUI Home.

Comandos cableados (detalle en `cortex-cli/00-estructura.md`): doctor, tutor/hint, org-config, promote/review-knowledge, memory-report, webgraph, autopilot, search/context/stats/reindex, session (+hooks), next, hu, ide, remember/forget, docs, ci, setup/init, pr-context, mcp-server, finish.

`NativeMemory` es el glue de retrieval (layout + BM25 + JSONL episódico + ONNX + RRF). JSON de `--json` pasa por `PyVal` para igualar `json.dumps` de CPython.

Límites observados en código:

- HU/Jira nativo solo `file://` (sin HTTP en el crate)
- `memory-report --telemetry` falla explícito
- webgraph federado falla explícito
- setup interactivo no existe (exige `--non-interactive`)
- finish `--interactive` no cableado

## cortex-setup — writers, IDEs, COMPOSED

Tres bloques:

1. **Documentación canónica**: DocType, routing, jinja 13 templates, yaml PyYAML, writers `build_note`.
2. **Setup de proyecto**: detector de stack, templates (config, CI DevSecDocOps, vault seed), 11 adapters IDE, 4 session hooks.
3. **Skills COMPOSED**: grill → to-spec → to-tickets → implement/tdd/diagnose → review (+ glossary). Tríada thin+craft (sync/SDDwork/documenter). Marcadores HTML dedicados para no pisar Codex.

MCP que inyectan los adapters: `cortex-cli mcp-server --stdio`.

Traducción de tools canónicos validada solo para `claude_code` y `opencode`.

## Dependencias entre los cinco crates

```
cortex-workspace  (sin deps Cortex)
cortex-setup      (sin deps Cortex)
        ^
        | persist_note / templates / IDE / hooks
cortex-services   --> cortex-app + cortex-setup
cortex-mcp        --> setup, app, workspace, services, autopilot, embed
cortex-cli        --> (casi todo el workspace, incl. mcp, tui, doctor, ...)
```

## Cómo navegar los docs

1. Leer `00-estructura.md` del crate.
2. Abrir el `.md` del archivo (nombre = path con `--`).
3. Cada ficha: qué hay, para qué, recibe de, envía a, notas del código.

No se usaron README/docs/handoffs del repo como fuente.
