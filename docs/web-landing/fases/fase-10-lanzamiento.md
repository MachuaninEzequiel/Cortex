---
title: Fase 10 — Lanzamiento y post-launch
doc_type: phase
phase: 10
status: pending
depends_on: [phase-09]
unlocks: []
estimated_duration: 3 días-persona + monitoring continuo
---

# Fase 10 — Lanzamiento y post-launch

## Objetivo

**Lanzar** la landing al mundo, **medir** la respuesta, **iterar** rápido sobre feedback inicial. Esta fase no termina el día del lanzamiento; abarca los **primeros 30 días** post-launch con plan explícito de monitoreo y mejoras.

## Entregables

1. **QA cross-browser y cross-device** completo.
2. **Plan de comunicación** ejecutado.
3. **Lanzamiento técnico** sin downtime.
4. **Analytics y error tracking** verificados en producción.
5. **Plan de mantenimiento** mensual definido.
6. **Post-mortem** 30 días después.

## Tareas detalladas

### 10.1 QA cross-browser (1 día)

#### Browsers a testear

| Browser | Versiones |
| --- | --- |
| Chrome | Últimas 2 versiones |
| Edge | Últimas 2 versiones |
| Firefox | Últimas 2 versiones |
| Safari | Últimas 2 versiones macOS + iOS |
| Samsung Internet | Mobile Android |
| Brave / Arc / Opera | Smoke test |

#### Devices a testear

| Tipo | Devices específicos |
| --- | --- |
| Phone (small) | iPhone SE (375×667), Pixel 4a |
| Phone (large) | iPhone 14 Pro Max, Samsung S23 Ultra |
| Tablet | iPad 10.2", iPad Pro 12.9" |
| Laptop | MacBook 13", Surface Laptop |
| Desktop | 1920×1080, 2560×1440, 3840×2160 |

#### Checklist por device

- [ ] Layout no roto.
- [ ] Animaciones suaves.
- [ ] Forms funcionan.
- [ ] Demos cargan.
- [ ] Copy legible.
- [ ] Touch targets ok en mobile.
- [ ] Modal/drawer funcionan en mobile.

### 10.2 Plan de comunicación (0.5 día)

#### Canales

| Canal | Asset | Timing |
| --- | --- | --- |
| **HackerNews** | "Show HN: Cortex — Memoria corporativa para agentes IA" | Día 1, 6am EST |
| **Reddit** (r/LocalLLaMA, r/MachineLearning, r/programming) | Posts adaptados por subreddit | Día 1, escalonado |
| **X/Twitter** | Thread de 8-10 tweets con visuales del WebGraph, CLI player | Día 1, mañana |
| **LinkedIn** | Post largo con foco en gobernanza enterprise | Día 1, mañana |
| **Dev.to** | Artículo técnico explicando arquitectura | Día 2-3 |
| **Newsletter propio** | Si existe, comunicación con early adopters | Día 0 (pre-launch) |
| **Newsletters externos** | Outreach a TLDR, Console, etc. | Pre-launch 2 semanas |
| **Discord/Slack** | Anuncio en comunidades Python, MCP, AI agents | Día 1 |

#### Assets para comunicación

- [ ] **Video corto** (60-90s) tipo "demo reel" mostrando hero + WebGraph + CLI + outcome.
- [ ] **GIFs animados** para Twitter (WebGraph drag, CLI player).
- [ ] **Screenshots** hi-res para blog posts.
- [ ] **Press kit**: logo en varias variantes, screenshots, copy descriptivo.

### 10.3 Lanzamiento técnico (0.5 día)

#### Día -1 (pre-launch)

- [ ] DNS pre-warming.
- [ ] Cloudflare Pages production deploy.
- [ ] Smoke test desde 5 ubicaciones geográficas (puedes usar latency-test.com o similar).
- [ ] Monitoring activos: alertas Cloudflare, Plausible accesible.
- [ ] Backup del repo + S3 mirror de assets.

#### Día 0 (launch)

- [ ] **Confirmar** todas las URLs:
  - https://cortex.dev → 200
  - https://cortex.dev/en → 200
  - https://cortex.dev/enterprise → 200
  - https://cortex.dev/changelog → 200
  - https://cortex.dev/legal → 200
- [ ] Ejecutar comunicación coordinada.
- [ ] Equipo en standby para responder comentarios.
- [ ] Monitoring activo de errors (Sentry o Cloudflare logs).

#### Rollback plan

