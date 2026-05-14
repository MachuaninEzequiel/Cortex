---
title: Fase 01 — Esqueleto y layout
doc_type: phase
phase: 1
status: pending
depends_on: [phase-00]
unlocks: [phase-02]
estimated_duration: 4 días-persona
---

# Fase 01 — Esqueleto y layout

## Objetivo

Construir el **chassis** de la landing: header, footer, layout base, routing, tema claro/oscuro, i18n y todos los componentes UI primitivos. Al terminar esta fase, la landing tiene su forma pero sin contenido narrativo aún.

## Entregables

1. **Layout base** `Base.astro` con header sticky + footer + slot principal.
2. **Header funcional** con navegación, CTA, theme toggle, language toggle.
3. **Footer** con todas las columnas y links del IA (`01-arquitectura-informacion.md` §4).
4. **Theme system** claro/oscuro con persistencia localStorage.
5. **i18n base** con páginas en `/` (es) y `/en/`.
6. **Routing** de las 4 páginas: `/`, `/enterprise`, `/changelog`, `/legal`.
7. **Componentes primitivos** en Storybook: Button, Card, CodeBlock, Callout, Pill, Tabs.
8. **Sistema de anchors** con scroll suave y deep-linking.

## Tareas detalladas

### 1.1 Layout base (1 día)

`src/layouts/Base.astro`:

```astro
---
import Header from '~/components/Header.astro';
import Footer from '~/components/Footer.astro';
import SEO from '~/components/SEO.astro';

interface Props {
  title: string;
  description: string;
  ogImage?: string;
  lang?: 'es' | 'en';
}
const { title, description, ogImage, lang = 'es' } = Astro.props;
---
<!DOCTYPE html>
<html lang={lang} class="scroll-smooth">
  <head>
    <SEO {title} {description} {ogImage} />
    <link rel="preconnect" href="https://plausible.io" />
    <script is:inline>
      /* Theme bootstrap: aplica clase ANTES de hidratar React para evitar FOUC */
      const t = localStorage.getItem('cortex-theme')
        ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.classList.add(t);
    </script>
  </head>
  <body class="min-h-screen bg-bg-base text-fg-primary antialiased">
    <Header />
    <main><slot /></main>
    <Footer />
  </body>
</html>
```

- [ ] Implementar `<SEO>` con title/desc/og/canonical/hreflang.
- [ ] Verificar que el theme bootstrap no causa FOUC.

### 1.2 Header (1 día)

- [ ] `src/components/Header.astro` con:
  - Logo + texto "Cortex" (mark + wordmark).
  - Nav links según `01-arquitectura-informacion.md` §3.
  - CTA primario `[Probar Cortex →]`.
  - `<ThemeToggle client:idle />` (isla React).
  - `<LangToggle client:idle />` (isla React).
- [ ] Sticky + blur backdrop en scroll (`backdrop-blur` Tailwind).
- [ ] Mobile menu (hamburger → `<Sheet>` o drawer).
- [ ] Cambio de tema en scroll: detecta sección actual via Intersection Observer; ajusta color del header.

### 1.3 Footer (0.5 día)

- [ ] `src/components/Footer.astro` con 4 columnas (Producto, Recursos, Comunidad, Legal).
- [ ] Mention "v0.5.0" auto-leído desde `package.json` de Cortex (script de build que copia versión).
- [ ] Iconos sociales (GitHub, X/Twitter, Discord si aplica).
- [ ] Copyright dinámico (año actual).

### 1.4 Theme toggle (0.5 día)

`src/components/islands/ThemeToggle.tsx`:

- [ ] Estados: `light`, `dark`, `system`.
- [ ] Iconos Lucide: `Sun`, `Moon`, `Monitor`.
- [ ] Persiste en `localStorage['cortex-theme']`.
- [ ] Emite evento `theme-change` para analytics.
- [ ] Animación con `view-transition-name: theme` cuando el navegador soporte.

### 1.5 Language toggle (0.5 día)

- [ ] `src/components/islands/LangToggle.tsx` con select `ES | EN`.
- [ ] Cambia URL: `/` ↔ `/en/`.
- [ ] Persiste preferencia (`cortex-lang`).
- [ ] `hreflang` correcto en `<head>`.

### 1.6 i18n setup (0.5 día)

- [ ] Configurar Astro i18n en `astro.config.mjs` (ya hecho en Fase 00).
- [ ] Crear `src/i18n/es.json` y `src/i18n/en.json` con keys iniciales (microcopy de `01-arquitectura-informacion.md` §11).
- [ ] Helper `t(key, lang)` en `src/lib/i18n.ts`.
- [ ] Test: cambio de idioma actualiza header y footer.

### 1.7 Routing de páginas (0.5 día)

- [ ] `src/pages/index.astro` — landing (single-page).
- [ ] `src/pages/enterprise.astro` — Enterprise page.
- [ ] `src/pages/changelog.astro` — Changelog (placeholder).
- [ ] `src/pages/legal.astro` — Legal (placeholder).
- [ ] `src/pages/en/index.astro`, `src/pages/en/enterprise.astro`, etc. (espejos).
- [ ] Verificar que cada página tiene su `<SEO>` correcto.

### 1.8 Componentes primitivos + Storybook (1 día)

Crear y documentar en Storybook:

- [ ] `<Button>` con variants `primary | secondary | ghost | link` y sizes `sm | md | lg`.
- [ ] `<Card>` con variants `default | glass | gradient-border | interactive`.
- [ ] `<CodeBlock>` con prop `code`, `lang`, `filename`, `showCopy`, `tabs`. Usa Shiki SSR.
- [ ] `<Callout>` con variants `info | tip | warning | danger`.
- [ ] `<Pill>` con variants `default | accent | outline`.
- [ ] `<Tabs>` keyboard-navegable (← → para cambiar, Home/End para extremos).
- [ ] Storybook addon a11y verde para cada componente.

### 1.9 Scroll y anchors (0.5 día)

- [ ] Scroll suave global (`scroll-behavior: smooth` + offset por header sticky).
- [ ] Util `scrollToAnchor(id)` en `src/lib/scroll.ts`.
- [ ] Detección de anchor activo via IntersectionObserver.
- [ ] Update de `history` con `replaceState` (sin saltar) al pasar de sección.

## Criterios de aceptación

- ✅ `/` renderiza header + footer + main vacío sin errores.
- ✅ Theme toggle cambia colores sin FOUC.
- ✅ Lang toggle cambia idioma de header/footer.
- ✅ Mobile menu funciona en breakpoint `< sm`.
- ✅ Todos los componentes primitivos en Storybook con a11y verde.
- ✅ Lighthouse Mobile ≥ 95 (página vacía).
- ✅ Bundle JS inicial < 30 KB (sin secciones aún).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| FOUC al cambiar tema | Theme bootstrap inline ANTES de cargar CSS |
| Hreflang incorrecto | Test E2E que valida `<link rel="alternate">` en todas las páginas |
| Storybook lento de configurar | Usar template oficial Astro + Storybook (existe integración) |

## Siguiente fase

→ [Fase 02 — Hero y problema](fase-02-hero-problema.md)
