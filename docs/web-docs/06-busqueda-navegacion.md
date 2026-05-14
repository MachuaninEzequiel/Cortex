---
title: Búsqueda y navegación — Cortex Docs
doc_type: reference
status: draft
parent: README.md
---

# Búsqueda y Navegación

## 1. Modelo de búsqueda

Dos motores complementarios coexisten:

| Motor | Stack | Cuándo gana | Tamaño |
| --- | --- | --- | --- |
| **Full-text (Pagefind)** | Estático en cliente | Queries específicas, palabras exactas, lookup técnico | ~300-500 KB |
| **Semántico (Cortex MCP)** | Endpoint server-side | Queries en lenguaje natural, intención difusa | 0 KB cliente |

La UX **unifica ambos en una sola búsqueda** con secciones diferenciadas.

## 2. Componente `<SearchOverlay>`

### 2.1 Invocación

- **`⌘K` (Mac) / `Ctrl+K` (Win/Linux)**: abre overlay desde cualquier página.
- **Click en search bar del header**: idem.
- **`/`**: alternativa de tecla rápida (estilo GitHub).
- **`Escape`**: cierra overlay.

### 2.2 Layout

```
┌──────────────────────────────────────────────────────────┐
│  🔍  configurar enterprise                          ⌘K   │
├──────────────────────────────────────────────────────────┤
│  ⏎ Buscando full-text + semántico...                     │
│                                                          │
│  📄 RESULTADOS FULL-TEXT                                  │
│  ─────────────────────                                   │
│  ▸ Setup Enterprise                                       │
│    /enterprise/setup                                      │
│    "...configurá `.cortex/org.yaml` mediante el wizard..."│
│                                                          │
│  ▸ org.yaml Reference                                     │
│    /enterprise/org-yaml-reference                         │
│    "...todos los campos del archivo de configuración..."  │
│                                                          │
│  💡 RELACIONADOS SEMÁNTICOS                               │
│  ──────────────────────                                  │
│  ▸ Presets enterprise                                     │
│    /enterprise/presets                                    │
│    "Pre-configuraciones para empresas pequeñas..."        │
│                                                          │
│  ▸ Promotion pipeline                                     │
│    /enterprise/promotion-pipeline                         │
│    "Flujo de promoción candidate → reviewed..."           │
├──────────────────────────────────────────────────────────┤
│  ↑↓ navegar  ⏎ abrir  ⎋ cerrar                          │
└──────────────────────────────────────────────────────────┘
```

### 2.3 Comportamiento

1. **Al tipear**: debounce 200ms.
2. **Pagefind**: query inmediata (es local, <50ms).
3. **Semántico**: query async; mientras carga, mostrar skeleton.
4. **Resultados**: top 5 full-text + top 3 semántico, de-duplicados.
5. **Navegación con teclado**: ↑↓ entre resultados, ⏎ abre, ⎋ cierra.
6. **Sin resultados**: mensaje + sugerir filtrar por sección o reportar gap.

### 2.4 Filtros

- **Por sección**: pill al lado del search input ("CLI", "Concepts", etc.).
- **Por versión**: hereda de la URL actual (no editable en overlay).
- **Por idioma**: hereda de la URL actual.

### 2.5 Quick actions

Algunas queries gatillan acciones especiales en lugar de resultados:

| Query | Acción |
| --- | --- |
| `cortex <command>` | Navega directo a `/cli/.../<command>` si existe |
| `org.yaml` | Navega a `/enterprise/org-yaml-reference` |
| `ide cursor` / `cursor` | Navega a `/ide/cursor` |
| `?changelog` | Navega a `/reference/changelog` |
| `?settings` | Open theme/lang settings modal |

## 3. Endpoint `/api/search-semantic`

`apps/docs/src/pages/api/search-semantic.ts`:

```ts
export const prerender = false;

export async function GET({ url, request }) {
  const query = url.searchParams.get('q');
  const lang = url.searchParams.get('lang') ?? 'es';
  const version = url.searchParams.get('v') ?? 'latest';

  // Proxy a Cortex MCP server con el docs como vault
  const response = await fetch(process.env.CORTEX_DOCS_MCP_URL + '/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      scope: 'local',
      filters: { lang, version, tags_includes: ['docs'] },
      top_k: 5,
    }),
  });

  const data = await response.json();
  return new Response(JSON.stringify(data), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=300' },
  });
}
```

### 3.1 Backend

Un **Cortex MCP server público** ejecuta:

```bash
cortex mcp-serve \
  --project-root /srv/cortex-docs-vault \
  --read-only \
  --bind 0.0.0.0:9100
```

Donde `/srv/cortex-docs-vault/` contiene el docs indexado.

Pipeline:

1. Cada release del docs → tarball publicado.
2. Servidor MCP descarga el tarball, lo extrae, ejecuta `cortex index-docs`.
3. Si el server crashea, el endpoint cae a fallback (sin resultados semánticos).

