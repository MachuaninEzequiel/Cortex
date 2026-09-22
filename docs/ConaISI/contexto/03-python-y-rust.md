# Contexto: Python (`cortex/`) y Rust (`rust/`)

## Qué representa cada carpeta hoy

`cortex/` es el paquete Python instalable (`cortex-memory` 0.7.0). Sigue teniendo la fachada pública `AgentMemory`, el CLI Typer, el MCP 1.x, embedders, documenter, enterprise, etc. Tests del repo (`pyproject.toml` `testpaths = ["tests"]`) cubren este paquete.

`rust/` es el workspace nativo de la migración. El CLI documenta en `main.rs`: «CLI 100% nativo (sin passthrough a Python)». `CORTEX_PY=1` es rollback histórico: avisa y **no** delega.

`cortex/brain/__init__.py` está marcado **DEPRECATED**: el dueño nativo es `cortex-brain` (Rust + llama.cpp). El Python se conserva como oráculo.

`cortex-py` no reemplaza el paquete `cortex/`: expone `cortex_core._native` para que el Python llame al núcleo (cosine, store, BM25, vecinos, embedder) en batch. Feature `CORTEX_NATIVE=1` aparece en comentarios de la fachada nativa como opt-in.

## Correspondencia módulo ↔ crate (observada en nombres y path deps)

| Python | Rust |
|---|---|
| `cortex.core.CortexConfig` | `cortex-config` |
| `cortex.semantic.*`, `retrieval.*`, `episodic.*`, `session.*`, `documenter.*`, `ci.*`, `pr_capture`, `doc_*` | `cortex-app` |
| `cortex.services.*`, `documentation.migration` | `cortex-services` |
| `cortex.setup.*`, `ide.*`, `session.hooks.*` | `cortex-setup` |
| `cortex.workspace.*`, `git_policy`, `handoff`, `runtime_context` | `cortex-workspace` |
| `cortex.cli.*` | `cortex-cli` |
| `cortex.mcp.*` | `cortex-mcp` |
| `cortex.action_engine.*` | `cortex-actions` |
| `cortex.tui.*` | `cortex-tui` |
| `cortex.autopilot.*` | `cortex-autopilot` |
| `cortex.pipeline.*` | `cortex-pipeline` |
| `cortex.enterprise.*` | `cortex-enterprise` |
| `cortex.doctor` | `cortex-doctor` |
| `cortex.tutor.*` | `cortex-tutor` |
| `cortex.webgraph.*` | `cortex-webgraph-server` |
| `cortex.brain.*` | `cortex-brain` (+ `cortex-brain-app`) |
| `cortex.embedders.onnx` | `cortex-embed` |
| scoring/store/bm25/webgraph vecinos | `cortex-core` |

No hay crate Python para `cortex.hooks.agent_hooks` ni `cortex.workitems` como crate propio: workitems viven dentro de `cortex-app` (`workitems.rs`). Companion/HERDR y branding no tienen paquete Python equivalente de producto.

## Paridad como contrato

El código Rust está lleno de examples `*_check.rs` y tests `*_parity.rs` / `cli_self_golden` / `mcp_golden_contract`. La semántica se clona:

- mismos nombres de tools MCP y mismo orden de keys JSON (`tools_catalog.rs`)
- mismos textos de error Typer-like en el CLI nativo
- mismos números BM25 (substring + idf snapshot desde Python)
- mismos bits de cosine (Neumaier)
- same dump YAML estilo PyYAML (`cortex-workspace/src/pyyaml.rs`, `pyjson` en varios crates)

Donde Rust **no** copia el runtime Python: el CLI ya no llama a Typer; el MCP nativo usa backends `Native*Backend` que hablan con `cortex-app`/`cortex-services`/`cortex-autopilot`, no con el proceso Python.

## Cómo se elige el runtime en la práctica (código)

- Instalar el paquete: `pyproject.toml` script `cortex` → Python.
- Instalar el binario: comentario en `main.rs`: `cargo install --path rust/crates/cortex-cli`.
- Brain UI: Tauri empaqueta `apps/brain-ui` + `cortex-brain-app`.
- Companion: bins `cortex-companion`, `cortex-herdr-sidecar`, `cortex-herdr-float`, `cortex-herdr-copilot`.
- Bindings: maturin en `cortex-py/pyproject.toml` produce `cortex_core._native`.

Python opcional-deps: `local` (sentence-transformers), `fastembed`, `openai`, `anthropic`, `ollama`, `webgraph` (flask). Rust opcional: feature `llama` en brain/companion/brain-app; feature `onnx` en embed/py.
