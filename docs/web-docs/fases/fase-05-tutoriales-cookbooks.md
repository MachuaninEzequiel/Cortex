---
title: Fase 05 — Tutoriales end-to-end y Cookbooks
doc_type: phase
phase: 5
status: pending
depends_on: [phase-04]
unlocks: [phase-06]
estimated_duration: 5 días-persona
---

# Fase 05 — Tutoriales end-to-end y Cookbooks

## Objetivo

Cubrir la sección **`/tutorials/`** con **flujos completos** de adopción, y crear **"recetas"** (Cookbook) que resuelvan tareas específicas comunes.

Las páginas de tutorials van más allá del Quickstart: son experiencias de aprendizaje guiado de **30-90 minutos** con outcomes verificables.

## Entregables

### Sección `/tutorials/` — 6-8 tutoriales

| Slug | Duración | Outcome |
| --- | --- | --- |
| `tutorials/first-feature-with-cortex` | 30 min | Implementar feature pequeña con flujo tripartito completo |
| `tutorials/enterprise-rollout` | 90 min | Configurar Enterprise desde cero para 3 proyectos |
| `tutorials/ci-integration` | 45 min | Integrar Cortex en CI/CD (GitHub Actions) |
| `tutorials/custom-pipeline-stage` | 60 min | Agregar un stage custom al pipeline |
| `tutorials/migrate-from-vanilla` | 45 min | Migrar proyecto existente sin Cortex a Cortex |
| `tutorials/autopilot-adoption` | 60 min | Adoptar Autopilot gradualmente (observe → assist → autopilot) |
| `tutorials/multi-project-team` | 90 min | Setup multi-tenant teams con scopes y promotion |
| `tutorials/build-your-own-skill` | 45 min | Crear y compartir un Cortex skill |

### Sección `/guides/` (cookbook) — recetas adicionales

Complementa los tutoriales con **how-tos cortos** (5-15 min cada uno):

| Slug | Receta |
| --- | --- |
| `guides/recover-from-vault-corruption` | Recuperar de un vault corrupto |
| `guides/bulk-import-existing-docs` | Importar documentación existente al vault |
| `guides/export-vault-to-obsidian` | Usar vault en Obsidian externamente |
| `guides/jira-sync-workflow` | Sync de issues con Jira |
| `guides/share-knowledge-between-projects` | Compartir conocimiento via Enterprise vault |
| `guides/audit-knowledge-promotion` | Auditar el pipeline de promoción |
| `guides/customize-frontmatter-schema` | Customizar schema de docs |
| `guides/limit-token-usage` | Limitar consumo de tokens en agentes |
| `guides/debug-mcp-issues` | Debug problemas comunes de MCP |
| `guides/configure-embedder-openai` | Usar OpenAI embeddings en lugar de ONNX |
| `guides/scheduled-promotion-review` | Setup de revisión periódica de candidates |
| `guides/disaster-recovery` | Plan de recuperación de vault |

## Estructura de tutorial

```mdx
---
title: "Tu primera feature con Cortex"
doc_type: tutorial
summary: |
  Implementá una feature pequeña usando el ciclo tripartito completo de
  Cortex: crear spec, codear, guardar session, verificar.
section: tutorials
audience: [developer]
tags: [tutorial, first-feature, tripartite, getting-started]
since_version: 0.1.0
last_review: 2026-05-14
status: stable
prerequisites:
  - getting-started/installation
  - getting-started/first-session
time_estimate_minutes: 30
outcome: |
  Al finalizar, tendrás una feature implementada con spec persistente,
  session note auditable, y podrás recuperar todo el contexto con
  `cortex search`.
related:
  - concepts/tripartite-cycle
  - cli/governance/create-spec
  - cli/governance/save-session
---

## Lo que vas a lograr

Una feature simple (agregar un endpoint `/health` a un proyecto FastAPI) con:

- ✅ Spec técnica creada y persistida.
- ✅ Implementación en código.
- ✅ Session note guardada con confidence labels.
- ✅ Búsqueda funcional sobre lo que hiciste.

## Prerrequisitos

- Cortex instalado ([install](../getting-started/installation)).
- Workspace inicializado en un proyecto Python.
- IDE conectado a Cortex via MCP (opcional pero recomendado).

## Paso 1 — Crear la spec

<Steps>

1. Posicionate en tu proyecto:
   ```bash data-runnable
   cd ~/proyecto-test
   ```

2. Creá la spec:
   ```bash data-runnable
   cortex create-spec \
     --title "Health endpoint" \
     --goal "Agregar endpoint /health que retorne status del servicio"
   ```

3. Verificá:
   ```bash data-runnable
   ls -la .cortex/vault/specs/
   ```
   Debería aparecer `SPEC-<id>.md`.

</Steps>

## Paso 2 — Implementar la feature

(... continúa con resto del tutorial ...)

## Paso 3 — Guardar la session

(...)

## Paso 4 — Verificar

```bash data-runnable
cortex search "health endpoint"
```

Esperás ver:

- Tu spec recién creada (score alto).
- Tu session note (score alto).

## ¿Qué aprendiste?

- El ciclo tripartito: spec → implementation → session.
- Cómo persistir decisiones en el vault.
- Cómo recuperar contexto con `cortex search`.

## Próximos pasos

- [Tutorial: Adoptar Autopilot](./autopilot-adoption)
- [Concepts: Hybrid memory](../concepts/hybrid-memory)
```

