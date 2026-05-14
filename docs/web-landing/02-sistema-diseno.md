---
title: Sistema de diseño — Cortex Landing
doc_type: reference
status: draft
parent: README.md
---

# Sistema de Diseño — Cortex Landing

Este documento define **tokens, componentes, motion y guías** que rigen el aspecto visual de la landing. Es la **fuente única** durante la implementación; cualquier desviación debe documentarse aquí.

## 1. Principios de marca

| Principio | Aplicación visual |
| --- | --- |
| **Memoria y profundidad** | Layering, glassmorphism sutil, parallax leve. |
| **Gobernanza y rigor** | Grid de 12 columnas estricto, alineación tipográfica fuerte. |
| **Tecnología sin pretensión** | Tipografía variable, sin "tech-bro neon", paleta sobria. |
| **Confianza editorial** | Espacios generosos, jerarquía clara, lectura cómoda. |

## 2. Tokens de color

### Modo oscuro (default)

| Token | Valor | Uso |
| --- | --- | --- |
| `--bg-base` | `#0A0A0B` | Fondo principal |
| `--bg-elevated` | `#111114` | Tarjetas, modales |
| `--bg-subtle` | `#161618` | Code blocks, secciones alternas |
| `--fg-primary` | `#F4F4F5` | Texto principal |
| `--fg-secondary` | `#A1A1AA` | Texto secundario |
| `--fg-muted` | `#71717A` | Captions, helpers |
| `--border-subtle` | `#27272A` | Bordes hairline |
| `--border-strong` | `#3F3F46` | Bordes destacados |
| `--accent-primary` | `#FF6B1A` | Naranja Cortex (CTAs, hover) |
| `--accent-primary-soft` | `#FFB280` | Hover suave, gradientes |
| `--accent-secondary` | `#8B5CF6` | Violeta acento (Enterprise) |
| `--accent-tertiary` | `#14B8A6` | Verde teal acento (success/memory) |
| `--danger` | `#EF4444` | Errores, advertencias |
| `--warning` | `#F59E0B` | Avisos |
| `--success` | `#22C55E` | Confirmaciones |

### Modo claro

| Token | Valor |
| --- | --- |
| `--bg-base` | `#FFFFFF` |
| `--bg-elevated` | `#FAFAFA` |
| `--bg-subtle` | `#F4F4F5` |
| `--fg-primary` | `#09090B` |
| `--fg-secondary` | `#52525B` |
| `--fg-muted` | `#71717A` |
| `--border-subtle` | `#E4E4E7` |
| `--border-strong` | `#D4D4D8` |
| Accents | iguales que oscuro |

### Gradientes signature

| Token | Valor | Uso |
| --- | --- | --- |
| `--gradient-hero` | `radial-gradient(at 30% 20%, #FF6B1A33, transparent 60%), radial-gradient(at 70% 80%, #8B5CF633, transparent 60%)` | Fondo del hero |
| `--gradient-accent-line` | `linear-gradient(90deg, #FF6B1A, #8B5CF6, #14B8A6)` | Líneas decorativas |
| `--gradient-memory` | `linear-gradient(135deg, #14B8A6 0%, #8B5CF6 100%)` | Sección Memoria |

## 3. Tipografía

### Familias

- **Display / Headings**: **Inter Variable** (alternativa: Geist). Variable axis: weight 100-900, slant 0-12.
- **Body**: misma — Inter Variable.
- **Mono / Code**: **JetBrains Mono Variable** (alternativa: Geist Mono).

Self-hosted en `/fonts/` (no Google Fonts en producción por privacy + performance).

### Escala (clamp-fluida)

| Token | Mobile | Desktop | Uso |
| --- | --- | --- | --- |
| `text-display` | `clamp(2.5rem, 6vw, 4.5rem)` | 72px | Hero H1 |
| `text-title-1` | `clamp(2rem, 4vw, 3.5rem)` | 56px | H2 de sección |
| `text-title-2` | `clamp(1.5rem, 3vw, 2.5rem)` | 40px | H2 secundario |
| `text-title-3` | `clamp(1.25rem, 2vw, 1.75rem)` | 28px | H3 |
| `text-body-lg` | `1.125rem` | 18px | Párrafo lead |
| `text-body` | `1rem` | 16px | Body |
| `text-caption` | `0.875rem` | 14px | Captions |
| `text-mono-sm` | `0.875rem` | 14px | Inline code |

### Reglas

- Line-height **1.2** para títulos, **1.6** para body, **1.5** para code.
- Letter-spacing: **-0.02em** en headings ≥ 32px.
- Wrap balance (`text-wrap: balance`) en H1/H2.

## 4. Grid y espaciado

### Grid

- **12 columnas**, gap 24px en desktop, 16px en mobile.
- Max-width contenedor: **1280px**.
- Padding lateral: **24px** mobile, **48px** tablet, **80px** desktop.
- Secciones full-bleed permitidas en hero y diagramas.

### Espaciado (escala 4px)

`4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128 · 192`

Aliases:
- `space-xs: 8`, `space-sm: 12`, `space-md: 24`, `space-lg: 48`, `space-xl: 96`, `space-2xl: 192`.

## 5. Iconografía e ilustraciones

### Iconos

- **Lucide Icons** como base.
- Tamaño base: 20px (inline), 24px (UI), 32-48px (decorativo).
- Stroke 1.5px.

### Ilustraciones

- Estilo **isométrico técnico** o **line-art** monocromo + acento naranja.
- Generación recomendada: ilustraciones SVG vectoriales custom por el diseñador, **no stock**.
- Alternativa interim: ilustraciones generadas con **MidJourney** post-procesadas, o uso de **unDraw** customizado.

### Patrones decorativos

