---
title: Fase 03 — Módulos profundos (Autopilot, Enterprise, MCP, WebGraph)
doc_type: phase
phase: 3
status: pending
depends_on: [phase-02]
unlocks: [phase-04]
estimated_duration: 6 días-persona
---

# Fase 03 — Módulos profundos

## Objetivo

Documentar **en profundidad** los módulos avanzados de Cortex:

- **Autopilot** — Modo autónomo opt-in.
- **Enterprise** — Memoria corporativa, governance.
- **MCP** — Protocolo Model Context Protocol, todas las tools.
- **WebGraph** — Visualizador de knowledge graph.

Estas secciones son las que **Persona B (integrador)** y **Persona C (Enterprise)** consumen más.

## Entregables

### Sección `/autopilot/` — 6 páginas

| Slug | Doctype | Contenido |
| --- | --- | --- |
| `autopilot/overview` | explanation | Qué es Autopilot, cuándo usarlo, comparación con manual |
| `autopilot/modes` | reference | observe vs assist vs autopilot, comportamiento, ejemplos |
| `autopilot/policies` | reference | Budget, Timeout, Enforcement, Auto-checkpoint |
| `autopilot/lifecycle` | explanation | start → preflight → checkpoint → finish con diagrama |
| `autopilot/handoff-schema` | reference | YAML schema completo de handoffs entre subagentes |
| `autopilot/troubleshooting` | how-to | Issues comunes, debug, logs |

### Sección `/enterprise/` — 10 páginas

| Slug | Doctype | Contenido |
| --- | --- | --- |
| `enterprise/overview` | explanation | Qué es Enterprise, cuándo, propuesta de valor |
| `enterprise/quickstart` | tutorial | Setup enterprise en 15 min |
| `enterprise/org-yaml-reference` | reference | Schema completo de org.yaml con cada campo |
| `enterprise/presets` | reference | 4 presets: small-company, multi-project-team, regulated-organization, custom |
| `enterprise/promotion-pipeline` | explanation + how-to | Workflow candidate → reviewed → promoted |
| `enterprise/retention-policies` | reference | Política de retención por doctype |
| `enterprise/memory-report` | how-to | Cómo leer `cortex memory-report` |
| `enterprise/governance-profiles` | reference | observability / advisory / enforced |
| `enterprise/multi-tenant-teams` | reference | Teams (Fase 10 de enterprise) |
| `enterprise/compliance-guide` | how-to | Cómo demostrar compliance |
| `enterprise/threat-model` | reference | Security threat model |

### Sección `/mcp/` — 12+ páginas

| Slug | Doctype | Contenido |
| --- | --- | --- |
| `mcp/overview` | explanation | Qué es MCP, por qué Cortex lo usa, arquitectura |
| `mcp/server-setup` | how-to | Configurar `cortex mcp-server` |
| `mcp/integration-guide` | how-to | Conectar un cliente MCP custom |
| `mcp/tools/cortex_search` | reference | Tool detail con schema |
| `mcp/tools/cortex_context` | reference | Idem |
| `mcp/tools/cortex_create_spec` | reference | Idem |
| `mcp/tools/cortex_save_session` | reference | Idem |
| `mcp/tools/cortex_sync_ticket` | reference | Idem |
| `mcp/tools/cortex_validate_handoff` | reference | Idem |
| `mcp/tools/cortex_verify_session_claims` | reference | Idem |
| `mcp/autopilot-tools/cortex_autopilot_start` | reference | Idem |
| `mcp/autopilot-tools/cortex_autopilot_preflight` | reference | Idem |
| `mcp/autopilot-tools/cortex_autopilot_checkpoint` | reference | Idem |
| `mcp/autopilot-tools/cortex_autopilot_finish` | reference | Idem |
| `mcp/autopilot-tools/cortex_autopilot_status` | reference | Idem |

### Sección `/concepts/` adicionales

