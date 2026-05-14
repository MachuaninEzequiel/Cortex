---
title: Fase 09 — Lanzamiento y mantenimiento
doc_type: phase
phase: 9
status: pending
depends_on: [phase-08]
unlocks: []
estimated_duration: 3 días-persona + monitoring continuo
---

# Fase 09 — Lanzamiento y mantenimiento

## Objetivo

Cerrar el proyecto docs con **lanzamiento técnico** sólido, **comunicación coordinada** con la landing, y un **plan de mantenimiento** sustentable.

A diferencia de la landing (que se lanza una vez), el **docs evoluciona** continuamente con cada release. Esta fase define el **régimen continuo** de mantenimiento.

## Entregables

1. **QA exhaustivo** previo al launch.
2. **Lanzamiento sincronizado** con la landing.
3. **Plan de mantenimiento** documentado.
4. **CI checks continuos** (link check, freshness, coverage).
5. **Roadmap V1.1** definido en base a primeros feedbacks.

## Tareas detalladas

### 9.1 QA pre-launch (1 día)

#### Coverage checks

- [ ] `pnpm check-cli-coverage` reporta ≥ 95%.
- [ ] `pnpm check-mcp-coverage` reporta 100%.
- [ ] `pnpm check-frontmatter-completeness` reporta 100%.
- [ ] Linkcheck verde (cero links rotos).
- [ ] Schema validation: cero errores.

#### Manual review

- [ ] Lectura tester #1 (Persona A — Junior dev): completa getting-started en ≤ 30 min.
- [ ] Lectura tester #2 (Persona B — Senior dev): encuentra reference de comando específico en < 60s vía búsqueda.
- [ ] Lectura tester #3 (Persona C — Enterprise lead): completa enterprise quickstart en ≤ 60 min.
- [ ] Lectura tester #4 (Persona D — el tutor): `cortex tutor ask` retorna respuestas correctas para 17/20 queries del bench.

#### Performance

- [ ] Lighthouse Mobile ≥ 90 en:
  - Landing del docs (`/`).
  - Top 5 páginas más visitadas (Quickstart, CLI search, etc.).
- [ ] Bundle JS inicial < 50 KB.
- [ ] Pagefind index < 500 KB.

#### Accesibilidad

- [ ] axe-core: cero errores críticos.
- [ ] pa11y-ci verde.
- [ ] Test manual con NVDA/VoiceOver en 3 páginas.

#### Cross-browser

- [ ] Chrome, Edge, Firefox, Safari últimas 2 versiones.
- [ ] Search overlay funciona en todos.
- [ ] Mobile responsive verificado.

### 9.2 Lanzamiento coordinado (0.5 día)

#### Pre-launch (día -1)

- [ ] DNS final `docs.cortex.dev` apunta a Cloudflare Pages.
- [ ] SSL automático activo.
- [ ] Production deploy de v0.5.0 build.
- [ ] Cortex MCP server público activo y healthy.
- [ ] Sitemap submitido a Google Search Console + Bing.
- [ ] Cache CDN warm-up.

#### Launch (día 0)

- [ ] Coordinar con [Fase 10 de la landing](../../web-landing/fases/fase-10-lanzamiento.md):
  - Landing apunta a `docs.cortex.dev` ya activo.
  - Anuncios mencionan ambas URLs.

#### Post-launch monitoring (días 1-7)

- [ ] Daily check de Plausible: pageviews, top pages, top search queries.
- [ ] Search queries sin resultados: revisar dashboard.
- [ ] 404 errors: investigar y crear redirects.
- [ ] Feedback widget (👍/👎): revisar páginas con muchas 👎.
- [ ] Issues en GitHub etiquetadas `docs`: responder en <24h.

### 9.3 Plan de mantenimiento continuo (0.5 día)

#### Cadencia con releases de Cortex

| Cuando ocurre… | Acción en docs |
| --- | --- |
| Cortex saca v0.5.1 (patch) | Update `since_version` si hay nuevas features; sin re-snapshot |
| Cortex saca v0.6.0 (minor) | Update páginas afectadas; snapshot v0.5.0 inmutable |
| Cortex saca v1.0.0 (major) | Migration guide específica + docs review completo |
| Comando nuevo agregado | Página nueva en `/cli/`; failover de coverage check |
| Comando deprecado | Marcar `status: deprecated`; banner |
| MCP tool nueva | Página nueva en `/mcp/tools/`; coverage check |
| Schema config cambia | Update `/reference/configuration.mdx` |

#### CI automation

CI workflows que corren continuamente:

