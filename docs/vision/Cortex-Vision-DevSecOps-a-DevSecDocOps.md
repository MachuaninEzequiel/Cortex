---
title: "Cortex — De DevSecOps a DevSecDocOps: Estado Actual vs. Visión"
date: 2026-04-13
tags:
  - cortex
  - vision
  - devsecops
  - devsecdocops
  - roadmap
status: proposal
project: cortex
aliases:
  - DevSecOps a DevSecDocOps
  - Estado Actual vs Vision
---
# 🗺️ De DevSecOps a DevSecDocOps — Estado Actual vs. Visión

## Lo que tenemos hoy

### DevSecOps (proyecto existente)
- **Pipeline CI/CD** con 3 workflows de GitHub Actions (feature, PR, deploy)
- **Seguridad automatizada**: ESLint security plugin (SAST), npm audit (SCA), Dependabot
- **Memory agent** (`cortex-memory.py`) con 5 comandos CLI integrados en el pipeline
- **Vault de memoria** con 4 carpetas: `architecture/`, `runbooks/`, `security-decisions/`, `incidents/`
- **Extensión VS Code** con comandos y sidebar para acceder a la memoria

### Cortex (core)
- **Memoria híbrida**: episódica (ChromaDB) + semántica (vault markdown con embeddings vectoriales)
- **RRF cross-source**: resultados episódicos y semánticos compiten en una única lista ordenada
- **CLI completo**: `init`, `remember`, `search`, `sync-vault`, `stats`, `forget`
- **Agent hooks**: `CortexHook` decorator y `CortexLangChainCallback`
- **25/25 tests pasando**

### Qué memoria se genera actualmente
| Evento | Qué se guarda |
|--------|--------------|
| Lint falla | Resultado del lint en el pipeline |
| Tests fallan | Resultado de los tests |
| Audit falla | Resultado del audit + nota de incidente automática |
| Deploy | Resultado del deploy |

### Qué falta
- Solo captura **resultados binarios** (pass/fail) del pipeline
- No captura **decisiones de diseño**, **cambios en la base de datos**, **nuevos endpoints**, **historias de usuario**
- La memoria es **técnica/operativa**, no **semántica del dominio**
- No hay mecanismo para que **un dev guarde contexto manualmente** desde VS Code (más allá del CLI)
- No hay **relaciones entre memorias** (ej: "este PR está relacionado con aquella decisión de arquitectura")
- No hay **multi-proyecto**: la memoria es de un solo repo

---

## Lo que necesitamos para alcanzar la visión

### 1. Captura automática expandida

| Qué agregar | Cómo |
|-------------|------|
| Historias de usuario | Parsear PR descriptions / commit messages / Jira integration |
| Decisiones de arquitectura | ADR (Architecture Decision Records) auto-generados desde PRs con etiquetas |
| Cambios en DB | Parsear migrations / schema diffs desde el pipeline |
| Nuevos endpoints | Parsear routes/controllers desde el código en CI |
| Incidentes de producción | Webhook desde monitoring (Datadog, Sentry, etc.) → Cortex |
| Code review comments | Capturar conversaciones de PR reviews como memoria episódica |

### 2. Memoria compartida multi-proyecto

| Qué cambiar | Cómo |
|-------------|------|
| Multi-repo | Un vault centralizado (o federado) que agregue memoria de múltiples repos |
| Multi-dev | Cada dev tiene su instancia de Cortex conectada al mismo vault |
| Agentes coordinados | Los agentes de cada dev consultan la misma memoria del proyecto |

### 3. Relaciones entre memorias

| Qué agregar | Cómo |
|-------------|------|
| Links automáticos | Si un PR menciona "fix database connection", linkear con notas previas de DB |
| Grafo de conocimiento | Extraer entidades (endpoints, tablas, servicios) y crear relaciones |
| Referencias cruzadas | Un incident note que referencie el PR que lo fixó y la decisión de arquitectura relacionada |

### 4. Interfaz de consulta para humanos

| Qué agregar | Cómo |
|-------------|------|
| Dashboard web | Ver memorias recientes, buscar por tags, explorar grafo |
| VS Code integrado | Panel lateral que muestre "qué se hizo en este módulo" sin escribir comandos |
| Slack/Teams bot | Preguntarle a Cortex: *"¿qué sabemos sobre el servicio de pagos?"* |

### 5. De DevSecOps a DevSecDocOps

El concepto evoluciona:

```
DevSecOps:  Development + Security + Operations
DevSecDocOps: Development + Security + Documentation + Operations
```

La documentación deja de ser una fase del proceso y se convierte en un **subproducto automático** del pipeline.

---

## Resumen: delta entre lo que hay y lo que queremos

| Dimensión | Hoy | Visión |
|-----------|-----|--------|
| Qué se captura | Pass/fail del pipeline | TODO: decisiones, HU, DB changes, endpoints, reviews, incidentes |
| Quién accede | Pipeline + CLI | TODO: devs (VS Code), agentes (hooks), humanos (dashboard), SREs (Slack) |
| Alcance | Un repo | TODO: multi-repo, multi-equipo |
| Relaciones | Ninguna | TODO: grafo de conocimiento, links automáticos |
| Documentación | Manual (si se hace) | TODO: automática como subproducto del pipeline |
| Agentes | Con contexto limitado | TODO: con contexto completo del proyecto |

---

## Enlaces relacionados

- [[Cortex-IA-Documentacion-Integrada]]
- [[Cortex-Memoria-Hibrida]]
- [[Cortex-DevSecOps-Integracion]]
