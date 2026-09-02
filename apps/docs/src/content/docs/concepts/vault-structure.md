---
title: Estructura del Vault y Tipos de Documentos
description: Organización canónica del Vault de Cortex, carpetas estándar y esquemas de documentos estructurados.
---

El **Vault** de Cortex (`.cortex/vault/` o `vault/`) es la base de conocimiento estructurada donde se almacena la memoria semántica del proyecto en formato Markdown con frontmatter YAML.

---

## Organización Canónica del Vault

```text
.cortex/vault/
├── adrs/             ← Architectural Decision Records (ADRs)
├── architecture/     ← Documentos globales de arquitectura y diseño de sistemas
├── changelogs/       ← Historial de cambios por versión
├── decisions/        ← Decisiones técnicas puntuales
├── designs/          ← Notas de diseño detalladas y contratos de API
├── glossary/         ← Términos técnicos y glosario del dominio
├── handoffs/         ← Transferencias de contexto entre agentes/sesiones
├── hu/               ← Historias de usuario y requerimientos importados
├── incidents/        ← Reportes de incidentes operativos
├── postmortems/      ← Análisis post-mortem y lecciones aprendidas
├── runbooks/         ← Guías operativas paso a paso
└── sessions/         ← Resúmenes formales de sesiones concluidas
```

---

## Tipos de Documentos Canónicos (`DocTypes`)

El catalogador nativo de Cortex (`DOC_TYPE_VALID_SLUGS`) reconoce **11 tipos de documentos canónicos**:

| DocType | Carpeta de Destino | Campos Requeridos Mínimos |
| :--- | :--- | :--- |
| **`adr`** | `vault/adrs/` | `title`, `context`, `decision` |
| **`decision`** | `vault/decisions/` | `title`, `context`, `decision` |
| **`spec`** | `vault/specs/` | `title`, `summary`, `scope`, `acceptance_criteria` |
| **`design`** | `vault/designs/` | `title`, `session_id`, `spec_path`, `architecture_decision` |
| **`handoff`** | `vault/handoffs/` | `title`, `parent_session_id`, `completed_tasks`, `pending_tasks` |
| **`session`** | `vault/sessions/` | `title`, `spec_summary`, `session_id` |
| **`incident`** | `vault/incidents/` | `title`, `short_description`, `severity` |
| **`postmortem`** | `vault/postmortems/` | `title`, `incident_path`, `incident_number`, `root_cause` |
| **`runbook`** | `vault/runbooks/` | `title`, `runbook_kind`, `procedure` |
| **`architecture`** | `vault/architecture/` | `title`, `summary` |
| **`changelog`** | `vault/changelogs/` | `title`, `version` |
| **`glossary`** | `vault/glossary/` | `title`, `term`, `definition` |
| **`hu`** | `vault/hu/` | `title`, `external_id`, `source` |

---

## Estructura del Frontmatter YAML

Todas las notas en el Vault siguen un esquema estandarizado de metadatos:

```markdown
---
title: "Migración a Rust Nativo del Servidor MCP"
doc_type: "adr"
status: "accepted"
tags: ["mcp", "rust", "performance", "architecture"]
created_at: "2026-05-20"
updated_at: "2026-05-22"
links: ["vault/adrs/001-cortex-core-purity.md"]
---

# ADR 002: Servidor MCP Nativo en Rust

## Contexto
El servidor MCP original dependía de un subproceso Python con tiempos de arranque superiores a 400ms...

## Decisión
Implementar el servidor MCP directamente en Rust usando el crate `rmcp` y `tokio`...

## Consecuencias
* Tiempo de respuesta del health check (`cortex_ping`) reducido a < 5ms.
* Eliminación completa de la dependencia en tiempo de ejecución de Python.
```

---

## Escritura Canónica mediante MCP y CLI

Los agentes de IA no crean archivos directamente con nombres arbitrarios. En su lugar, utilizan la herramienta MCP **`cortex_write_doc`** o el comando de CLI `cortex docs`, los cuales:
1. Validan que todos los campos requeridos para ese `doc_type` estén presentes.
2. Formatean el frontmatter YAML según las normas de gobernanza.
3. Asignan un nombre de archivo normalizado y lo ubican en la carpeta correspondiente.
4. Actualizan de forma inmediata el índice invertido BM25 y la caché vectorial.