- **Grid de puntos** para fondos (svg pattern, opacity 0.05).
- **Líneas de conexión** estilo "circuit board" para sección arquitectura.
- **Glow blobs** (radial-gradient blurred) en hero.

## 6. Componentes core

| Componente | Variantes | Notas |
| --- | --- | --- |
| `<Button>` | primary, secondary, ghost, link | min-height 44px (touch target) |
| `<Card>` | default, glass, gradient-border, interactive | radius 16px |
| `<Callout>` | info, tip, warning, danger | iconos Lucide |
| `<CodeBlock>` | con tabs, con copy button, con highlight | usa `shiki` para SSR |
| `<Pill>` | default, accent, outline | usado para tags y filtros |
| `<Tabs>` | underline, segmented | keyboard-navegable |
| `<NavItem>` | default, active, dropdown | con focus visible |
| `<MetricCard>` | con número grande + label | para "<1ms latency", "85% coverage" |
| `<FeatureCard>` | icon + title + body + link | grid 2/3/4 columnas |
| `<DiagramCanvas>` | container responsive para SVG | con zoom/pan opcional |
| `<DemoFrame>` | iframe seguro con controles | para WebGraph |
| `<TerminalPlayer>` | replay de CLI con timing | usa asciinema o custom |

## 7. Motion

### Tokens

| Token | Valor | Uso |
| --- | --- | --- |
| `--ease-out-soft` | `cubic-bezier(0.16, 1, 0.3, 1)` | Entrances |
| `--ease-in-soft` | `cubic-bezier(0.7, 0, 0.84, 0)` | Exits |
| `--ease-spring` | `cubic-bezier(0.68, -0.55, 0.265, 1.55)` | Interacciones |
| `--duration-fast` | `150ms` | Hover, focus |
| `--duration-base` | `300ms` | Reveals, transitions |
| `--duration-slow` | `600ms` | Entrances grandes |
| `--duration-deliberate` | `900ms` | Storytelling |

### Reglas

1. **Toda animación respeta `prefers-reduced-motion`** y se reduce a fade-in 150ms o instantánea.
2. **Scroll-driven animations** se construyen con **Framer Motion** (scroll-linked) en islas hidratadas, o con CSS `animation-timeline: view()` cuando el soporte sea suficiente.
3. **Entrance staggered**: hijos entran con offset 50-100ms entre sí.
4. **Hover en cards**: lift 4px + glow border accent.
5. **CTA primario**: shimmer sutil en gradient al hover.
6. **No autoplay con audio**. Nunca.

### Animaciones signature

- **Hero**: typewriter del subtitle + parallax leve del blob gradient.
- **Arquitectura interactiva**: nodos pulsan en entrance, líneas se dibujan progresivamente con `stroke-dasharray`.
- **Memory layers**: 3 capas (episódica/semántica/enterprise) se separan en parallax al scroll.
- **Tripartito**: 3 columnas (Sync/SDDwork/Documenter) se conectan con flecha animada al activar.
- **WebGraph**: nodos con física suave (force-directed), responde al cursor con repel.
- **CLI player**: tipeo con timing realista, output progresivo, syntax highlighting en vivo.

## 8. Tema claro/oscuro

- **Default**: oscuro (alineado con público técnico).
- **Toggle**: switch en header.
- **Persistencia**: localStorage + respeto a `prefers-color-scheme` en primer load.
- **Transición**: 200ms con `view-transition-name` en navegadores soportados, sin transición en otros (no flash).

## 9. Estados accesibles

| Estado | Tratamiento |
| --- | --- |
| Focus visible | Anillo `--accent-primary` 2px + offset 2px en todos los interactivos |
| Hover | Cursor pointer + cambio sutil de color o lift |
| Active / Pressed | Scale 0.97 en buttons |
| Disabled | Opacity 0.5 + cursor not-allowed |
| Loading | Spinner mono o shimmer skeleton |
| Error | Color `--danger`, ícono, mensaje claro |

## 10. Responsive breakpoints

| Nombre | Min-width | Uso típico |
| --- | --- | --- |
| `xs` | 0 | Mobile portrait |
| `sm` | 640px | Mobile landscape |
| `md` | 768px | Tablet |
| `lg` | 1024px | Desktop pequeño |
| `xl` | 1280px | Desktop |
| `2xl` | 1536px | Desktop grande |

### Reglas

- **Mobile-first** al escribir CSS.
- **Right rail (TOC)** solo desde `xl`.
- **Diagrama interactivo** desde `md`; en `sm` se reemplaza por carrusel de imágenes.

## 11. Internacionalización visual

- **No hard-code de strings**. Todo texto via `i18n` con keys.
- **`lang` y `dir` correctos** en `<html>`.
- **Locale-aware** para números, fechas, RTL preparado (aunque V1 no incluya idiomas RTL).
- **Tipografía**: Inter cubre buen rango latino + cirílico + griego; revisar si se añade hebreo/árabe en futuro.

## 12. Entregables del sistema de diseño

Al final de la Fase 00 deben existir:

- ✅ Figma library con tokens, componentes y patterns (link en sección 13).
- ✅ `tokens.json` exportado en formato Style Dictionary.
- ✅ Tailwind config (o equivalente) generado desde tokens.
- ✅ Storybook con todos los componentes y estados.
- ✅ Guía de Motion (este documento, sección 7) implementada como hook `useMotion()`.

## 13. Recursos

- **Figma**: (placeholder — crear en Fase 00).
- **Moodboard**: (placeholder — Fase 00).
- **Brand assets**: `/c/Cortex/assets/logo.png` y derivados (SVG vectorial pendiente).
- **Inspiración**: linear.app, vercel.com, stripe.com, supabase.com, resend.com, railway.app.