Reforzar con páginas profundas si aún no están:

- `/concepts/intelligent-routing.mdx` — Fast Track vs Deep Track (autopilot).
- `/concepts/handoff-verification.mdx` — Verification gates, confidence labels.
- `/concepts/promotion-pipeline.mdx` — explanation paralela al how-to.

### `/guides/` adicionales (relacionadas con módulos)

- `/guides/configure-enterprise.mdx` — how-to consolidando setup.
- `/guides/migrate-to-enterprise.mdx` — desde local.
- `/guides/inspect-knowledge-graph.mdx` — usar webgraph.
- `/guides/automate-with-autopilot.mdx` — adopción de autopilot.

### Sección `/webgraph` (subsumida en `/cli/webgraph/`)

WebGraph es small, se cubre en CLI reference + concepts. No requiere sección top-level.

## Tareas detalladas

### 3.1 Autopilot — 6 páginas (1.5 días)

- [ ] Reutilizar contenido de `docs/autopilot/` (12 fases) como insumo.
- [ ] Cada página con `<Steps>` cuando aplique.
- [ ] Lifecycle con diagrama (componente `<DiagramAutopilotLifecycle />`).
- [ ] Handoff schema con YAML completo + Zod validation reference.

### 3.2 Enterprise — 10 páginas (2 días)

- [ ] Reutilizar contenido de `docs/enterprise/`.
- [ ] `org-yaml-reference` es exhaustivo, cada campo con tipo, default, ejemplo.
- [ ] Presets con tabla comparativa.
- [ ] Promotion pipeline con diagrama animado (componente) o estático.
- [ ] Compliance guide con checklist accionable.

### 3.3 MCP — 12+ páginas (1.5 días)

- [ ] Overview con diagrama del protocolo.
- [ ] Page por tool con:
  - Nombre y disponibilidad (since).
  - Input schema (JSON con descripción).
  - Output schema.
  - Ejemplo de invocación (cliente MCP genérico).
  - Errores posibles.
- [ ] Helper componente `<McpToolReference>` consistente.

### 3.4 Concepts adicionales (0.5 día)

- [ ] `intelligent-routing.mdx` con flowchart.
- [ ] `handoff-verification.mdx`.

### 3.5 Guides relacionadas (0.5 día)

- [ ] 4 how-tos consolidando flujos completos.

## Diagramas necesarios

| Diagrama | Tipo | Fase de creación |
| --- | --- | --- |
| Arquitectura Autopilot (5 capas) | SVG / componente | 3.1 |
| Lifecycle Autopilot | Mermaid en MDX o componente | 3.1 |
| Topología Enterprise | SVG / componente | 3.2 |
| Promotion pipeline | Mermaid en MDX | 3.2 |
| MCP protocol overview | SVG / Mermaid | 3.3 |
| Intelligent Routing flowchart | Mermaid | 3.4 |

Decisión: **Mermaid** para diagramas de lógica/flujo (renderizable inline en MDX vía plugin); **SVG/componentes** para diagramas arquitecturales complejos (mejor estética).

## Criterios de aceptación

- ✅ 6 páginas autopilot completas, con diagramas.
- ✅ 10 páginas enterprise completas, con tabla de presets clara.
- ✅ 12+ páginas MCP, cada tool con schema completo.
- ✅ Coverage MCP: `pnpm check-mcp-coverage` reporta 100%.
- ✅ Linkcheck verde.
- ✅ Page tutorial enterprise quickstart ejecutable end-to-end.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| `org.yaml` reference es muy largo y aburrido | Dividir en secciones con tabs por área; cada campo con ejemplo |
| MCP schemas cambian con releases | Generar schemas auto desde el server cuando posible |
| Diagramas Mermaid se ven feos | Tema custom + revisión visual; fallback a SVG si necesario |

## Siguiente fase

→ [Fase 04 — IDE y MCP integration](fase-04-ide-mcp.md)
