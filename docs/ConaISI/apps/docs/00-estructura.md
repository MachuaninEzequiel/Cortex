# apps/docs — estructura interna

Sitio estático de documentación. Código de empaquetado leído; prosa de `src/content/docs/**` no usada como arquitectura.

```
apps/docs/
  package.json
  pnpm-lock.yaml
  pnpm-workspace.yaml
  astro.config.mjs
  tsconfig.json
  .gitignore
  public/favicon.svg
  src/
    assets/cortex-logo.svg
    content/config.ts
    content/docs/          ← páginas Starlight (es root + en)
  dist/                    ← build (ignorado)
  .astro/                  ← cache Astro (ignorado)
```

## Sidebar declarado en astro.config.mjs (estructura del producto según el sitio)

- Comenzando: welcome, quickstart, installation, doctor
- Arquitectura: overview, tripartite-memory, hybrid-search-rrf, onnx-embeddings, vault-structure, workspace-layout
- CLI (Rust Nativo): overview, tui, doctor, setup, session, search, remember, hu, next, webgraph, autopilot, ide, tutor, ci-pr, docs
- MCP (32 Tools): overview, ping-health, search-context, session-tools, docs-specs, autopilot-tools, tickets-vault
- (siguen bloques IDE / enterprise / cortexbrain en el mismo config)

Este sidebar coincide con comandos reales de `cortex-cli` y con `cortex-mcp` (`SERVER_VERSION = "2.2"`, 32 tools en `tools_catalog.rs`). La coincidencia se verifica en el código de rust, no en los markdown del sitio.

## Archivos de contenido presentes (nombres solamente)

getting-started: welcome, quickstart, installation, doctor  
concepts: overview, tripartite-memory, hybrid-search-rrf, onnx-embeddings, vault-structure, workspace-layout  
cli: overview + un md por comando  
mcp: overview, ping-health, search-context, session-tools, docs-specs, autopilot-tools, tickets-vault  
ide: claude, codex-antigravity, cursor, pi-opencode  
enterprise: governance, memory-report, review-promotion  
cortexbrain: overview, webgraph  
en/: index.mdx + getting-started/quickstart.md  
index.mdx (root)

## Relaciones

### Recibe de
Copy escrito a mano. No importa crates Rust en compile-time.

### Envía a
Build estático (`astro build` → `dist/`). Consumidores: navegador / hosting.

### Notas
`defaultLocale: 'root'` con `lang: 'es'`. Inglés bajo prefijo `en`.
