---
title: Fase 06 — Búsqueda full-text y semántica
doc_type: phase
phase: 6
status: pending
depends_on: [phase-05]
unlocks: [phase-07]
estimated_duration: 4 días-persona
---

# Fase 06 — Búsqueda full-text y semántica

## Objetivo

Implementar el sistema de búsqueda unificado descrito en [`06-busqueda-navegacion.md`](../06-busqueda-navegacion.md):

- **Pagefind** (full-text) — built-in Starlight, customizado.
- **Search semántico** vía Cortex MCP server.
- **Overlay unificado** (`⌘K`) con resultados de ambos.
- **Command palette** (`⌘⇧K`).
- **Analytics** de queries.

## Entregables

1. **Pagefind index** generado y servido.
2. **Cortex MCP server público** corriendo con el docs indexado.
3. **Endpoint `/api/search-semantic`** funcional.
4. **Componente `<SearchOverlay>`** con UX descrita.
5. **Command palette** `<CommandPalette>`.
6. **Analytics** de búsqueda instrumentados.
7. **Tests E2E** del flujo de búsqueda.

## Tareas detalladas

### 6.1 Setup Pagefind (0.5 día)

Starlight incluye Pagefind nativamente. Customización:

- [ ] Configurar `pagefind` options en `astro.config.mjs`:
  ```ts
  pagefind: {
    ranking: { termSimilarity: 1, pageLength: 0.5 },
    forceLanguage: 'es', // o auto-detect
  }
  ```
- [ ] Excluir páginas `status: draft` del index.
- [ ] Excluir secciones específicas con `data-pagefind-ignore` cuando aplique.
- [ ] Verificar tamaño del index final (< 500 KB target).

### 6.2 Cortex MCP server público (1 día)

#### Infraestructura

Servidor dedicado con Cortex corriendo en modo MCP read-only:

- **Host**: Cloudflare Worker o VM pequeña (Hetzner, Fly.io, Railway).
- **Cortex install** desde pip.
- **Vault** poblado con tarball del docs.
- **Endpoint MCP** expuesto en puerto interno.
- **Proxy HTTP** para HTTP → MCP-over-stdio.

#### Setup steps

```bash
# En el server:
pip install cortex-memory
mkdir /srv/cortex-docs-vault
cd /srv/cortex-docs-vault
cortex setup agent --non-interactive

# Descargar tarball del docs y extraer
curl -L https://github.com/cortex/web/releases/download/docs-v0.5.0/cortex-docs-0.5.0.tar.gz \
  | tar -xz -C .cortex/vault/

# Indexar
cortex index-docs

# Levantar MCP server
cortex mcp-serve --bind 0.0.0.0:9100 --read-only
```

- [ ] Setup automatizado vía script + systemd o Docker.
- [ ] Healthcheck endpoint.
- [ ] Update automático cuando tarball cambia (cron o webhook).

### 6.3 Endpoint `/api/search-semantic` (0.5 día)

`apps/docs/src/pages/api/search-semantic.ts`:

- [ ] Implementar según spec en `06-busqueda-navegacion.md` §3.
- [ ] Variables de entorno: `CORTEX_DOCS_MCP_URL` (privado).
- [ ] Cache edge 5 min.
- [ ] Rate limit por IP via Cloudflare Workers.
- [ ] Fallback si MCP server cae.

### 6.4 Componente `<SearchOverlay>` (1.5 días)

`apps/docs/src/components/islands/SearchOverlay.tsx`:

#### Features

- [ ] Modal overlay full-screen mobile, centered desktop.
- [ ] Input con debounce 200ms.
- [ ] Resultados Pagefind sincrónicos (<50ms).
- [ ] Resultados semánticos async con skeleton.
- [ ] Secciones diferenciadas (Full-text / Semantic).
- [ ] Keyboard navigation completa (↑↓⏎⎋).
- [ ] Filtros por sección (pills).
- [ ] Quick actions matching:
  - `cortex <cmd>` → navega directo si existe.
  - `org.yaml` → navega a reference.
- [ ] Sin resultados: mensaje + sugerir reportar gap.

#### Performance

- [ ] Lazy load: solo carga al abrir overlay primera vez.
- [ ] Cache de queries (en-memory durante sesión).
- [ ] Debounce eficiente.

#### Trigger

- [ ] Hook `useSearchOverlay()` con `open()`, `close()`.
- [ ] Atajo `⌘K / Ctrl+K / /` registrado globalmente.
- [ ] Click en search bar del header.
- [ ] Botón flotante mobile opcional.

### 6.5 Command palette (0.5 día)

`apps/docs/src/components/islands/CommandPalette.tsx`:

- [ ] Mismo overlay, modo `command`.
- [ ] Comandos pre-definidos:
  - "Ir a sección X" → 11 secciones top-level.
  - "Cambiar tema" → toggle.
  - "Cambiar idioma" → toggle.
  - "Cambiar versión" → submenu.
  - "Ver shortcuts" → modal con lista.
- [ ] Invocable con `⌘⇧K / Ctrl+Shift+K`.

### 6.6 Analytics (0.5 día)

Eventos a trackear:

- [ ] `search_open`
- [ ] `search_query` (debounced, query)
- [ ] `search_click` (query, result, rank)
- [ ] `search_no_results` (query)
- [ ] `search_quick_action` (query, action_id)

Stack: Plausible custom events.

Dashboard semanal: top queries, queries sin resultados, queries con bajo CTR.

### 6.7 Tests E2E (0.5 día)

Playwright tests:

- [ ] `⌘K` abre overlay.
- [ ] Tipear "search" muestra resultados.
- [ ] Click navega a página correcta.
- [ ] `Esc` cierra overlay.
- [ ] Quick action `cortex search` navega directo.
- [ ] Semantic results aparecen cuando MCP responde.
- [ ] Fallback gracefulcuando MCP no responde.

## Criterios de aceptación

- ✅ `⌘K` funciona en todas las páginas.
- ✅ Pagefind retorna resultados en <100ms.
- ✅ Semantic search retorna resultados en <800ms (P95).
- ✅ Overlay accessible (keyboard, screen reader).
- ✅ Mobile: overlay full-screen funcional.
- ✅ Tests E2E verdes.
- ✅ Analytics events disparándose.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| MCP server cae y rompe search | Endpoint con timeout 1s, fallback solo Pagefind |
| Pagefind index muy grande | Excluir páginas draft + chunking inteligente |
| Latencia semántica alta | Cache edge 5 min + warm-up con queries comunes |
| Costo del MCP server (infra) | Usar Cloudflare Worker que invoca instancia tiny |

## Siguiente fase

→ [Fase 07 — Puente con el Tutor (la pieza crítica)](fase-07-puente-tutor.md)
