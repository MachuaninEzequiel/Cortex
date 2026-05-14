---
title: Stack técnico — Cortex Landing
doc_type: reference
status: draft
parent: README.md
---

# Stack Técnico — Cortex Landing

## 1. Decisión principal

**Stack recomendado**: **Astro 4+ con islas React + Tailwind CSS + Framer Motion + Pagefind**.

| Capa | Tecnología | Versión mínima | Razón |
| --- | --- | --- | --- |
| Framework | **Astro** | 4.x | SSR/SSG por defecto, islands architecture, bundle JS ínfimo. |
| UI runtime (islas) | **React** | 18+ | Ecosistema, Framer Motion, familiaridad. |
| Styling | **Tailwind CSS** | 3.4+ | Tokens en JIT, design system rápido, DX óptima. |
| Motion | **Framer Motion** | 11+ | Scroll-linked, layout animations, gestures. |
| Iconos | **Lucide React** | latest | Tree-shakeable, SVG inline. |
| Code highlighting | **Shiki** | latest | SSR sin JS adicional. |
| Search | **Pagefind** | 1.x | Estático, sin servidor, ~75KB. |
| Forms | **Astro Actions** o **Formspree** | — | Simple, sin backend custom. |
| Analytics | **Plausible** | self-hosted o cloud | Privacy-first, lightweight (<1KB). |
| Hosting | **Cloudflare Pages** o **Vercel** | — | Edge global, CI integrado, dominios SSL gratis. |
| CI | **GitHub Actions** | — | Lint, type, build, Lighthouse-CI, deploy preview. |

## 2. Por qué Astro

| Criterio | Astro | Next.js | SvelteKit | Vite + React |
| --- | --- | --- | --- | --- |
| Bundle JS por defecto | ~0 KB | ~80 KB | ~30 KB | ~150 KB |
| Islas / partial hydration | ✅ Nativo | ⚠️ App Router | ⚠️ Manual | ❌ |
| SSG simple | ✅ | ✅ | ✅ | ⚠️ |
| Velocidad de DX | Muy alta | Alta | Alta | Alta |
| Madurez ecosistema | Alta | Muy alta | Media | Alta |
| Fit con landing estático + islas animadas | **Óptimo** | Bueno | Bueno | Subóptimo |

> **Veredicto**: Astro es el fit ideal para una landing predominantemente estática con islas hidratadas (hero, demos, diagramas) y zero JS donde no se necesita.

### Alternativa secundaria: Next.js 14 (App Router + RSC)

Aceptable si el equipo tiene fuerte experiencia con React y planea features dinámicas futuras (dashboard, auth, etc). Penalización: bundle inicial mayor, complejidad mayor.

### Alternativa descartada: SvelteKit

Excelente técnicamente, pero ecosistema de Motion menor que Framer y curva de aprendizaje no justificada si el equipo es React-first.

## 3. Estructura del repositorio (a crear)

Decisión: **monorepo separado** del proyecto Cortex Python.

```
cortex-web/                      ← Nuevo repo (sugerencia: github.com/cortex/web)
├── apps/
│   ├── landing/                 ← Este proyecto
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── index.astro
│   │   │   │   ├── enterprise.astro
│   │   │   │   ├── changelog.astro
│   │   │   │   └── legal.astro
│   │   │   ├── sections/        ← Cada sección de la landing
│   │   │   │   ├── Hero.astro
│   │   │   │   ├── Problem.astro
│   │   │   │   ├── Solution.astro
│   │   │   │   ├── Architecture.astro
│   │   │   │   ├── Pillars.astro
│   │   │   │   ├── Demos.astro
│   │   │   │   ├── UseCases.astro
│   │   │   │   ├── Comparison.astro
│   │   │   │   ├── Install.astro
│   │   │   │   └── Community.astro
│   │   │   ├── components/      ← UI library
│   │   │   │   ├── Button.astro
│   │   │   │   ├── Card.astro
│   │   │   │   ├── CodeBlock.astro
│   │   │   │   ├── Callout.astro
│   │   │   │   └── islands/     ← Componentes React hidratados
│   │   │   │       ├── ArchitectureDiagram.tsx
│   │   │   │       ├── WebGraphDemo.tsx
│   │   │   │       ├── TerminalPlayer.tsx
│   │   │   │       └── ThemeToggle.tsx
│   │   │   ├── layouts/
│   │   │   │   └── Base.astro
│   │   │   ├── content/         ← Markdown source (changelog, legal)
│   │   │   ├── i18n/            ← Traducciones
│   │   │   │   ├── es.json
│   │   │   │   └── en.json
│   │   │   ├── styles/
│   │   │   │   ├── global.css
│   │   │   │   └── tokens.css   ← Generado de tokens.json
│   │   │   └── lib/
│   │   │       ├── analytics.ts
│   │   │       ├── seo.ts
│   │   │       └── motion.ts
│   │   ├── public/
│   │   │   ├── fonts/           ← Inter + JetBrains Mono self-hosted
│   │   │   ├── og/              ← Open Graph images
│   │   │   └── snapshots/       ← WebGraph JSON snapshot
│   │   ├── astro.config.mjs
│   │   ├── tailwind.config.cjs
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── docs/                    ← Sitio de documentación (ver web-docs)
├── packages/
│   ├── design-tokens/           ← tokens.json + Style Dictionary
│   ├── ui/                      ← Componentes compartidos (opt-in)
│   └── icons/                   ← (opcional) SVGs custom
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy-landing.yml
│       └── lighthouse.yml
├── pnpm-workspace.yaml
├── package.json
└── README.md
```

> El monorepo facilita compartir tokens de diseño entre landing y docs site sin duplicar trabajo.

