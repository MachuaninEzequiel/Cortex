---
title: Fase 00 — Cimientos
doc_type: phase
phase: 0
status: pending
depends_on: []
unlocks: [phase-01]
estimated_duration: 5 días-persona
---

# Fase 00 — Cimientos

## Objetivo

Dejar listo todo lo que **no se ve** pero **sin lo cual el proyecto no avanza**: repositorio, scaffolding Astro, design tokens, CI, dominio, identidad visual y moodboard aprobado.

## Entregables

1. **Repositorio `cortex-web`** creado y configurado.
2. **Scaffolding Astro + Tailwind + React islands** funcional con un "hello world".
3. **Design tokens** (`tokens.json` + Style Dictionary) generando `tokens.css` + Tailwind config.
4. **CI pipeline** con lint, type-check, build, Lighthouse-CI configurado.
5. **Deploy preview** funcional en Cloudflare Pages (o Vercel).
6. **Dominio** registrado y SSL activo (`cortex.dev` o equivalente — a confirmar disponibilidad).
7. **Moodboard** Figma aprobado por dirección.
8. **Tipografía** Inter Variable + JetBrains Mono Variable self-hosted bajo `/public/fonts/`.
9. **Logo SVG vectorial** (derivado de `assets/logo.png`) en variantes light/dark.

## Tareas detalladas

### 0.1 Repositorio (1 día)

- [ ] Crear repo `cortex-web` (sugerencia: `github.com/MachuaninEzequiel/cortex-web` o `github.com/cortex/web`).
- [ ] Inicializar pnpm workspace con estructura monorepo (ver `04-stack-tecnico.md` §3).
- [ ] Configurar `.gitignore`, `LICENSE` (MIT, igual que Cortex), `README.md`.
- [ ] Branch protection en `main`: PR review obligatorio, status checks obligatorios.
- [ ] Crear `apps/landing/` y `packages/design-tokens/` vacíos.

### 0.2 Scaffolding Astro (1 día)

```bash
cd apps/landing
pnpm create astro@latest . --template minimal --typescript strict --no-install --no-git
pnpm install
pnpm add -D @astrojs/tailwind @astrojs/react @astrojs/sitemap astro-compress
pnpm add react react-dom framer-motion lucide-react
pnpm add -D @types/react @types/react-dom tailwindcss postcss autoprefixer
```

- [ ] `astro.config.mjs` con integraciones (ver `04-stack-tecnico.md` §4).
- [ ] Página `src/pages/index.astro` con "hello cortex".
- [ ] Layout `src/layouts/Base.astro` minimal con `<html lang>`, `<head>` con OG/SEO básico, slot.
- [ ] Smoke test: `pnpm dev` arranca, página visible en localhost:4321.

### 0.3 Design tokens (1 día)

- [ ] Crear `packages/design-tokens/tokens.json` con todos los tokens listados en `02-sistema-diseno.md` §2-5.
- [ ] Instalar Style Dictionary: `pnpm add -D style-dictionary -w`.
- [ ] Script `pnpm build:tokens` que genera:
  - `apps/landing/src/styles/tokens.css` (CSS variables).
  - `apps/landing/tailwind.config.cjs` (theme extension).
- [ ] Verificar que tokens están disponibles tanto en CSS (`var(--bg-base)`) como en Tailwind (`bg-bg-base`).

### 0.4 Tipografía (0.5 día)