- [ ] Si performance se degrada o errores spike:
  - Rollback a deploy anterior con Cloudflare Pages 1-click.
  - Comunicar incident en X/Status page.
  - Fix forward o backout según gravedad.

### 10.4 Post-launch monitoring (continuo)

#### Día 1-7

- [ ] Daily check de Plausible: pageviews, top sources, conversion.
- [ ] Daily check de Search Console: indexación, errores.
- [ ] Responder comentarios HN/Reddit/Twitter en < 4 horas.
- [ ] Reportar bugs encontrados en GitHub issues.
- [ ] Hotfixes para crashes y errores críticos.

#### Semana 2-4

- [ ] Weekly review de métricas vs objetivos (ver `00-vision-y-objetivos.md` §5).
- [ ] A/B test #1 (sugerencia): hero copy "amnesia" vs "memoria corporativa".
- [ ] A/B test #2: posición de los CTAs.
- [ ] Iteración semanal con cambios menores.

### 10.5 Post-mortem (día 30) (0.5 día)

Documento `docs/web-landing/post-mortem-launch.md`:

- [ ] **Métricas vs objetivos**: tabla con planeado vs real.
- [ ] **Qué funcionó**: secciones con mejor engagement, CTAs más clickeados.
- [ ] **Qué no funcionó**: secciones abandonadas, bounces tempranos.
- [ ] **Bugs encontrados**: lista categorizada.
- [ ] **Lecciones aprendidas**: para la próxima iteración.
- [ ] **Plan de V1.1**: cambios prioritarios para el próximo sprint.

### 10.6 Plan de mantenimiento (0.5 día)

#### Cadencia mensual

| Tarea | Frecuencia | Responsable |
| --- | --- | --- |
| Actualizar versión de Cortex en footer | Cada release | Dev |
| Regenerar snapshot WebGraph | Mensual | CI automático |
| Actualizar CHANGELOG render | Cada release | CI automático |
| Audit Lighthouse | Mensual | CI automático |
| Audit accesibilidad | Trimestral | Dev |
| Audit seguridad (pnpm audit) | Semanal | CI |
| Revisión métricas + iteración | Mensual | Marketing/Dev |

#### Cadencia por evento

| Evento | Acción |
| --- | --- |
| Release de Cortex mayor | Actualizar landing copy, OG, screenshots |
| Cambio de logo | Regenerar assets |
| Nuevo IDE soportado | Agregar tab en selector |
| Bug crítico | Hotfix < 24h |

## Criterios de aceptación

- ✅ Launch ejecutado sin downtime.
- ✅ Pageviews día 1 ≥ 5,000 (estimado conservador HN frontpage).
- ✅ Conversion to docs día 1 ≥ 35% según `00-vision-y-objetivos.md`.
- ✅ Cero bugs críticos durante semana 1.
- ✅ Plan de mantenimiento documentado y socializado.
- ✅ Post-mortem publicado en día 30.

## KPIs de éxito (revisar día 30)

| KPI | Target | Real (a llenar día 30) |
| --- | --- | --- |
| Total pageviews | ≥ 20,000 | — |
| Unique visitors | ≥ 12,000 | — |
| Conversion to docs | ≥ 35% | — |
| Conversion to install copy | ≥ 12% | — |
| GitHub stars (delta) | +30% | — |
| Enterprise leads | ≥ 5 | — |
| Avg time on page | ≥ 2:30 | — |
| Avg scroll depth | ≥ 65% desktop | — |
| Lighthouse Performance | ≥ 90 sostenido | — |

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| HN slashdot effect tira el site | Cloudflare CDN absorbe; verificar cuotas Pages |
| Bug crítico post-launch | Rollback 1-click + comunicar |
| Críticas en HN/Reddit | Responder con humildad, no defensivamente |
| Métricas debajo de target | Iteración rápida (A/B tests, copy changes) |
| Equipo agotado post-launch | Plan de descanso de 1 semana post-launch |

## Siguiente paso post-fase

Después de los 30 días, el proyecto entra en **modo mantenimiento + V1.1**.

V1.1 sugerido (después de evaluar post-mortem):

- Blog inicial con 3 artículos (technical deep dives).
- Casos de estudio reales (cuando haya).
- Demo interactiva online (Cortex corriendo en servidor compartido, sandbox).
- Comparativa expandida con productos específicos (LangChain Memory, MemGPT, etc.).
- Página `/community` con showcases y testimonios.
