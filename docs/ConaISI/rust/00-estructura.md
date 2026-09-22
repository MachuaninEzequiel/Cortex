# rust/ — estructura interna (código)

Fuente: `rust/Cargo.toml`, `rust/crates/*/Cargo.toml` y el árbol de `src/` (sin `target/`).

Workspace Cargo `resolver = "2"`. Paquete de workspace: versión `0.1.0`, edition `2021`, license `MIT`. Profile release: `lto = "thin"`, `codegen-units = 1`.

Regla explícita en el Cargo.toml del workspace: `cortex-core` es dominio puro (jamás PyO3); `cortex-embed` envuelve ONNX; `cortex-py` es fachada PyO3 gruesa (APIs batch).

## Árbol de primer nivel

```
rust/
  Cargo.toml          workspace + members + workspace.dependencies
  Cargo.lock
  .gitignore
  examples/
    dbg_ap.rs         smoke de WorkspaceLayout.discover
  crates/
    22 crates (listados abajo)
  target/             artefactos de build (NO documentados; no son fuente)
```

## Members del workspace (orden del Cargo.toml)

1. `cortex-core`
2. `cortex-embed`
3. `cortex-py`
4. `cortex-brain`
5. `cortex-cli`
6. `cortex-config`
7. `cortex-app`
8. `cortex-services`
9. `cortex-branding`
10. `cortex-tui`
11. `cortex-setup`
12. `cortex-actions`
13. `cortex-mcp`
14. `cortex-workspace`
15. `cortex-webgraph-server`
16. `cortex-enterprise`
17. `cortex-doctor`
18. `cortex-autopilot`
19. `cortex-pipeline`
20. `cortex-tutor`
21. `cortex-companion`
22. `cortex-brain-app`

## Grafo de dependencias crate→crate (solo path deps)

```
cortex-core          (sin deps internas)
cortex-embed         (sin deps internas)
cortex-config        (sin deps internas)
cortex-branding      (sin deps internas)
cortex-setup         (sin deps internas de otros crates Cortex)
cortex-py            → cortex-core, cortex-embed
cortex-workspace     (sin path deps de otros crates)
cortex-app           → cortex-core, cortex-embed, cortex-config, cortex-setup
cortex-services      → cortex-app, cortex-setup
cortex-actions       → cortex-app, cortex-enterprise, cortex-setup
cortex-tui           → cortex-actions, cortex-app, cortex-branding
cortex-enterprise    → cortex-app, cortex-setup, cortex-workspace
cortex-webgraph-server → cortex-core, cortex-app, cortex-workspace, cortex-setup
cortex-tutor         → cortex-workspace
cortex-autopilot     → cortex-app, cortex-enterprise, cortex-workspace, cortex-mcp
cortex-doctor        → cortex-app, cortex-config, cortex-autopilot, cortex-enterprise, cortex-workspace
cortex-mcp           → cortex-setup, cortex-app, cortex-workspace, cortex-services, cortex-autopilot, cortex-embed
cortex-pipeline      → cortex-enterprise, cortex-app, cortex-services, cortex-workspace
cortex-cli           → doctor, enterprise, tutor, autopilot, webgraph-server, workspace,
                       core, app, embed, actions, services, setup, mcp, config, tui
cortex-companion     → cortex-cli, actions, app, config, workspace, branding, brain
cortex-brain         → cortex-branding
cortex-brain-app     → cortex-brain, cortex-enterprise, cortex-workspace
```

El binario de usuario `cortex-cli` es el glue nativo: concentra comandos y llama al resto. `cortex-companion` reusa `cortex-cli` como librería. `cortex-brain-app` es el shell Tauri del binario unificado `cortex-brain`.

## Qué hay en cada crate (una línea, del código)

| Crate | Rol observado en el código |
|---|---|
| cortex-core | Coseno batch, store `vectors.v3.bin`, BM25 substring, vecinos webgraph |
| cortex-embed | `OnnxEmbedder` (ort + tokenizers), mean-pool + L2 |
| cortex-py | Módulo Python `cortex_core._native` (PyO3 ABI3) |
| cortex-config | Carga/dump de config YAML→JSON canónico |
| cortex-app | Vault semántico, episódica JSONL, RRF/context, sesiones, documenter, CI, PR |
| cortex-services | `SpecService`, `NoteService`, migración/validación de vault |
| cortex-setup | IDE adapters, hooks de sesión, writers de notas, templates composed |
| cortex-workspace | `WorkspaceLayout`, git policy, handoff, skills, runtime_context |
| cortex-cli | Binario clap `cortex-cli` 0.1.0, dispatch 100% nativo |
| cortex-mcp | Servidor MCP rmcp, 32 tools, backends nativos |
| cortex-actions | ActionEngine: catálogo, scheduler, runner, learning, signals |
| cortex-tui | TUI ratatui (Home, sessions, search, splash) |
| cortex-branding | Paleta, logo, wordmark, ANSI, gradientes |
| cortex-brain | Asistente local: router, tools READ/SAFE_ACTION, llama.cpp opcional |
| cortex-brain-app | Shell Tauri + IPC + org_memory + graph + chat engine |
| cortex-companion | Companion/HERDR: HUD, sidecar, copilot, approval, screens |
| cortex-enterprise | org.yaml, governance, promotion, retrieval unificado, reporting |
| cortex-doctor | Checks de runtime/layout/git/governance |
| cortex-autopilot | Detectores + policies + lifecycle start/preflight/checkpoint/finish |
| cortex-pipeline | Orchestrator + stages security/lint/test/documentation + GitHub runner |
| cortex-tutor | Guía offline + hint contextual |
| cortex-webgraph-server | Axum: grafo semantic/episodic/hybrid, federation, cache |

## Dónde está la ficha de cada archivo

Un `.md` por archivo fuente bajo `ConaISI/rust/crates/<crate>/`. Convenciones de nombre (varían por lote de inventario, ambas válidas):

- plano: `src--lib.md`
- espejo: `src/lib.rs.md`

Índices de lote: `_lote1-indice.md`, `_lote2-indice.md`, `_lote3-indice.md`.
