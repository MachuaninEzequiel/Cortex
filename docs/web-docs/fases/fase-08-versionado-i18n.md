---
title: Fase 08 — Versionado e Internacionalización
doc_type: phase
phase: 8
status: pending
depends_on: [phase-07]
unlocks: [phase-09]
estimated_duration: 5 días-persona
---

# Fase 08 — Versionado e Internacionalización

## Objetivo

Llevar el docs a un nivel **maduro de gobernanza editorial**: versionado por release, traducción al inglés, gestión de contenido obsoleto, redirects.

## Entregables

1. **Versionado funcional** con sub-routes `/v{version}/`.
2. **Banner de versión obsoleta** automático.
3. **Selector de versión** en header.
4. **Inglés completo** — todas las páginas de V1 traducidas.
5. **Hreflang** correcto.
6. **Redirects** desde URLs antiguas.

## Sub-fase A — Versionado

### A.1 Arquitectura de versionado

#### Decisión: sub-route vs branches

| Opción | Pros | Contras |
| --- | --- | --- |
| **Sub-route** `/v0.5.0/`, `/v0.4.0/` | Único deploy, fácil link cross-version | Más build time |
| **Branches** | Builds independientes | Complica deploys |
| **Subdomain** `v0-4.docs.cortex.dev` | Aislado | DNS overhead, SEO disperso |

**Decisión recomendada**: **sub-route**. Astro maneja bien múltiples versiones en un build.

### A.2 Implementación

#### Estructura

```
apps/docs/src/content/docs/
├── es/
│   ├── (current: contenido actual = v0.5.0 latest)
│   └── v0.4.0/                ← Snapshots inmutables
│       ├── getting-started/
│       └── ...
└── en/
    └── (mirror)
```

Decisión alternativa: **rama git por versión** + script de snapshot:

- Branch `docs-v0.5.0` se freezea al lanzar v0.5.0.
- Build pipeline incluye contenido de todas las branches versionadas.

Recomendado: combinar ambas — `main` es la latest, branches versionadas se freezean.

### A.3 Routing

URL pattern:

- `docs.cortex.dev/es/...` → latest (alias a v0.5.0 actual).
- `docs.cortex.dev/v0.5.0/es/...` → versión 0.5.0 (canonical).
- `docs.cortex.dev/v0.4.0/es/...` → versión 0.4.0.
- `docs.cortex.dev/latest/es/...` → redirect a la última.

### A.4 Selector de versión

`<VersionSwitcher>` en header:

- Dropdown con todas las versiones disponibles.
- Versión actual destacada.
- Versiones obsoletas en sección "Versiones anteriores".
- Click → navega a la misma página en otra versión (si existe).
- Si la página no existe en la otra versión, navega a `/v{X}/{lang}/` (landing).

Data en `public/versions.json` generado en build:

```json
{
  "latest": "0.5.0",
  "versions": [
    { "id": "0.5.0", "released_at": "2026-05-14", "status": "stable" },
    { "id": "0.4.0", "released_at": "2026-02-10", "status": "deprecated" },
    { "id": "0.3.0", "released_at": "2025-11-20", "status": "deprecated" }
  ]
}
```

### A.5 Banner de versión obsoleta

Si el usuario navega versión != latest:

```
[i] Estás viendo documentación de v0.4.0 (deprecated).
    Última versión: v0.5.0.
    [Ver esta página en v0.5.0 →] (si existe)
```

### A.6 Página `/v{X}/{lang}/changelog`

Cada versión tiene su changelog accesible.

## Sub-fase B — Internacionalización (i18n)

### B.1 Estrategia de traducción

| Tipo de contenido | Estrategia |
| --- | --- |
| **Páginas core** (getting-started, concepts, CLI) | Traducción humana revisada |
| **Reference** (org.yaml, MCP tools) | Traducción auto-asistida (DeepL/GPT) + revisión humana |
| **Tutoriales** | Traducción humana, ajustada culturalmente |
| **Cookbook** | Idem |
| **Glossary** | Traducción humana, términos consistentes |

