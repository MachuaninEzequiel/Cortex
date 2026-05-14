---
title: Arquitectura de Información — Cortex Docs
doc_type: reference
status: draft
parent: README.md
---

# Arquitectura de Información — Cortex Docs

## 1. Site map general

El sitio se estructura en **8 secciones top-level** + páginas auxiliares.

```
docs.cortex.dev
├── /                          ← Landing del docs (overview + cards)
├── /getting-started/
│   ├── /                      ← Quickstart (5 min)
│   ├── installation
│   ├── first-session
│   ├── connect-ide
│   └── troubleshooting
├── /concepts/                 ← Explicaciones (no how-to)
│   ├── overview
│   ├── hybrid-memory
│   ├── rrf-retrieval
│   ├── tripartite-cycle
│   ├── vault-structure
│   ├── episodic-vs-semantic
│   ├── enterprise-memory
│   ├── workspace-layout-v2
│   └── glossary
├── /guides/                   ← How-tos
│   ├── create-spec
│   ├── save-session
│   ├── search-memory
│   ├── promote-knowledge
│   ├── configure-enterprise
│   ├── customize-pipeline
│   ├── work-with-jira
│   ├── multiple-projects
│   └── ci-cd-integration
├── /cli/                      ← Reference comandos
│   ├── overview
│   ├── setup
│   ├── memory (search, remember, forget, context, stats)
│   ├── governance (create-spec, save-session, validate-docs, index-docs)
│   ├── enterprise (org-config, promote-knowledge, memory-report)
│   ├── autopilot (start, preflight, checkpoint, finish, doctor)
│   ├── ide (inject, sync-ide, install-skills)
│   ├── mcp (mcp-server)
│   ├── webgraph (serve, export)
│   ├── tutor (tutor, hint, ask)
│   └── tooling (doctor, agent-guidelines)
├── /mcp/                      ← MCP protocol reference
│   ├── overview
│   ├── tools/
│   │   ├── cortex_search
│   │   ├── cortex_context
│   │   ├── cortex_create_spec
│   │   ├── cortex_save_session
│   │   ├── cortex_sync_ticket
│   │   ├── cortex_validate_handoff
│   │   └── cortex_verify_session_claims
│   ├── autopilot-tools/
│   ├── server-setup
│   └── integration-guide
├── /ide/                      ← Guías por IDE
│   ├── overview
│   ├── pi
│   ├── claude-code
│   ├── cursor
│   ├── vscode
│   ├── opencode
│   └── codex
├── /autopilot/                ← Autopilot dedicado
│   ├── overview
│   ├── modes
│   ├── policies
│   ├── lifecycle
│   ├── handoff-schema
│   └── troubleshooting
├── /enterprise/               ← Enterprise dedicado
│   ├── overview
│   ├── org-yaml-reference
│   ├── presets
│   ├── promotion-pipeline
│   ├── retention-policies
│   ├── memory-report
│   ├── governance-profiles
│   ├── multi-tenant-teams
│   ├── compliance-guide
│   └── threat-model
├── /tutorials/                ← End-to-end tutoriales
│   ├── first-feature-with-cortex
│   ├── enterprise-rollout
│   ├── ci-integration-tutorial
│   └── custom-pipeline-stage
├── /reference/                ← Reference técnica
│   ├── configuration            (config.yaml + org.yaml + autopilot.yaml + workspace.yaml)
│   ├── frontmatter-schema       (DocTypes y campos)
│   ├── api/python-sdk           (cortex.AgentMemory público)
│   ├── api/models               (Pydantic models)
│   └── changelog
├── /community/                ← Comunidad
│   ├── contributing
│   ├── code-of-conduct
│   ├── support
│   └── showcase
└── /legal/
    ├── privacy
    ├── terms
    └── license
```

## 2. Diátaxis aplicado

Cada sección corresponde a un cuadrante del modelo Diátaxis:

| Cuadrante | Sección | Orientación |
| --- | --- | --- |
| **Tutorials** | `/getting-started/`, `/tutorials/` | Aprendizaje (estudiante) |
| **How-to guides** | `/guides/`, `/ide/`, `/community/contributing` | Tarea (problema concreto) |
| **Reference** | `/cli/`, `/mcp/`, `/reference/` | Información (lookup) |
| **Explanation** | `/concepts/`, `/autopilot/overview`, `/enterprise/overview` | Comprensión (mental model) |

Esta clasificación determina:

- **Tono y profundidad** (tutoriales son pacientes, reference es preciso).
- **Search ranking** (queries "cómo hago X" priorizan how-to; "qué es Y" priorizan explanations).
- **Estructura del frontmatter** (cada doctype tiene campos requeridos distintos).

## 3. Navegación

### 3.1 Header

```
[Cortex Logo] [v0.5.0 ▾]   Getting started · Concepts · Guides · CLI · MCP · IDE · Enterprise   [🔍 Search ⌘K] [GitHub] [🌐 ES/EN] [🌓]
```

- **Selector de versión**: dropdown con versiones publicadas.
- **Search global** invocable con `⌘/Ctrl+K` (Pagefind + semántico, ver [`06-busqueda-navegacion.md`](06-busqueda-navegacion.md)).
- **Toggle idioma** ES/EN.
- **Toggle tema** claro/oscuro.

