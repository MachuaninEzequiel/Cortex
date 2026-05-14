---
title: Plan Maestro — Cortex Landing Web
doc_type: plan
status: draft
owner: MachuaninEzequiel
created_at: 2026-05-14
audience: [diseño, frontend, marketing, dirección]
---

# Plan Maestro — Cortex Landing Web

## Resumen ejecutivo

Este directorio contiene el **plan integral** para la **landing pública de Cortex** (no la documentación técnica — esa vive en [`docs/web-docs/`](../web-docs/README.md)). El objetivo de la landing es **convertir visitantes en adopters** mediante una narrativa visual, animada y altamente estética que comunique en menos de 60 segundos:

1. **Qué problema resuelve Cortex** (la *amnesia de sesión* de los agentes y la falta de gobernanza documental en proyectos asistidos por IA).
2. **Cómo lo resuelve** (memoria híbrida RRF + ciclo tripartito + Autopilot + Enterprise governance).
3. **Por qué importa** (decisiones trazables, conocimiento corporativo, agentes verificables).
4. **Cómo empezar** (instalación con `pipx`, integración IDE, primer `cortex setup full`).

La pieza **no es una doc-site**; es un **portfolio narrativo y experiencial** del producto, con foco en estética, animaciones, ilustraciones y diagramas interactivos. La doc técnica se enlaza desde la landing pero vive aparte.

---

## Alcance del plan

Este plan describe **únicamente la planificación**: no incluye código. La implementación se desarrollará en un repositorio o subdirectorio independiente (a decidir en [Fase 00](fases/fase-00-cimientos.md)). El presente plan cubre:

- Visión, audiencia, objetivos y métricas de éxito.
- Arquitectura de información (qué secciones y en qué orden).
- Sistema de diseño (tokens, componentes, motion, ilustraciones).
- Estrategia de contenido (copy completo por sección, tono, narrativa).
- Stack técnico recomendado y alternativas.
- **11 fases** secuenciales con criterios de aceptación, entregables, dependencias y riesgos.

---

## Índice de documentos

### Documentos transversales

| Documento | Contenido |
| --- | --- |
| [`00-vision-y-objetivos.md`](00-vision-y-objetivos.md) | Visión, personas objetivo, jobs-to-be-done, KPIs y métricas. |
| [`01-arquitectura-informacion.md`](01-arquitectura-informacion.md) | Site map, secciones, jerarquía, navegación, CTAs y orden narrativo. |
| [`02-sistema-diseno.md`](02-sistema-diseno.md) | Identidad visual, tipografía, paleta, tokens, grilla, componentes, motion. |
| [`03-estrategia-contenido.md`](03-estrategia-contenido.md) | Copy completo por sección, tono, glosario, microcopy y FAQ. |
| [`04-stack-tecnico.md`](04-stack-tecnico.md) | Stack recomendado (Astro + React islands + Framer Motion), alternativas, hosting, observabilidad. |

### Fases de ejecución

| Fase | Documento | Objetivo |
| --- | --- | --- |
| 00 | [`fases/fase-00-cimientos.md`](fases/fase-00-cimientos.md) | Repositorio, design tokens, CI, dominio, scaffolding. |
| 01 | [`fases/fase-01-esqueleto.md`](fases/fase-01-esqueleto.md) | Layout maestro, routing, header, footer, base de tema. |
| 02 | [`fases/fase-02-hero-problema.md`](fases/fase-02-hero-problema.md) | Hero animado, sección Problema/Solución. |
| 03 | [`fases/fase-03-arquitectura-interactiva.md`](fases/fase-03-arquitectura-interactiva.md) | Diagrama interactivo de la arquitectura de Cortex. |
| 04 | [`fases/fase-04-pilares-features.md`](fases/fase-04-pilares-features.md) | Pilares tecnológicos: Memoria Híbrida, Tripartito, Enterprise. |
| 05 | [`fases/fase-05-demos-interactivos.md`](fases/fase-05-demos-interactivos.md) | Demo WebGraph embebido + demo CLI animado + demo Autopilot. |
| 06 | [`fases/fase-06-casos-de-uso.md`](fases/fase-06-casos-de-uso.md) | Personas, historias, comparativa con/sin Cortex. |
| 07 | [`fases/fase-07-instalacion-cta.md`](fases/fase-07-instalacion-cta.md) | Wizard de instalación interactivo, CTAs, formularios. |
| 08 | [`fases/fase-08-animaciones-pulido.md`](fases/fase-08-animaciones-pulido.md) | Animaciones scroll-driven, micro-interacciones, transiciones. |
| 09 | [`fases/fase-09-performance-seo-a11y.md`](fases/fase-09-performance-seo-a11y.md) | Lighthouse ≥95, SEO, OG, sitemap, accesibilidad WCAG AA. |
| 10 | [`fases/fase-10-lanzamiento.md`](fases/fase-10-lanzamiento.md) | QA cross-browser, analytics, lanzamiento y post-launch. |

