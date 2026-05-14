---
title: Plan Maestro — Cortex Documentation Site
doc_type: plan
status: draft
owner: MachuaninEzequiel
created_at: 2026-05-14
audience: [dirección, ingeniería, devrel, escritores técnicos]
---

# Plan Maestro — Cortex Documentation Site

## Resumen ejecutivo

Este directorio contiene el **plan integral** para construir la **documentación oficial de Cortex** como sitio web, modelado a partir de la calidad y experiencia de **[docs.claude.com/claude-code](https://docs.claude.com/en/docs/claude-code/overview)**. La pieza debe ser **la fuente canónica** que un desarrollador consulta para:

- **Instalar y configurar** Cortex en su entorno.
- **Comprender** la arquitectura, el modelo tripartito, el vault, la memoria híbrida.
- **Aprender a usar** cada comando CLI, cada herramienta MCP, cada módulo (Autopilot, Enterprise, WebGraph).
- **Resolver dudas operativas** vía búsqueda full-text + búsqueda semántica.
- **Adoptar Cortex en una organización** con guías por persona (dev individual, equipo, enterprise lead).

> **Diferenciador clave de Cortex docs vs. otras docs:** el contenido es **consumible tanto por humanos (vía web) como por el `cortex tutor` (vía vault indexado + endpoint API)**. Es una **misma fuente de verdad, dos canales de acceso**. Ver [`03-integracion-tutor.md`](03-integracion-tutor.md) para el detalle del puente.

---

## Alcance del plan

Este plan describe **únicamente la planificación** (no implementación). El producto final será un sitio Markdown-first con:

- Una **fuente única** (`content/` en Markdown + frontmatter estructurado).
- **Dos consumidores**:
  - **Sitio web** estático (build con Astro Starlight u opción equivalente).
  - **Tutor de Cortex** (que ya existe en `cortex/tutor/`) extendido para consumir el mismo `content/` vía indexación semántica.
- **Una pipeline de validación** que asegura consistencia entre ambos consumidores.

El plan está dividido en **10 fases** secuenciales, con dependencias explícitas y criterios de aceptación.

---

## Índice de documentos

### Documentos transversales

| Documento | Contenido |
| --- | --- |
| [`00-vision-y-objetivos.md`](00-vision-y-objetivos.md) | Visión, audiencias (3 personas), objetivos, KPIs y métricas de adopción documental. |
| [`01-arquitectura-informacion.md`](01-arquitectura-informacion.md) | Site map completo: jerarquía de páginas, navegación lateral, breadcrumbs, taxonomía. |
| [`02-taxonomia-contenido.md`](02-taxonomia-contenido.md) | DocTypes (tutorial, how-to, reference, explanation — modelo Diátaxis), frontmatter schema, naming. |
| [`03-integracion-tutor.md`](03-integracion-tutor.md) | **Núcleo del plan.** Cómo el `cortex tutor` consume el contenido del site. API, indexación, sync. |
| [`04-sistema-diseno.md`](04-sistema-diseno.md) | Design tokens, componentes (callouts, code blocks, tabs, cards), tipografía, tema claro/oscuro. |
| [`05-stack-tecnico.md`](05-stack-tecnico.md) | Stack recomendado (Astro Starlight), alternativas, search (Pagefind/Algolia), hosting, CI/CD. |
| [`06-busqueda-navegacion.md`](06-busqueda-navegacion.md) | Búsqueda full-text + semántica, command palette, navegación contextual. |

### Fases de ejecución

| Fase | Documento | Objetivo |
| --- | --- | --- |
| 00 | [`fases/fase-00-cimientos.md`](fases/fase-00-cimientos.md) | Repositorio, scaffolding Astro Starlight, design tokens, CI, deploy preview. |
| 01 | [`fases/fase-01-migracion-contenido.md`](fases/fase-01-migracion-contenido.md) | Auditar y migrar `docs/guides/` existentes al nuevo schema. |
| 02 | [`fases/fase-02-paginas-core.md`](fases/fase-02-paginas-core.md) | Páginas core: Overview, Quickstart, Installation, Concepts, CLI Reference. |
| 03 | [`fases/fase-03-modulos-profundos.md`](fases/fase-03-modulos-profundos.md) | Memoria Híbrida, Vault, Autopilot, Enterprise, WebGraph, MCP. |
| 04 | [`fases/fase-04-ide-mcp.md`](fases/fase-04-ide-mcp.md) | Guías IDE (Pi, Claude Code, Cursor, VSCode, OpenCode, Codex) + MCP reference. |
| 05 | [`fases/fase-05-tutoriales-cookbooks.md`](fases/fase-05-tutoriales-cookbooks.md) | Tutoriales end-to-end y "recipes" (cookbook). |
| 06 | [`fases/fase-06-busqueda.md`](fases/fase-06-busqueda.md) | Pagefind + búsqueda semántica vía endpoint Cortex. |
| 07 | [`fases/fase-07-puente-tutor.md`](fases/fase-07-puente-tutor.md) | **Extensión del `cortex tutor`** para consumir el site (la pieza clave). |
| 08 | [`fases/fase-08-versionado-i18n.md`](fases/fase-08-versionado-i18n.md) | Versionado por release, internacionalización ES/EN. |
| 09 | [`fases/fase-09-lanzamiento.md`](fases/fase-09-lanzamiento.md) | QA, analytics, redirects, anuncio, post-launch. |

---

## Filosofía

### Modelo Diátaxis adaptado

La documentación se organiza siguiendo el [framework Diátaxis](https://diataxis.fr), con cuatro modos de contenido distintos:

1. **Tutorials** — Aprendizaje guiado paso a paso (orientado a estudiantes).
2. **How-to guides** — Recetas para resolver problemas concretos (orientado a tareas).
3. **Reference** — Información técnica precisa (orientado a información).
4. **Explanation** — Discusión, conceptos, "por qué" (orientado a comprensión).

Cada página declarará su `doc_type` en el frontmatter, permitiendo filtrado y ranking diferenciado tanto en búsqueda como en el tutor.

### Inspirado en docs.claude.com/claude-code

La referencia explícita es la documentación de Claude Code. Patrones que se replican:

- **Navegación lateral persistente** con secciones colapsables.
- **Code blocks con tabs** para mostrar el mismo comando en distintos shells.
- **Callouts tipados** (info, warning, danger, tip).
- **"On this page"** (right rail) con anchors de la página actual.
- **Breadcrumbs** que muestran ruta jerárquica.
- **Búsqueda global** invocable con `Cmd/Ctrl+K`.
- **Tema claro/oscuro** con respeto a `prefers-color-scheme`.
- **Versionado visible** en la barra superior.

---

## Principios rectores

1. **Una fuente, dos canales.** El Markdown del `content/` es consumido por el site **y** por el tutor. Cualquier cambio en el contenido se refleja automáticamente en ambos.
2. **Frontmatter como contrato.** Todo archivo declara `title`, `doc_type`, `summary`, `tags`, `audience`, `cli_commands`, `mcp_tools`. Sin esto, el documento no se publica ni se indexa.
3. **Examples ejecutables.** Los snippets de CLI se prueban en CI: si el ejemplo deja de funcionar, el build falla.
4. **Versionado por release de Cortex.** Cada versión publicada de `cortex-memory` tiene snapshot inmutable de docs.
5. **Búsqueda no opcional.** Pagefind (estático) + endpoint semántico (Cortex MCP) operativos desde el día 1.
6. **Linkable y compartible.** Cada heading H2/H3 tiene anchor automático y botón "copy link".
7. **Accesible.** WCAG AA, keyboard-only navegable, screen-reader friendly.

---

## Estado y siguiente paso

- **Estado**: `draft` — plan recién creado.
- **Siguiente paso**: leer [`00-vision-y-objetivos.md`](00-vision-y-objetivos.md), revisar [`03-integracion-tutor.md`](03-integracion-tutor.md) (decisión arquitectónica crítica), aprobar [Fase 00](fases/fase-00-cimientos.md).

---

## Relación con el resto de la documentación

- [`../web-landing/README.md`](../web-landing/README.md) — Plan de la landing pública (hermano de este).
- [`../canonical-documentation/`](../canonical-documentation/) — Esquema de DocTypes y routing canónico que **debe ser reutilizado**.
- [`../tutor/PLAN-TUTOR-HINT.md`](../tutor/PLAN-TUTOR-HINT.md) — Plan original del tutor CLI; punto de partida para la Fase 07.
- [`../guides/`](../guides/) — Contenido fuente a migrar en la Fase 01.