- [ ] Descargar Inter Variable (.woff2) y JetBrains Mono Variable (.woff2) de [rsms.me/inter](https://rsms.me/inter/) y [jetbrains.com/lp/mono](https://www.jetbrains.com/lp/mono/).
- [ ] Colocar en `public/fonts/`.
- [ ] Definir `@font-face` en `src/styles/global.css` con `font-display: swap`.
- [ ] Preload en `Base.astro`:

```html
<link rel="preload" href="/fonts/Inter-Variable.woff2" as="font" type="font/woff2" crossorigin>
```

### 0.5 CI pipeline (1 día)

- [ ] `.github/workflows/ci.yml`:
  - Setup pnpm + Node 20.
  - `pnpm install --frozen-lockfile`.
  - `pnpm lint` (eslint + stylelint).
  - `pnpm typecheck` (tsc --noEmit).
  - `pnpm build`.
  - Upload artifact (dist).
- [ ] `.github/workflows/lighthouse.yml`:
  - Trigger en PR.
  - Usar `treosh/lighthouse-ci-action`.
  - Configurar `lighthouserc.json` con thresholds (Performance 90, A11y 95, BP 95, SEO 95).
- [ ] `.github/workflows/deploy-preview.yml`:
  - Build y deploy a Cloudflare Pages preview por branch.
  - Comment en PR con URL del preview.

### 0.6 Dominio y hosting (0.5 día)

- [ ] **Investigación**: ¿está disponible `cortex.dev`? ¿`getcortex.dev`? ¿`cortex.tools`?
- [ ] Compra de dominio (a decidir por dirección).
- [ ] Conectar a Cloudflare Pages (o Vercel).
- [ ] Configurar DNS, SSL, redirects `www →` apex.
- [ ] Verificar IPv6 + HTTP/3.

### 0.7 Moodboard e identidad visual (1 día)

- [ ] Crear Figma file: `Cortex Landing — Brand & Moodboard`.
- [ ] Tres páginas:
  1. **Moodboard**: capturas de linear.app, vercel.com, stripe.com, supabase.com, resend.com.
  2. **Identidad**: logos, colores, tipografía, tono.
  3. **Direcciones visuales** (3 propuestas): "Editorial sobrio", "Tech maximalista", "Sci-fi suave".
- [ ] **Decisión de dirección** en review con MachuaninEzequiel.
- [ ] Documento `02-sistema-diseno.md` se actualiza si la dirección elegida cambia tokens.

### 0.8 Logo SVG (0.5 día)

- [ ] Convertir `assets/logo.png` a SVG vectorial usando herramienta (Vector Magic, Illustrator, Inkscape).
- [ ] Producir variantes:
  - `logo-light.svg` (sobre fondo oscuro).
  - `logo-dark.svg` (sobre fondo claro).
  - `logo-mark.svg` (solo símbolo, sin texto).
  - `logo-mark-square.svg` (favicon source).
- [ ] Generar favicons:
  - `favicon.ico` (16, 32, 48).
  - `icon-192.png`, `icon-512.png`.
  - `apple-touch-icon.png` (180).
  - `manifest.webmanifest`.

## Criterios de aceptación

- ✅ `pnpm dev` arranca sin warnings en < 3s.
- ✅ `pnpm build` produce dist limpio en < 30s.
- ✅ Página "hello cortex" se ve correctamente con tipografía y colores tokens-driven.
- ✅ CI verde en PR de prueba.
- ✅ Preview deploy generado en PR.
- ✅ Lighthouse en preview ≥ 95 en todas las métricas (página vacía).
- ✅ Moodboard aprobado por dirección con sign-off explícito.

## Definición de "hecho"

Fase 00 está completa cuando:

- Existe un commit en `main` con el scaffolding final.
- Existe un tag `v0.0.1-scaffold`.
- Hay un Loom de 5 minutos mostrando el setup funcionando.
- El documento `02-sistema-diseno.md` está actualizado si hubo cambios de dirección.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Dominio deseado no disponible | Lista de 5 alternativas priorizadas pre-aprobada |
| Decisión visual demorada | Time-boxing 3 días para review de moodboard |
| Style Dictionary complica setup | Fallback: definir tokens directamente en `tailwind.config.cjs` + CSS variables |
| Cloudflare Pages tiene cuotas | Plan free es suficiente; Vercel Hobby como backup |

## Siguiente fase

→ [Fase 01 — Esqueleto](fase-01-esqueleto.md)