### B.2 Pipeline de traducción

Tooling:

- [ ] **DeepL** o **GPT-4** para primer pass automático.
- [ ] **Crowdin** o **Lokalise** para gestión colaborativa (opcional V1.1).
- [ ] Para V1, scripts internos:
  - `pnpm translate:auto` — corre auto-translate sobre archivos sin contraparte EN.
  - `pnpm translate:diff` — diff de cambios entre ES y EN (detectar drift).

#### Workflow

```
1. Dev escribe doc en ES (idioma primario).
2. Script auto-genera draft EN.
3. Revisor humano edita EN draft (puede ser el mismo dev si sabe inglés).
4. PR con ambos idiomas.
5. CI valida ambos versions.
```

### B.3 Hreflang

En cada página `<head>`:

```html
<link rel="alternate" hreflang="es" href="https://docs.cortex.dev/v0.5.0/es/cli/search" />
<link rel="alternate" hreflang="en" href="https://docs.cortex.dev/v0.5.0/en/cli/search" />
<link rel="alternate" hreflang="x-default" href="https://docs.cortex.dev/v0.5.0/es/cli/search" />
```

### B.4 Fallback idiomático

Si una página existe en ES pero no en EN:

- En la página EN, mostrar banner:
  ```
  This page is not available in English yet.
  [Ver en español →] [Contribuir traducción →]
  ```

CI alerta (no bloquea) si páginas EN faltantes > 5% del total ES.

### B.5 Glossary cross-language

Términos consistentes entre ES y EN:

| ES | EN |
| --- | --- |
| Memoria episódica | Episodic memory |
| Memoria semántica | Semantic memory |
| Vault | Vault (no traducir) |
| Especificación técnica | Technical spec |
| Sesión | Session |
| Promotion | Promotion (no traducir) |
| Tópico (tutor) | Topic |

Mantener `glossary.{es,en}.json` para auto-validación.

## Tareas detalladas

### 8.1 Versionado — implementación (1.5 días)

- [ ] Estructura de directorios versionados.
- [ ] Script de snapshot al lanzar versión.
- [ ] Routing en Astro.
- [ ] `<VersionSwitcher>` componente.
- [ ] Banner de versión obsoleta.
- [ ] Tests E2E navegando entre versiones.

### 8.2 i18n — traducción (3 días)

- [ ] Setup pipeline de traducción (DeepL/GPT API key opcional).
- [ ] Auto-translate de páginas migradas en Fase 01 (placeholders EN se vuelven drafts).
- [ ] Revisión humana de:
  - 6 páginas getting-started.
  - 9 páginas concepts.
  - 35 páginas CLI (sample 10 revisadas a fondo).
  - 8 páginas enterprise.
  - Otras priorizadas.
- [ ] Tests de hreflang correctos.

### 8.3 Redirects (0.5 día)

`apps/docs/public/_redirects` (Cloudflare Pages format):

- [ ] Old URL → new URL si renombramos páginas.
- [ ] `/` → `/es/` (auto detección de idioma).
- [ ] `/v0.5.0/` → `/v0.5.0/es/`.

## Criterios de aceptación

- ✅ Versionado funcional: puedo navegar v0.5.0 y v0.4.0.
- ✅ Selector de versión cambia entre versiones.
- ✅ Banner aparece en versiones obsoletas.
- ✅ ≥ 95% de páginas críticas (getting-started, concepts, CLI top 10) en EN.
- ✅ Hreflang correcto en todas las páginas.
- ✅ Fallback funcional para páginas no traducidas.
- ✅ Tests E2E verdes.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Versionado infla build time | Limitar a 3 versiones activas; older = archived static |
| Traducción auto introduce errores técnicos | Revisión humana mandatoria; glossary canónico |
| Mantenimiento dual-language es costoso | Priorizar ES; EN tolerable con drift hasta 10% |
| Redirects rotos por URL changes | Linkcheck cross-version en CI |

## Siguiente fase

→ [Fase 09 — Lanzamiento](fase-09-lanzamiento.md)
