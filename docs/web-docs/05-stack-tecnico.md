---
title: Stack Técnico — Cortex Docs
doc_type: reference
status: draft
parent: README.md
---

# Stack Técnico — Cortex Docs

## 1. Decisión principal

**Stack recomendado**: **Astro 4+ con Starlight + MDX + Pagefind**.

| Capa | Tecnología | Razón |
| --- | --- | --- |
| Framework | **Astro 4+** | Mismo que landing — coherencia, reuso de tokens |
| Theme/preset | **Starlight** | Theme oficial Astro para docs, bien mantenido, soporte i18n + versiones |
| Content | **MDX** | Markdown + componentes React/Astro |
| Styling | **Tailwind CSS** | Coherencia con landing |
| Search full-text | **Pagefind** | Built-in en Starlight, estático, < 100KB |
| Search semántico | **Cortex MCP** | Endpoint `/api/search` proxiea a Cortex server |
| Code highlight | **Shiki** | Built-in en Starlight |
| Hosting | **Cloudflare Pages** | Edge global, mismo que landing |
| Distribución vault | **GitHub Releases (tarball)** | Simple, sin nuevas deps |

## 2. Por qué Starlight

[Starlight](https://starlight.astro.build/) es el theme oficial de Astro para documentación. Decisión tomada porque ya provee:

- ✅ Layout estándar (header, sidebar, right rail, content).
- ✅ Search Pagefind integrado.
- ✅ i18n con `defaultLocale` + `locales`.
- ✅ Versionado (vía estructura de directorios).
- ✅ Tema claro/oscuro.
- ✅ Componentes Markdown extendidos (Tabs, Cards, Code, etc.).
- ✅ Frontmatter schema con Zod nativo.
- ✅ Sidebar jerárquico con auto-detección.

**Lo que customizamos**:

- Diseño visual (tokens propios, no Starlight defaults).
- Componentes custom (`<CommandReference>`, `<McpToolReference>`, etc.).
- Integración con Cortex MCP para search semántico.
- Pipeline de export para `cortex docs-sync`.

### Alternativas evaluadas

| Tool | Pros | Contras | Decisión |
| --- | --- | --- | --- |
| **Starlight** | Astro nativo, i18n out-of-box, mantenido por Astro team | Customización del layout requiere ejection parcial | **Recomendado** |
| **Docusaurus** | Maduro, plugin ecosystem | React-only, bundle más pesado, no comparte tokens con landing Astro | No |
| **MkDocs Material** | Search excelente, Python-native (mismo stack Cortex) | Python build, divergencia con landing Astro | Descartado |
| **VitePress** | Rápido, simple | Vue-only, menos i18n | No |
| **Nextra** | Next.js-native | Bundle pesado, no comparte stack | No |
| **Custom Astro** | Control total | Reinventar la rueda; Starlight ya resuelve 80% | No |

## 3. Estructura del repositorio

Dentro del monorepo `cortex-web` (compartido con landing):

```
cortex-web/
├── apps/
│   ├── landing/        ← Ya planificado en web-landing/
│   └── docs/           ← Este proyecto
│       ├── src/
│       │   ├── content/
│       │   │   ├── docs/             ← Markdown source
│       │   │   │   ├── es/
│       │   │   │   │   ├── index.mdx
│       │   │   │   │   ├── getting-started/
│       │   │   │   │   ├── concepts/
│       │   │   │   │   ├── guides/
│       │   │   │   │   ├── cli/
│       │   │   │   │   ├── mcp/
│       │   │   │   │   ├── ide/
│       │   │   │   │   ├── autopilot/
│       │   │   │   │   ├── enterprise/
│       │   │   │   │   ├── tutorials/
│       │   │   │   │   ├── reference/
│       │   │   │   │   └── community/
│       │   │   │   └── en/
│       │   │   │       └── (mirror)
│       │   │   └── config.ts       ← Content schema
│       │   ├── components/
│       │   │   ├── CommandReference.astro
│       │   │   ├── McpToolReference.astro
│       │   │   ├── ConfigReference.astro
│       │   │   ├── VersionBadge.astro
│       │   │   ├── Deprecated.astro
│       │   │   ├── Term.astro
│       │   │   ├── Steps.astro
│       │   │   └── islands/
│       │   │       ├── SearchSemantic.tsx
│       │   │       ├── VersionSwitcher.tsx
│       │   │       └── FeedbackWidget.tsx
│       │   ├── lib/
│       │   │   ├── search.ts
│       │   │   ├── version.ts
│       │   │   └── tutor-export.ts ← Script para tarball
│       │   ├── styles/
│       │   │   └── docs.css
│       │   └── pages/
│       │       └── api/
│       │           └── search-semantic.ts ← Endpoint proxy
│       ├── public/
│       │   ├── img/
│       │   └── diagrams/
│       ├── scripts/
│       │   ├── validate-content.ts
│       │   ├── generate-tarball.ts
│       │   ├── check-cli-coverage.ts
│       │   └── check-mcp-coverage.ts
│       ├── astro.config.mjs
│       ├── tailwind.config.cjs
│       └── package.json
├── packages/
│   ├── design-tokens/    ← Compartido con landing
│   ├── ui/                ← Compartido con landing
│   └── content-schemas/  ← Zod schemas compartidos
└── .github/
    └── workflows/
        ├── docs-ci.yml
        ├── docs-deploy.yml
        └── docs-tarball.yml
```

## 4. Configuración Astro + Starlight

`astro.config.mjs`:

```js
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://docs.cortex.dev',
  integrations: [
    starlight({
      title: 'Cortex Docs',
      logo: { light: './src/assets/logo-light.svg', dark: './src/assets/logo-dark.svg' },
      defaultLocale: 'es',
      locales: {
        es: { label: 'Español' },
        en: { label: 'English' },
      },
      sidebar: [
        { label: 'Getting started', autogenerate: { directory: 'getting-started' } },
        { label: 'Concepts', autogenerate: { directory: 'concepts' } },
        { label: 'Guides', autogenerate: { directory: 'guides' } },
        { label: 'CLI', autogenerate: { directory: 'cli' } },
        { label: 'MCP', autogenerate: { directory: 'mcp' } },
        { label: 'IDE', autogenerate: { directory: 'ide' } },
        { label: 'Autopilot', autogenerate: { directory: 'autopilot' } },
        { label: 'Enterprise', autogenerate: { directory: 'enterprise' } },
        { label: 'Tutorials', autogenerate: { directory: 'tutorials' } },
        { label: 'Reference', autogenerate: { directory: 'reference' } },
        { label: 'Community', autogenerate: { directory: 'community' } },
      ],
      social: {
        github: 'https://github.com/MachuaninEzequiel/Cortex',
      },
      customCss: ['./src/styles/docs.css'],
      head: [/* meta tags, OG */],
      components: {
        Search: './src/components/islands/SearchWithSemantic.astro',
        SiteTitle: './src/components/SiteTitleWithVersion.astro',
      },
      editLink: {
        baseUrl: 'https://github.com/cortex/web/edit/main/apps/docs/',
      },
    }),
    tailwind({ applyBaseStyles: false }),
  ],
});
```

## 5. Versionado

### 5.1 Estrategia

- **URL pattern**: `docs.cortex.dev/v0.5.0/{lang}/...`
- **`latest`**: redirect a la última versión publicada.
- **Snapshots**: Cada release de Cortex publica un build inmutable.
- **Branch strategy**: `main` corresponde a la próxima versión; tags `docs-v0.5.0` corresponden a snapshots.

### 5.2 Implementación

- **Subdomain o subdir**: usar **subdirectorio versionado** (`/v0.5.0/`).
- **Build separado por versión**: en cada release, snapshot del repo → deploy a Cloudflare Pages con sub-route.
- **VersionSwitcher** isla con lista de versiones disponibles (data en `public/versions.json`).

### 5.3 Banner versión obsoleta

Si el usuario navega `v0.4.0` mientras existe `v0.5.0`:

```
[i] Estás viendo documentación de v0.4.0. La versión actual es v0.5.0. [Ver →]
```

## 6. Search

### 6.1 Pagefind (full-text)

- Built-in en Starlight.
- Index generado en build (`pnpm build` → `dist/_pagefind/`).
- Tamaño esperado: ~200-500 KB para todo el docs.
- Invocable con `⌘/Ctrl+K`.

### 6.2 Semántico (vía Cortex MCP)

Para queries naturales tipo "cómo configuro retention policies":

- **Endpoint propio**: `apps/docs/src/pages/api/search-semantic.ts`.
- **Backend**: invoca un Cortex MCP server público que tiene **el propio docs indexado** como vault.
- **Fallback**: si el endpoint no responde en 1s, mostrar solo resultados Pagefind.

### 6.3 UX de búsqueda unificada

```
┌─────────────────────────────────────────────────┐
│  ⌘K Buscá en los docs...                       │
├─────────────────────────────────────────────────┤
│  🔍 Resultados full-text (Pagefind)             │
│     - /cli/memory/search                         │
│     - /guides/search-memory                      │
│                                                  │
│  💡 Resultados semánticos                        │
│     "Cómo busco con RRF" ↔ /concepts/rrf...     │
│     "Filter by scope" ↔ /cli/memory/search#scope │
└─────────────────────────────────────────────────┘
```

Ver [`06-busqueda-navegacion.md`](06-busqueda-navegacion.md) para detalle.

## 7. Pipeline de tarball para `cortex docs-sync`

Ver [`03-integracion-tutor.md`](03-integracion-tutor.md) §4.

`apps/docs/scripts/generate-tarball.ts`:

1. Copia `src/content/docs/` → `dist-tarball/content/`.
2. Genera `dist-tarball/index.json` con metadata de todas las páginas (slug, title, summary, tags, frontmatter completo).
3. Empaqueta como `cortex-docs-{version}.tar.gz`.
4. Sube como asset de GitHub release.

CI workflow `.github/workflows/docs-tarball.yml`:

- Trigger: tag matching `docs-v*`.
- Build site + tarball.
- Crear release con tarball como asset.

## 8. CI/CD

| Workflow | Trigger | Acciones |
| --- | --- | --- |
| `docs-ci.yml` | PR | Lint, schema validate, link check, snippet test, build |
| `docs-coverage.yml` | PR | Verifica que todo comando CLI/MCP tenga página |
| `docs-deploy-preview.yml` | PR | Deploy preview a Cloudflare Pages |
| `docs-deploy-prod.yml` | merge a main | Deploy a `docs.cortex.dev/latest/` |
| `docs-tarball.yml` | tag `docs-v*` | Build tarball + publish release |
| `docs-snapshot.yml` | tag `docs-v*` | Deploy snapshot a `docs.cortex.dev/v{version}/` |
| `docs-nightly-check.yml` | nightly | Lighthouse, link-check, a11y, last_review > 6mo warnings |

## 9. Performance

| Métrica | Target |
| --- | --- |
| LCP | < 1.5s |
| FCP | < 1s |
| INP | < 200ms |
| CLS | < 0.05 |
| JS bundle (initial) | < 50 KB |
| Pagefind index | < 500 KB |

Optimizaciones:

- Pre-render todo (SSG).
- Imágenes en SVG o AVIF.
- Fonts subset latín, preload.
- Componentes islands con `client:visible` o `client:idle` solo donde necesario.

## 10. Observabilidad

- **Plausible** para analytics.
- **Cloudflare logs** para errors.
- **Sentry** opcional para errors JS.
- **Search analytics**: log de queries (con privacy, sin PII) para detectar gaps de documentación.

## 11. Dependencias críticas

| Lib | Tamaño | Por qué |
| --- | --- | --- |
| `@astrojs/starlight` | bundled | Theme principal |
| `astro` | bundled | Framework |
| `react` (solo islands) | ~45 KB | Para islands específicas |
| `shiki` | SSR | Highlight |
| `pagefind` | ~75 KB lazy | Search |
| `zod` | ~10 KB | Schema content |

## 12. Decisiones de implementación

| # | Decisión | Recomendación |
| --- | --- | --- |
| D1 | ¿Starlight default o full custom? | **Starlight + customización via slots/components** |
| D2 | ¿Una versión o todas en mismo deploy? | **Sub-route por versión**, `latest` como alias |
| D3 | ¿Search semántico siempre on o opt-in? | **Default on**, fallback graceful |
| D4 | ¿i18n: traducción humana o auto? | **Humana para ES (priority), auto-asistida para EN** |
| D5 | ¿Hosting separado de landing? | **Mismo Cloudflare account, subdomain `docs.`** |
