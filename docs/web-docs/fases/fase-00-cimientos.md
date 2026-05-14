---
title: Fase 00 — Cimientos
doc_type: phase
phase: 0
status: pending
depends_on: []
unlocks: [phase-01]
estimated_duration: 4 días-persona
---

# Fase 00 — Cimientos

## Objetivo

Dejar listo todo lo que **no se ve** pero **sin lo cual el proyecto docs no avanza**: scaffolding Astro Starlight, content schema, design tokens compartidos, CI, deploy preview.

> **Nota**: si la landing ya completó su Fase 00, este proyecto reutiliza el monorepo `cortex-web` y los `packages/design-tokens` ya configurados. Solo crea `apps/docs/`.

## Entregables

1. **`apps/docs/`** scaffolding Astro Starlight funcional.
2. **Content schema** Zod implementado y validable.
3. **Design tokens** docs heredados de landing + extensiones específicas.
4. **CI pipeline** docs (lint, schema validate, link check, build).
5. **Deploy preview** funcional en `docs.cortex.dev/preview-{branch}`.
6. **Subdomain** `docs.cortex.dev` configurado.
7. **Una página de prueba** ("Hello docs") que verifica el pipeline end-to-end.

## Tareas detalladas

### 0.1 Scaffold Astro Starlight (1 día)

```bash
cd cortex-web/apps
pnpm create astro@latest docs --template starlight --typescript strict --no-install --no-git
cd docs
pnpm install
```

- [ ] Verificar Starlight version ≥ 0.25 (i18n + versionado estables).
- [ ] Configurar `astro.config.mjs` según `05-stack-tecnico.md` §4.
- [ ] Configurar i18n base con `defaultLocale: 'es'` y `locales: { es, en }`.
- [ ] Crear `src/content/docs/es/index.mdx` con "Hello docs".
- [ ] Crear `src/content/docs/en/index.mdx` con mirror.
- [ ] `pnpm dev` arranca, accesible en localhost:4321.

### 0.2 Content schema con Zod (1 día)

`apps/docs/src/content/config.ts`:

```ts
import { z, defineCollection } from 'astro:content';
import { docsSchema } from '@astrojs/starlight/schema';

const cortexDocSchema = docsSchema({
  extend: z.object({
    doc_type: z.enum(['tutorial', 'how-to', 'reference', 'explanation', 'glossary', 'index', 'changelog']),
    summary: z.string().min(80).max(300),
    audience: z.array(z.enum(['developer', 'integrator', 'enterprise', 'contributor'])),
    tags: z.array(z.string()).min(3).max(10),
    since_version: z.string().regex(/^\d+\.\d+\.\d+$/),
    last_review: z.coerce.date(),
    status: z.enum(['draft', 'preview', 'stable', 'deprecated']),
    cli_commands: z.array(z.string()).optional(),
    mcp_tools: z.array(z.string()).optional(),
    related: z.array(z.string()).optional(),
    tutor: z.object({
      icon: z.string().optional(),
      one_liner: z.string().optional(),
      order: z.number().optional(),
      terminal_summary: z.string().optional(),
    }).optional(),
  }),
});

export const collections = {
  docs: defineCollection({ type: 'content', schema: cortexDocSchema }),
};
```

- [ ] Schema funciona — frontmatter inválido = build-fail.
- [ ] Test: crear página con frontmatter inválido, verificar error claro.

### 0.3 Design tokens (0.5 día)

- [ ] Reutilizar `packages/design-tokens/tokens.json` de landing (Fase 00 de landing).
- [ ] Agregar tokens específicos docs (ver `04-sistema-diseno.md` §2).
- [ ] Script `pnpm build:tokens` regenera Tailwind config + CSS variables.
- [ ] Inyectar tokens en `apps/docs/src/styles/docs.css`.

### 0.4 Customización visual Starlight (1 día)

Starlight permite override de:

- [ ] Logo (`logo: { light, dark }`).
- [ ] Colors (CSS variables override en `docs.css`).
- [ ] Fonts (preload Inter + JetBrains Mono).
- [ ] Custom components (slot replacement):
  - `Search` → componente custom con search semántico.
  - `SiteTitle` → con version badge.
  - `Footer` → custom con links.
- [ ] Tema claro/oscuro alineado con tokens.

### 0.5 Componentes custom esqueleto (0.5 día)

Crear archivos vacíos con TypeScript shells:

- [ ] `src/components/CommandReference.astro`.
- [ ] `src/components/McpToolReference.astro`.
- [ ] `src/components/ConfigReference.astro`.
- [ ] `src/components/VersionBadge.astro`.
- [ ] `src/components/Deprecated.astro`.
- [ ] `src/components/Term.astro`.

Cada uno con props tipadas y render mínimo. Implementación completa se hace en fases posteriores.

### 0.6 CI pipeline (0.5 día)

`.github/workflows/docs-ci.yml`:

```yaml
name: Docs CI
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter docs lint
      - run: pnpm --filter docs typecheck
      - run: pnpm --filter docs validate-content
      - run: pnpm --filter docs build
      - run: pnpm --filter docs check-links
```

- [ ] Script `validate-content`: corre Zod schema + checks adicionales.
- [ ] Script `check-links`: usa `markdown-link-check` o custom.
- [ ] Tests pasan con build vacío + Hello docs.

### 0.7 Deploy preview (0.5 día)

`.github/workflows/docs-deploy-preview.yml`:

- [ ] Build en PR → deploy a Cloudflare Pages como preview.
- [ ] Comment en PR con URL del preview.
- [ ] URL pattern: `docs-preview-{branch}.pages.dev` o `{branch}.docs.cortex.dev`.

### 0.8 Subdomain DNS (0.5 día)

- [ ] DNS `docs.cortex.dev` → Cloudflare Pages.
- [ ] SSL automático.
- [ ] Redirect: `cortex.dev/docs` → `docs.cortex.dev/`.

### 0.9 Página "Hello docs" (0.5 día)

`src/content/docs/es/index.mdx`:

```mdx
---
title: Documentación de Cortex
doc_type: index
summary: |
  Documentación oficial de Cortex — memoria corporativa y gobernanza
  para agentes IA.
audience: [developer, integrator, enterprise]
tags: [docs, overview, home]
since_version: 0.1.0
last_review: 2026-05-14
status: preview
---

# Bienvenido

Esta es la documentación oficial de Cortex.

## Quickstart

(en construcción)
```

- [ ] Renderiza correctamente en preview.
- [ ] Schema valida.
- [ ] Build pasa.

## Criterios de aceptación

- ✅ `pnpm dev` levanta el docs en < 5s.
- ✅ Página "Hello docs" se renderiza en `localhost:4321/es/`.
- ✅ Preview deploy funciona.
- ✅ CI verde: lint + typecheck + validate + build + linkcheck.
- ✅ DNS `docs.cortex.dev` responde 200.
- ✅ Lighthouse Mobile ≥ 95 (página vacía).
- ✅ Schema rechaza frontmatter inválido con error claro.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Starlight no permite override fácil de search | Build dropdown propio, no usar Search default |
| Tokens incompatibles con Starlight CSS | Override con specificity correcta; testear early |
| i18n config rota links cross-locale | Tests E2E que validan navegación entre idiomas |

## Siguiente fase

→ [Fase 01 — Migración de contenido](fase-01-migracion-contenido.md)