### 3.2 Caching

- **Edge cache**: 5 min (`Cache-Control: max-age=300`).
- **Memoria server**: query → result LRU 1024 entries.
- **CDN**: Cloudflare Workers KV opcional.

### 3.3 Rate limiting

- **Por IP**: 60 queries/min.
- **Por sesión** (cookie): 200/hour.
- **Global**: 10k/hour (alerta si excede).

### 3.4 Fallback

- Si endpoint tarda >1s o falla: marcar "Búsqueda semántica no disponible" en overlay, mostrar solo Pagefind.

## 4. Sidebar (navegación principal)

### 4.1 Estructura

Auto-generada por Starlight con override en `astro.config.mjs`:

```ts
sidebar: [
  { label: 'Getting started', autogenerate: { directory: 'getting-started' } },
  { label: 'Concepts', autogenerate: { directory: 'concepts' } },
  // ...
]
```

### 4.2 Comportamiento

- **Persistencia**: estado expandido/colapsado por sección, en localStorage.
- **Highlight**: página actual con estilo distintivo.
- **Scroll-into-view**: al cargar, sidebar scrollea hasta página actual.
- **Búsqueda inline**: input al top del sidebar filtra páginas por título.
- **Iconos por sección**: Lucide icons.

### 4.3 Mobile

- Hidden por default, drawer al click en hamburger.
- Slide-in desde la izquierda.
- Cierra al click fuera o tecla `Esc`.

## 5. Right rail ("On this page")

### 5.1 Contenido

- Lista de **H2 y H3** de la página actual.
- Indent por nivel.
- Anchor a cada heading.

### 5.2 Scroll-spy

- IntersectionObserver detecta heading visible.
- Highlight del item activo.
- Smooth scroll al click.

### 5.3 Acciones

Al final del right rail:

- **`Editar en GitHub`** (link a `edit_url` del frontmatter).
- **`¿Útil?`** (👍/👎) — dispara analytics, opcional input de texto si 👎.

### 5.4 Visibilidad

- Solo `xl` (≥1280px).
- En `lg`, el right rail desaparece y el contenido ocupa más ancho.

## 6. Breadcrumbs

### 6.1 Generación

- Auto-derivados del path: `/cli/memory/search` → `Docs · CLI · Memory · Search`.
- Cada segmento es link clickable.
- Configurable via frontmatter `breadcrumb` si se desea custom.

### 6.2 Mobile

- Truncated con ellipsis: `Docs · ... · Search`.
- Tap para expandir.

## 7. Footer de página

Cada página termina con:

- **Anterior / Siguiente**: navegación lineal en orden de sidebar.
- **Última actualización**: `last_review` del frontmatter.
- **Versión**: badge con `since_version`.
- **Tags**: pills clickables que filtran search.
- **Página relacionadas**: lista de `related` del frontmatter, manualmente curada.

## 8. Comandos quick (palette extendida)

`⌘⇧K` invoca un **command palette** distinto al search:

- "Ir a CLI" / "Ir a Enterprise" / etc.
- "Cambiar tema".
- "Cambiar idioma".
- "Cambiar versión".
- "Ver shortcuts".

Stack: mismo overlay component con modo `command`.

## 9. Shortcuts globales

| Shortcut | Acción |
| --- | --- |
| `⌘K / Ctrl+K / /` | Abrir búsqueda |
| `⌘⇧K / Ctrl+Shift+K` | Abrir command palette |
| `⌘⇧L` | Toggle idioma |
| `⌘⇧T` | Toggle tema |
| `↑↓` (en overlay) | Navegar resultados |
| `Enter` (en overlay) | Abrir resultado |
| `Esc` | Cerrar overlay |
| `?` | Ver lista de shortcuts |

Mostrar tooltip "Press ? for shortcuts" al hover sobre el search.

## 10. Sin JavaScript

- Search overlay no funciona sin JS.
- Mostrar formulario tradicional como fallback (`<form action="/search?q=">`).
- Sidebar y navegación principal funcionan sin JS (Astro SSR).

## 11. SEO y discoverability

- **Sitemap** incluye TODAS las páginas con `lastmod`.
- **OG image por página** opcional (auto-generada con título).
- **Schema.org `TechArticle`** en cada página de reference.
- **Schema.org `HowTo`** en cada how-to con steps.

## 12. Analytics de búsqueda

Eventos:

- `search_open`: abre overlay.
- `search_query`: submit (debounced).
- `search_click`: click en resultado.
- `search_no_results`: query sin resultados.
- `search_quick_action`: query gatilla quick action.

Dashboard semanal para revisar **queries sin resultados** y **queries con bajo CTR** → identificar gaps de documentación.

## 13. Mantenimiento

- **Pagefind index** regenera en cada build.
- **Cortex docs vault** regenera en cada release (workflow `docs-tarball.yml`).
- **MCP server** se redeploy con nuevo vault automáticamente.
