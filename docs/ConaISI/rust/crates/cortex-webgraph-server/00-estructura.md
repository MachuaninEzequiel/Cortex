# rust/crates/cortex-webgraph-server — estructura interna

Servidor HTTP Axum del grafo de conocimiento. `#![forbid(unsafe_code)]`. Cómputo de vecinos semánticos: `cortex-core::webgraph` (Gate G4).

```
cortex-webgraph-server/
├── Cargo.toml
├── examples/webgraph_check.rs
└── src/
    ├── lib.rs
    ├── contracts.rs        # Node/Edge/Snapshot, modos semantic|episodic|hybrid
    ├── style.rs            # colores DocType, legend
    ├── config.rs
    ├── sources.rs          # SemanticSource / EpisodicSource, EmbedFn
    ├── relation_builder.rs # wikilinks, spec-links, semantic neighbors
    ├── graph_builder.rs
    ├── cache.rs            # fingerprint sha256
    ├── service.rs          # WebGraphService
    ├── federation.rs       # workspace.yaml multi-proyecto
    ├── openers.rs          # path seguro + open
    ├── server.rs           # router axum
    └── pyjson.rs           # json.dumps-compatible
```

## Relaciones

- **Recibe de:** `cortex-core` (vecinos), `cortex-app`, `cortex-workspace`, `cortex-setup`, vault + memoria episódica.
- **Envía a:** HTTP (host/port de config; brain tools mencionan 8000; brain-app `open_webgraph_browser` usa `cortex webgraph serve` y `xdg-open http://127.0.0.1:8765`).