## 4. Configuración Astro clave

`astro.config.mjs`:

```js
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import compress from 'astro-compress';

export default defineConfig({
  site: 'https://cortex.dev',
  output: 'static',
  integrations: [
    tailwind({ applyBaseStyles: false }),
    react(),
    sitemap(),
    compress({ HTML: true, CSS: true, Image: false, SVG: true }),
  ],
  i18n: {
    defaultLocale: 'es',
    locales: ['es', 'en'],
    routing: { prefixDefaultLocale: false },
  },
  vite: {
    ssr: { noExternal: ['framer-motion'] },
  },
});
```

## 5. Estrategia de hidratación

| Componente | Estrategia | Razón |
| --- | --- | --- |
| Hero (parallax sutil) | `client:load` | Animación de entrada inmediata |
| ThemeToggle | `client:idle` | Se necesita pronto pero no crítico |
| ArchitectureDiagram | `client:visible` | Carga cuando entra en viewport |
| WebGraphDemo | `client:visible` | Idem |
| TerminalPlayer | `client:visible` | Idem |
| Footer / static cards | Sin hidratación | HTML puro |

## 6. Performance budget

| Métrica | Presupuesto |
| --- | --- |
| LCP | < 1.8s |
| INP | < 200ms |
| CLS | < 0.05 |
| Total JS (initial) | < 100 KB gzipped |
| Total CSS | < 30 KB gzipped |
| Imágenes | AVIF/WebP, lazy, srcset |
| Fuentes | WOFF2, `font-display: swap`, preload 1-2 weights |
| Bundle por isla | < 50 KB cada una |

Lighthouse-CI corre en cada PR. Build falla si performance < 90 en mobile.

## 7. Internacionalización

- **Astro i18n** nativo (no `astro-i18next` salvo necesidad).
- **Default locale**: `es`. URL: `/`.
- **Inglés**: `/en/`.
- **Keys en JSON** en `src/i18n/{lang}.json`, accedidas via util `t(key)`.
- **`hreflang`** generado automáticamente con sitemap.

## 8. Accesibilidad — herramientas

- **axe DevTools** en QA manual.
- **eslint-plugin-jsx-a11y** en lint.
- **pa11y-ci** corriendo en CI sobre todas las rutas.
- **Storybook a11y addon** para componentes.

## 9. Forms y backend

**Formulario Enterprise**: usar **Astro Actions** (Astro 4.5+) + **Cloudflare Workers** para procesar, o externalizar a **Formspree** / **Resend** si no hay backend.

Validación: **Zod** schema compartido client/server.

Anti-spam: **Cloudflare Turnstile** (free, privacy-friendly).

## 10. SEO y OG

- **`<title>`** y **`<meta description>`** por página/sección, generados con helper `seo.ts`.
- **Open Graph images** generadas en build con **`@vercel/og`** o **Satori**.
- **Sitemap** automático.
- **`robots.txt`** servido en `public/`.
- **JSON-LD `Organization`** + **`SoftwareApplication`** schema.
- **`canonical`** correcto por idioma.

## 11. Analytics

- **Plausible** (recomendado).
- Eventos custom inyectados via util `analytics.ts`.
- Sin cookies, sin consent banner (Plausible no requiere).
- Si se elige GA4: implementar consent banner GDPR-compliant.

## 12. CI/CD pipelines

| Workflow | Trigger | Acción |
| --- | --- | --- |
| `ci.yml` | PR | Lint (eslint, stylelint), type-check (tsc), build, tests unitarios |
| `lighthouse.yml` | PR | Lighthouse-CI sobre preview deploy, falla si < threshold |
| `deploy-landing.yml` | merge a `main` | Build + deploy a Cloudflare Pages |
| `deploy-preview.yml` | PR | Deploy preview por branch |
| `a11y.yml` | nightly | pa11y-ci sobre prod |

## 13. Observabilidad post-deploy

- **Plausible** dashboard público para métricas básicas.
- **Cloudflare Analytics** para performance edge.
- **Sentry** (opcional) para errores JS en producción.
- **Logflare** o **Cloudflare Logs** para logs de Workers (forms).

## 14. Dependencias críticas (justificación)

| Lib | Tamaño aprox | Por qué se acepta |
| --- | --- | --- |
| Framer Motion | ~50 KB gz | Necesario para scroll-linked animations complejas |
| React | ~45 KB gz | Solo cargado en islas, no en HTML estático |
| Tailwind | 0 KB (purgeado) | Tree-shaken al build |
| Lucide | ~3 KB tree-shaken | Iconos críticos |
| Shiki | SSR-only | No agrega a bundle cliente |
| Pagefind | ~75 KB lazy | Solo en página de búsqueda |

## 15. Riesgos técnicos

| Riesgo | Mitigación |
| --- | --- |
| Framer Motion infla bundle | Tree-shake con `motion/react`, no `framer-motion` global |
| WebGraph requiere data del backend Cortex | Snapshot JSON estático regenerado semanalmente vía cron |
| Shiki SSR ralentiza build | Cache de highlights, precomputar en build |
| i18n duplica keys | Lint custom para detectar keys faltantes |

## 16. Definición de "production-ready"

La landing se considera production-ready cuando:

1. Lighthouse Mobile ≥ 90 en todas las páginas.
2. axe-core 0 errores críticos.
3. Cross-browser tested: Chrome, Firefox, Safari, Edge (2 versiones atrás).
4. Responsive testeado en: iPhone SE, iPhone 14 Pro, iPad, MacBook 13, monitor 27".
5. Analytics + error tracking activos.
6. Backup del repo + assets en al menos 2 ubicaciones.
7. Plan de actualización mensual definido.