## Tareas detalladas

### 5.1 Tutoriales — escritura (3 días)

Cada tutorial cumple:

- [ ] Outcome claro al principio.
- [ ] Prerrequisitos explícitos.
- [ ] `<Steps>` para guiar.
- [ ] `data-runnable` cuando aplique.
- [ ] Verificación al final.
- [ ] "Qué aprendiste" + "Próximos pasos".
- [ ] Time estimate realista.

#### Selección de 6-8 tutoriales para V1

Priorizar (de la lista de 8 propuestos):

1. ✅ `first-feature-with-cortex` (Persona A, crítico para onboarding).
2. ✅ `enterprise-rollout` (Persona C, alto valor B2B).
3. ✅ `ci-integration` (Persona B, alto interés técnico).
4. ✅ `autopilot-adoption` (alto interés conversion).
5. ✅ `migrate-from-vanilla` (común para adopters).
6. ✅ `multi-project-team` (Persona C, advanced).

Posponer a V1.1:

- `custom-pipeline-stage`.
- `build-your-own-skill`.

### 5.2 Cookbook how-tos — escritura (1.5 días)

Cada how-to cumple:

- [ ] Problema claro al inicio ("Cómo X").
- [ ] Pasos cortos.
- [ ] Resultado verificable.
- [ ] Sin teoría (link a concepts si necesario).

#### Selección de 8-12 how-tos para V1

Priorizar los más buscados/preguntados:

1. ✅ `recover-from-vault-corruption`.
2. ✅ `bulk-import-existing-docs`.
3. ✅ `jira-sync-workflow`.
4. ✅ `share-knowledge-between-projects`.
5. ✅ `audit-knowledge-promotion`.
6. ✅ `debug-mcp-issues`.
7. ✅ `configure-embedder-openai`.
8. ✅ `disaster-recovery`.

### 5.3 Validación con usuarios reales (0.5 día)

- [ ] **Beta test interno**: 2-3 personas siguen los tutoriales en máquinas limpias.
- [ ] Registrar:
  - Tiempo real vs estimado.
  - Pasos donde se quedaron stuck.
  - Errores no documentados.
- [ ] Iteración rápida sobre feedback.

## Criterios de aceptación

- ✅ 6 tutoriales escritos y testeados.
- ✅ 8+ how-tos cookbook.
- ✅ Tiempo real ≤ 110% del estimado (margen 10%).
- ✅ ≥ 80% completitud por tester sin ayuda externa.
- ✅ Linkcheck verde.
- ✅ Coverage: todos los flujos críticos cubiertos.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Tutorial tarda más de lo estimado en CI | Test E2E con cronómetro; ajustar tiempo en frontmatter |
| Steps quedan obsoletos al cambiar Cortex | Test runnable de cada tutorial en CI |
| Cookbook crece sin control | Lista priorizada; new how-to requiere "estamos resolviendo esto X veces" como justificación |

## Siguiente fase

→ [Fase 06 — Búsqueda](fase-06-busqueda.md)