### 3.2 Sidebar (lateral izquierdo)

- **Persistente** en desktop (`xl`+).
- **Colapsable** en tablet.
- **Drawer** en mobile (botón hamburger).
- **Estructura jerárquica** con secciones expandibles.
- **Indicador de página actual** + scroll automático para mantener visible.
- **Persistencia de estado expandido/colapsado** por sección.

### 3.3 Right rail ("On this page")

- **Visible en desktop** (≥ 1280px).
- **Lista de H2/H3 de la página actual** con anchor.
- **Scroll-spy**: highlight del heading visible.
- **Botón "Editar en GitHub"** al final.
- **Botón feedback** "¿Útil?" 👍 / 👎.

### 3.4 Breadcrumbs

Visible en todas las páginas (excepto landing del docs):

```
Docs · CLI · Memory · search
```

## 4. Página tipo

Cada página estándar tiene la siguiente estructura visual:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Header (sticky)                                                          │
├──────────┬──────────────────────────────────────────────┬────────────────┤
│          │  Breadcrumbs                                  │ On this page   │
│ Sidebar  │                                               │ - Section 1    │
│          │  # Title                                       │ - Section 2    │
│  Section │  > Summary (frontmatter)                       │ - Subsection   │
│  ├ Page  │                                               │ - Section 3    │
│  ├ Page  │  ## Heading                                    │                │
│  ├ Page  │  Content...                                    │ ─────          │
│          │                                               │ [Edit] [Útil?] │
│          │  ```bash                                       │                │
│          │  cortex search "query"                         │                │
│          │  ```                                           │                │
│          │                                               │                │
│          │  Next: [Página siguiente →]                   │                │
│          │  Prev: [← Página anterior]                    │                │
└──────────┴──────────────────────────────────────────────┴────────────────┘
```

## 5. Componentes de contenido recurrentes

Definidos en [`04-sistema-diseno.md`](04-sistema-diseno.md):

- `<Callout type="info|tip|warning|danger">` — boxes destacados.
- `<CodeBlock>` con tabs, filename, copy.
- `<CommandReference>` — para documentar comandos CLI con sintaxis, flags, ejemplos.
- `<McpToolReference>` — para documentar tools MCP con schema, ejemplos.
- `<ConfigReference>` — para documentar opciones de config.yaml/org.yaml.
- `<Cards>` — grid de cards para navegación lateral.
- `<Steps>` — pasos numerados con visual.
- `<Tabs>` — para variantes (Windows/Mac/Linux, CLI/SDK, etc.).
- `<VersionBadge>` — indica desde qué versión está disponible algo.

## 6. Versionado

- **Default**: última versión publicada (ej. `v0.5.0`).
- **URL**: `docs.cortex.dev/v0.5.0/...` para versiones específicas (canonical).
- **`docs.cortex.dev/latest/...`**: alias a la última.
- **`docs.cortex.dev/...`**: redirige a la última.
- **Banner**: si el usuario navega versión vieja, banner sugiere actualizar.
- **Búsqueda**: filtrada por versión activa.
- **Tutor**: el `cortex tutor` declara qué versión de docs consume.

## 7. i18n

- **Idiomas V1**: `es` (default, completo), `en` (completo).
- **URL**: `docs.cortex.dev/es/...` y `docs.cortex.dev/en/...`.
- **`docs.cortex.dev/...`**: redirige al idioma del browser (Accept-Language) si está disponible.
- **Fallback**: si una página no existe en el idioma seleccionado, fallback a `es` con banner sugiriendo contribuir traducción.
- **Hreflang** correcto en `<head>`.

## 8. Estados especiales

- **404**: página custom con búsqueda destacada + cards de páginas populares.
- **500**: página custom con link a GitHub para reportar.
- **Página sin contenido en idioma**: fallback + banner.
- **Versión obsoleta**: banner sugiriendo actualizar.

## 9. Flujos de navegación clave

### 9.1 Onboarding (Persona A)

```
/ (landing docs) → /getting-started/ → installation → first-session → connect-ide → [done]
```

Cada página tiene **CTA "Next →"** explícito.

### 9.2 Lookup (Persona B)

```
[Search ⌘K] "search" → resultados → /cli/memory/search → ejemplos → done
```

### 9.3 Enterprise eval (Persona C)

```
/ → /enterprise/overview → org-yaml-reference → presets → promotion-pipeline → compliance-guide → done
```

### 9.4 Tutor offline (Persona D)

```
$ cortex tutor ask "¿cómo configuro enterprise?"
→ tutor busca en docs indexado → retorna párrafo + link al docs web
```

Ver [`03-integracion-tutor.md`](03-integracion-tutor.md) para detalle técnico.

## 10. Footer

```
Cortex Docs — v0.5.0

DOCS                COMUNIDAD              PROYECTO              LEGAL
Getting started     GitHub                 Cortex.dev (landing)  Privacy
Concepts            Discord                Changelog             Terms
CLI                 X / Twitter            Roadmap               License (MIT)
Reference           Contributing           Status                Trademark

© 2026 Cortex · Hecho con ♥ en Argentina
```
