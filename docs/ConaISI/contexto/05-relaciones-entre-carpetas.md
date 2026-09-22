# Contexto: cómo se relacionan `cortex/`, `apps/` y `rust/`

## Flujo de datos entre las tres raíces

```
apps/brain-ui  --invoke/listen-->  rust/crates/cortex-brain-app
                                         |  usa
                                         v
                                   cortex-brain, cortex-enterprise, cortex-workspace
                                         |
                                         v
                                   CLI `cortex` (tools del brain)
                                         |
                    +--------------------+--------------------+
                    v                    v                    v
              cortex-cli            cortex-mcp          cortex-webgraph-server
                    |                    |                    |
                    +---------+----------+--------------------+
                              v
                         cortex-app / services / actions / setup / enterprise
                              v
                         disco (.cortex, vault, memory, vectors.v3.bin)

apps/docs  --no runtime-->  (sitio estático; no habla con los crates)

cortex/ (Python)  --opcional FFI-->  rust/crates/cortex-py  --> cortex-core/embed
cortex/  --CLI Typer / MCP 1.x-->  mismos paths de disco
```

## Quién escribe y quién lee el disco

Todas las superficies (Python y Rust) convergen en `WorkspaceLayout`:

- Descubre el repo caminando hacia arriba.
- Distingue layout nuevo (`.cortex/workspace.yaml` layout_version ≥ 2, o `.cortex/config.yaml`) vs legacy (`config.yaml` en la raíz).
- Resuelve `config_path`, `vault`, `sessions_dir`, `memory`, `org.yaml`, skills, logs.

Por eso un `cortex search` nativo y un `AgentMemory.retrieve()` Python, si apuntan al mismo repo, leen el mismo vault. La episódica Python (Chroma) y la episódica Rust (JSONL en `cortex-app`) **no son el mismo archivo**; son dos implementaciones del mismo concepto. El store vectorial nativo `vectors.v3.bin` es el reemplazo del cache Python de chunks.

## apps/ no es el core

- `brain-ui` es chrome: Chat, Sidebar, TopBar, Settings, DoctorModal, OrgMemoryModal, WebGraphModal, ToolApprovalModal, GovernanceBar, MarkRam, StatusBar. Tipos en `types.ts`, i18n en `i18n.ts`. Sin Tauri no hay backend.
- `docs` es el sitio Starlight. Su sidebar nombra las mismas superficies que el código (CLI nativo, 32 tools MCP, Brain, enterprise) pero este inventario no tomó esa prosa como especificación.

## rust/ consume Python solo como oráculo de paridad

Comments y tests (`parity_fixtures`, golden MCP, examples `p12a*_check`) comparan bytes/JSON con el comportamiento Python. En runtime, `cortex-cli` no lanza el proceso Python. El brain nativo sí lanza el **binario CLI** (`CORTEX_BIN` o `"cortex"`) para tools READ: es un proceso, no un import.

## cortex/ sigue siendo API de librería

Cualquier código externo que haga `from cortex.core import AgentMemory` usa Python. El MCP de agentes modernos puede usar el servidor nativo (`cortex mcp-server`). Ambos hablan el mismo contrato de tools (nombres congelados en `tools_catalog.rs` / `cortex/mcp`).