- [ ] **Nightly link check**: detecta links rotos cuando target page se mueve.
- [ ] **Nightly freshness check**: alerta sobre `last_review > 6 meses` con `status: stable`.
- [ ] **Coverage check**: alerta si nuevo comando `cortex --help` no está documentado.
- [ ] **A11y check**: pa11y nightly.
- [ ] **Lighthouse weekly**: regression detection.
- [ ] **Search analytics weekly**: top queries sin resultados como issues automáticos.

#### Cadencia humana

| Frecuencia | Tarea |
| --- | --- |
| Semanal | Revisar issues GH `docs`, responder o asignar |
| Semanal | Top 10 queries sin resultados → backlog |
| Mensual | Lighthouse + a11y audit con humano |
| Trimestral | Re-screenshot IDE pages |
| Semestral | Review completo de páginas `status: stable` con `last_review` antiguo |
| Por release | Update `since_version` y snapshot |

#### Roles y responsabilidad

| Rol | Responsabilidad |
| --- | --- |
| Maintainer principal | Reviews de PR, releases, decisiones de estructura |
| Contributors | Issues, PRs, mejoras menores |
| Translator(s) | EN translations |
| Community | Reports de bugs, feedback |

### 9.4 Roadmap V1.1 (0.5 día)

Recopilar feedback de primeras 4 semanas → priorizar:

#### Posibles V1.1 features

- [ ] **Blog técnico** — deep dives, release notes detalladas.
- [ ] **Showcase** — proyectos usando Cortex con casos reales.
- [ ] **Interactive examples** — playground en el browser.
- [ ] **MCP tool playground** — invocar tools desde el browser (vía proxy).
- [ ] **Algolia DocSearch** opcional (si Pagefind se queda chico).
- [ ] **More languages** — PT-BR, FR.
- [ ] **PDF export** por sección.
- [ ] **AI-powered Q&A** integrado en el sitio (no solo tutor CLI).
- [ ] **Video tutorials** embebidos.

#### Priorización criteria

- Frecuencia de feedback ("X persona pidió esto").
- Impacto en métricas (Search hits, Time-on-page).
- Costo de implementación.
- Alineación con el core de Cortex.

### 9.5 Comunicación post-launch (0.5 día)

#### Quickstart guides públicos

- [ ] Blog post: "How we built the Cortex docs".
- [ ] Tweet thread: features de la docs (search semántico, tutor offline).
- [ ] Dev.to: arquitectura técnica del docs-site.

#### Post-mortem interno

Documento `docs/web-docs/post-mortem-launch.md`:

- [ ] Métricas vs objetivos (de `00-vision-y-objetivos.md` §6).
- [ ] Qué funcionó.
- [ ] Qué no funcionó.
- [ ] Bugs encontrados.
- [ ] Lecciones aprendidas.
- [ ] Plan iteración V1.1.

## Criterios de aceptación

- ✅ Lanzamiento sin downtime.
- ✅ Métricas semana 1:
  - Pageviews ≥ 3,000 (atribuible a launch).
  - Search queries ≥ 500.
  - Tutor downloads (via docs-sync logs) ≥ 50.
- ✅ Cero links rotos en producción.
- ✅ Plan de mantenimiento documentado y socializado.
- ✅ CI automation activa.
- ✅ Post-mortem publicado día 30.

## KPIs sostenidos (revisar mensualmente)

| KPI | Target Q1 post-launch |
| --- | --- |
| Pageviews/mes | ≥ 15,000 |
| Unique visitors | ≥ 8,000 |
| Search queries/mes | ≥ 2,500 |
| Search no-result rate | ≤ 12% |
| Tutor downloads (cum) | ≥ 500 |
| `cortex tutor ask` invocations (telemetría opt-in) | ≥ 1,000 |
| Avg time on page | ≥ 1:30 |
| Issues `docs` open | ≤ 10 sostenido |
| PR external/mes | ≥ 1 |

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Docs queda desactualizado rápidamente | CI checks continuos + ownership claro |
| Costos del MCP server suben | Monitor; opt para Cloudflare Worker tiny si crece |
| Volumen de issues docs > capacity | Triage label + auto-close obsoletos |
| Coverage CLI baja con nuevas features | Issue auto-creado por CI cuando detecta gap |
| Comunidad pide formato distinto (PDF, etc.) | Recolectar requests, priorizar V1.1 |

## Cierre del proyecto

Al final de Fase 09:

- ✅ **Docs en producción** con todos los features V1.
- ✅ **Tutor bridge funcional** — pieza distintiva del proyecto.
- ✅ **Plan de mantenimiento** sustentable.
- ✅ **Roadmap V1.1** priorizado.
- ✅ **Documentación interna** del proyecto (este folder de planes).

El proyecto **transiciona a modo mantenimiento continuo**.