---

## Filosofía de diseño

Cortex es **gobernanza, memoria y disciplina** para agentes IA. La landing debe **transmitir esos valores estéticamente**:

- **Gobernanza** → estructura clara, jerarquía visual, datos concretos.
- **Memoria** → continuidad, capas, profundidad — visualmente: parallax, layering, transiciones suaves.
- **Disciplina** → tipografía técnica, mono spaced para código, grid riguroso.

El tono visual es **"editorial técnico moderno"**: oscuro por defecto (con toggle a claro), tipografía variable, ilustraciones isométricas o line-art, grafos en SVG animado, y *motion* sutil que premia el scroll pero no marea.

**Referencias estéticas** (a citar en el moodboard de Fase 00):
- [linear.app](https://linear.app) — densidad informativa, tipografía, dark mode.
- [vercel.com](https://vercel.com) — hero animado, gradientes técnicos.
- [stripe.com](https://stripe.com) — diagramas interactivos, scroll storytelling.
- [supabase.com](https://supabase.com) — feature cards, demos embebidas.
- [resend.com](https://resend.com) — minimalismo, tipografía variable, motion sutil.

---

## Principios rectores

1. **Estética primero, sin sacrificar performance.** Lighthouse Performance ≥ 95 es no-negociable.
2. **Animar para narrar, no para decorar.** Cada animación debe sumar a la historia.
3. **Mobile-first responsivo, pero diseñado en desktop.** El producto se evalúa en pantallas grandes.
4. **Accesibilidad WCAG AA mínima.** Color contrast, focus states, reduced-motion.
5. **Internacionalización planificada desde día 0.** Español como idioma primario, inglés como segundo idioma soportado.
6. **Demo > screenshot.** Si algo puede ser interactivo (ej. WebGraph, CLI), debe serlo.
7. **Trazabilidad con la doc técnica.** Cada feature linkea al apartado correspondiente en [`web-docs`](../web-docs/README.md).

---

## Estado y siguiente paso

- **Estado**: `draft` — plan recién creado, requiere revisión de dirección antes de iniciar Fase 00.
- **Siguiente paso**: leer [`00-vision-y-objetivos.md`](00-vision-y-objetivos.md), validar audiencia y KPIs, y aprobar el inicio de [Fase 00](fases/fase-00-cimientos.md).

---

## Relación con el resto de la documentación

- [`../web-docs/README.md`](../web-docs/README.md) — Plan del sitio de documentación técnica (hermano de este).
- [`../vision/ARQUITECTURA-GLOBAL-CORTEX.md`](../vision/ARQUITECTURA-GLOBAL-CORTEX.md) — Fuente de verdad arquitectónica que alimenta los diagramas.
- [`../enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md`](../enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md) — Material para la sección Enterprise de la landing.
- [`../vision/PLAN_CORTEX_MAXIMO_IMPACTO.md`](../vision/PLAN_CORTEX_MAXIMO_IMPACTO.md) — Insumo principal para la narrativa marketing.
