---
title: Fase 09 — Performance, SEO y accesibilidad
doc_type: phase
phase: 9
status: pending
depends_on: [phase-08]
unlocks: [phase-10]
estimated_duration: 4 días-persona
---

# Fase 09 — Performance, SEO y accesibilidad

## Objetivo

Llevar la landing a niveles de excelencia técnica: **Lighthouse ≥ 95** en mobile, **WCAG AA** completo, **SEO** profesional con Open Graph dinámicas, sitemap, schema markup y i18n correctos.

## Entregables

1. **Lighthouse scores** ≥ 95 en Mobile (Performance, A11y, Best Practices, SEO).
2. **Web Vitals** dentro de presupuesto (LCP < 1.8s, INP < 200ms, CLS < 0.05).
3. **WCAG 2.1 AA** completo.
4. **SEO completo**: meta tags, OG dinámicas, sitemap, robots, JSON-LD.
5. **i18n correcto** con hreflang y URLs limpias.
6. **Pre-render Open Graph images** para todas las páginas.

## Tareas detalladas

### 9.1 Performance optimization (1.5 días)

#### Bundle audit

- [ ] Correr `astro build --verbose` y analizar tamaños.
- [ ] Identificar islas > 50KB y optimizar:
  - Tree-shake imports (`import { motion } from 'framer-motion'` específico).
  - Lazy-load sub-componentes.
  - Considerar reemplazos (ej. `clsx` en vez de `classnames`).
- [ ] Eliminar dependencias no usadas.

#### Imágenes

- [ ] Convertir todas las imágenes a **AVIF** (con fallback WebP, fallback JPG).
- [ ] Astro `<Image>` component con sizes correctos.
- [ ] `loading="lazy"` para todas las imágenes below-the-fold.
- [ ] `decoding="async"`.
- [ ] Pre-cargar la imagen LCP del hero con `<link rel="preload" as="image">`.

#### Fuentes

- [ ] Subset Inter y JetBrains Mono solo a latin (reduce 60-80% del tamaño).
- [ ] `font-display: swap`.
- [ ] Preload weights críticos (400, 600).

#### CSS

- [ ] Critical CSS inline en `<head>`.
- [ ] Resto cargado con `media="print" onload="this.media='all'"` trick (o Astro nativo).
- [ ] Purge Tailwind agresivo.

#### JavaScript

- [ ] Hidratación selectiva: `client:visible` por defecto, `client:idle` solo para imprescindibles.
- [ ] Compresión Brotli en server.
- [ ] HTTP/2 push deshabilitado (anti-patrón actual), HTTP/3 habilitado.

#### Web Vitals

| Métrica | Target | Cómo medirlo |
| --- | --- | --- |
| LCP | < 1.8s | PageSpeed Insights mobile |
| INP | < 200ms | Web-Vitals lib en producción |
| CLS | < 0.05 | Idem |
| FCP | < 1.2s | PSI |
| TTFB | < 600ms | Cloudflare analytics |

### 9.2 Accesibilidad WCAG AA (1.5 días)

#### Audit completo

- [ ] axe DevTools en cada página → 0 errores críticos.
- [ ] pa11y-ci en CI → bloqueante.
- [ ] WAVE chrome extension review.
- [ ] Manual keyboard-only test (Tab, Shift+Tab, Enter, Esc, ←→).

#### Checklist WCAG AA

| Requisito | Implementación |
| --- | --- |
| Contraste texto/fondo ≥ 4.5:1 (3:1 para large) | Verificado con tokens; ajustar `--fg-secondary` si necesario |
| Alt text en todas las imágenes | Auditoría manual + lint custom |
| Focus visible en todos los interactivos | Anillo accent definido en `02-sistema-diseno.md` §9 |
| Landmarks semánticos | `<header>`, `<main>`, `<nav>`, `<footer>`, `<section aria-labelledby>` |
| Headings jerárquicos sin saltos | H1 único, H2 por sección, H3 dentro, etc. |
| Form labels asociadas | `<label for>` correcto |
| Errores de form anunciados | `aria-live="polite"` en mensajes |
| Skip-to-content link | Primer focusable, visible en focus |
| Screen reader navegable | Tested con NVDA (Windows) o VoiceOver (macOS) |
| `prefers-reduced-motion` honored | Verificado en cada animación |
| Color no es único indicador | Iconos + texto, no solo color |
| Touch targets ≥ 44×44px | min-height en buttons |
| Idioma declarado | `<html lang>` correcto + `lang` en cambios |

