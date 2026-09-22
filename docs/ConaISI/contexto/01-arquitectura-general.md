# Contexto: arquitectura general (solo código)

Cortex es un sistema de memoria cognitiva híbrida para agentes de IA. Eso no es un slogan externo: está en tres sitios de código a la vez.

1. `cortex/__init__.py` — paquete Python `cortex-memory` versión **0.7.0**: «Hybrid Memory System for AI Agents», combina memoria episódica (vector DB) y semántica (markdown) en una capa cognitiva unificada.
2. `pyproject.toml` — mismo nombre, mismos keywords (`ai`, `agents`, `memory`, `rag`, `llm`, `embeddings`, `obsidian`), script de entrada `cortex = cortex.cli.main:app`.
3. `rust/crates/cortex-cli/src/main.rs` — binario nativo `cortex-cli 0.1.0`, about «Cortex -- hybrid cognitive memory for AI agents (CLI nativo)», **sin passthrough a Python**.

Hay dos stacks conviviendo en el repo. El Python es el paquete original (fachada `AgentMemory`, CLI Typer, MCP 1.x, Flask webgraph). El Rust es la migración total: 22 crates, CLI clap, MCP rmcp, TUI, companion, brain llama.cpp/Tauri, webgraph axum.

## Capas (de adentro hacia afuera)

```
                    [agentes IDE / humano / LLM local]
                     CLI  MCP  TUI  Companion  Brain/Tauri  Webgraph
                                      │
                         cortex-cli / cortex-mcp / cortex-companion / cortex-brain-app
                                      │
              cortex-app  cortex-services  cortex-actions  cortex-setup  cortex-enterprise
                                      │
                    cortex-core  cortex-embed  cortex-config  cortex-workspace
                                      │
                    disco: .cortex/  vault/  memory/  vectors.v3.bin  org.yaml
```

En Python la fachada equivalente es `AgentMemory` (`cortex/core.py`): cablea `EpisodicMemoryStore` + `VaultReader` + `HybridSearch` + `SpecService`/`NoteService`/`PRService` + `SessionService`. No contiene la lógica de negocio; la delega.

## Invariantes que el código impone

- **Dimensión de embeddings paramétrica.** `cortex-core` y el store `vectors.v3.bin` fallan ruidoso si un vector no coincide. Comentarios en `store.rs` y `scoring.rs` lo tratan como lección de `vector_cache.py`.
- **Paridad antes que velocidad.** BM25 no usa tantivy porque el Python cuenta substrings (`str.count`), no tokens. Coseno usa suma Neumaier para igualar `sum()` de CPython ≥3.12.
- **APIs batch en FFI.** `cortex-py` prohíbe loop-per-item: el coste FFI mataría la ganancia.
- **Brain no muta.** Tools del brain: `Tier::Read` o `Tier::SafeAction` (solo `webgraph.serve`). Mutaciones se proponen como comando CLI (`actions.propose`).
- **CLI nativo no delega.** `CORTEX_PY=1` imprime aviso y continúa nativo. Comando desconocido → `No such command`, rc 2.
- **Layout.** `WorkspaceLayout` es SSoT de paths. Layout nuevo: `repo/.cortex/{config.yaml,vault,memory,...}`. Legacy: `config.yaml` y `vault/` en la raíz del repo.

## Datos que el sistema persiste (observados)

| Dato | Dónde lo escribe el código |
|---|---|
| Config | `config.yaml` o `.cortex/config.yaml` |
| Org enterprise | `.cortex/org.yaml` (`DEFAULT_ENTERPRISE_CONFIG_PATH`) |
| Vault semántico | markdown con frontmatter, tipos adr/spec/session/hu/... |
| Episódica Python | Chroma en `persist_dir` (default `memory` / `.memory/chroma`) |
| Episódica Rust | JSONL en el persist dir de `cortex-app::episodic` |
| Vectores nativos | `vectors.v3.bin` magic `CCTXV3` |
| Sesiones | YAML en `layout.sessions_dir` |
| Feedback TUI | `feedback.jsonl` (companion) |
| Telemetría enricher | `.cortex/enrichment-events.jsonl` si está habilitada |
| Skills IDE | `.cortex/skills/`, markers `BEGIN CORTEX SECTION` |

## Dualidad de versiones

| Superficie | Python | Rust |
|---|---|---|
| Versión paquete | 0.7.0 (`cortex/__init__.py`) | 0.1.0 workspace |
| CLI | Typer `cortex.cli.main:app` | clap `cortex-cli` |
| MCP | `mcp>=1.2,<2` (`@server.list_tools`) | rmcp 0.8, `SERVER_VERSION="2.2"`, 32 tools |
| Webgraph | Flask (`optional-dependencies.webgraph`) | axum `cortex-webgraph-server` |
| Brain | `cortex.brain` marcado DEPRECATED | `cortex-brain` + `cortex-brain-app` |
| Embeddings | onnx/local/openai/fastembed | `cortex-embed` onnx + feature |
| Store vectorial | cache Python + opción nativa | `VectorStore` schema v3 |