#### ARIA específico

- [ ] `aria-label` en buttons sin texto (icon-only).
- [ ] `aria-current="page"` en nav link activo.
- [ ] `aria-expanded` en menús y accordions.
- [ ] `aria-controls` en tabs.
- [ ] `role="dialog"` y `aria-modal` en modales.
- [ ] `aria-live="polite"` para toasts.

### 9.3 SEO (1 día)

#### Meta tags por página

Helper `src/components/SEO.astro` recibe:

- `title` (formato: "Tema — Cortex")
- `description` (155-160 chars)
- `ogImage` (1200×630)
- `canonical` (URL absoluta)
- `lang` (es/en)
- `type` (`website` | `article`)

#### Open Graph dinámicas

- [ ] Generar OG images en build usando **Satori** o `@vercel/og`.
- [ ] Template OG por tipo:
  - Landing: logo grande + headline + URL.
  - Enterprise: logo + "Enterprise" badge + headline.
  - Changelog: logo + "v0.5.0 — What's new".
- [ ] Output en `public/og/{slug}.png`.

#### Sitemap

- [ ] Astro sitemap integration genera `sitemap-index.xml`.
- [ ] Incluye todas las páginas en ambos idiomas.
- [ ] Submitido a Google Search Console + Bing Webmaster Tools.

#### Robots.txt

```
User-agent: *
Allow: /

Sitemap: https://cortex.dev/sitemap-index.xml
```

#### JSON-LD Schema

Inyectar en `<head>` de landing:

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Cortex",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Windows, macOS, Linux",
  "description": "Memoria corporativa y gobernanza para agentes IA",
  "url": "https://cortex.dev",
  "softwareVersion": "0.5.0",
  "author": { "@type": "Person", "name": "MachuaninEzequiel" },
  "license": "https://opensource.org/licenses/MIT"
}
```

Y `Organization` schema separado.

#### Hreflang

```html
<link rel="alternate" hreflang="es" href="https://cortex.dev/" />
<link rel="alternate" hreflang="en" href="https://cortex.dev/en/" />
<link rel="alternate" hreflang="x-default" href="https://cortex.dev/" />
```

#### Search Console + Analytics

- [ ] Verificar dominio en Google Search Console (HTML tag).
- [ ] Verificar dominio en Bing Webmaster.
- [ ] Submit sitemap a ambos.

### 9.4 Best Practices Lighthouse (0.5 día)

| Item | Acción |
| --- | --- |
| HTTPS | Forzado por Cloudflare |
| HSTS | Header con max-age >= 1 year, includeSubDomains |
| No vulnerabilidades JS conocidas | `pnpm audit` clean en CI |
| Errores en consola | Cero en producción (audit final) |
| Imágenes correctamente dimensionadas | width/height attrs presentes |
| Pasivo event listeners | Verificar en touchstart/wheel |
| `unload` listeners | No usar (deprecated) |
| Permissions Policy | Restrictivo (`camera=(), microphone=()`, etc.) |
| CSP | Strict con nonces para scripts |

### 9.5 i18n verificación (0.5 día)

- [ ] Toggle ES/EN funciona en todas las páginas.
- [ ] Hreflang correcto en `<head>` de ambas versiones.
- [ ] URL canónicas por idioma.
- [ ] No mezcla de idiomas dentro de una página.
- [ ] Format locale-aware para números/fechas.
- [ ] Strings hardcoded en componentes son cero (lint custom).

## Criterios de aceptación

- ✅ Lighthouse Mobile en **todas las páginas**:
  - Performance ≥ 95
  - Accessibility ≥ 95
  - Best Practices ≥ 95
  - SEO ≥ 95
- ✅ Web Vitals dentro de presupuesto en CrUX (post-launch).
- ✅ pa11y-ci verde sin errores críticos.
- ✅ Tested con screen reader (NVDA o VoiceOver) — navegación clara.
- ✅ Lighthouse-CI bloqueando PRs que caigan thresholds.
- ✅ Search Console + Bing verificados.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Framer Motion infla bundle | Code-split por isla, lazy import |
| OG images no generan correctamente | Pre-generar en CI y commitear, no en build cada vez |
| Tests a11y false positives | Revisar manualmente cada warning |
| i18n keys faltantes | Lint custom + fallback a EN si key falta |

## Siguiente fase

→ [Fase 10 — Lanzamiento](fase-10-lanzamiento.md)
