---
title: Fase 01 — Migración de contenido existente
doc_type: phase
phase: 1
status: pending
depends_on: [phase-00]
unlocks: [phase-02]
estimated_duration: 5 días-persona
---

# Fase 01 — Migración de contenido existente

## Objetivo

**Auditar, reescribir y migrar** el contenido existente en `docs/guides/`, `docs/enterprise/`, `docs/autopilot/`, `docs/tutor/` al nuevo schema de frontmatter y estructura del docs site.

Esta fase **no escribe nuevo contenido**; solo migra el existente al nuevo formato. Las fases siguientes agregan páginas nuevas.

## Auditoría inicial

Material disponible en `C:\Cortex\docs\`:

| Carpeta | Archivos | Migración |
| --- | --- | --- |
| `guides/` | 11 archivos | Migrar todos a `/getting-started/`, `/guides/`, `/ide/` |
| `enterprise/` | 7 AVANCE + 7 PLAN + manifesto | Curar para `/enterprise/` overview + key pages |
| `autopilot/` | 12 fases | Curar para `/autopilot/` |
| `tutor/` | PLAN-TUTOR-HINT.md | Usar como background; no migrar literal |
| `vision/` | 4 archivos | NO migrar al docs (es para landing) |
| `roadmap/` | Múltiples | NO migrar (interno) |
| `refact/` | Plans | NO migrar (interno) |
| `security/` | threat-model.md | Migrar a `/enterprise/threat-model` |
| `ops/` | 3 archivos | Migrar a `/guides/` |
| `BusinessSignal/` | Propuesta | NO migrar V1 (no implementado) |

## Mapping de migración

### `docs/guides/` → docs site

| Archivo original | Destino |
| --- | --- |
| `getting-started.md` | `/getting-started/index.mdx` |
| `getting-started-adopters.md` | `/getting-started/for-teams.mdx` |
| `vault-structure.md` | `/concepts/vault-structure.mdx` |
| `pipeline-setup.md` | `/guides/setup-pipeline.mdx` |
| `pipeline-custom-modules.md` | `/guides/customize-pipeline.mdx` |
| `enterprise-vault.md` | `/concepts/enterprise-memory.mdx` |
| `configuration-reference.md` | `/reference/configuration.mdx` |
| `ide-pi.md` | `/ide/pi.mdx` |
| `ide-cursor.md` | `/ide/cursor.mdx` |
| `ide-codex.md` | `/ide/codex.mdx` |
| `ide-opencode.md` | `/ide/opencode.mdx` |
| `ide-claude-code.md` | `/ide/claude-code.mdx` |

### `docs/enterprise/` → docs site

Curar a 8-10 páginas finales:

| Destino | Fuentes |
| --- | --- |
| `/enterprise/overview.mdx` | MANIFIESTO-CORTEX-ENTERPRISE.md (resumido) |
| `/enterprise/org-yaml-reference.mdx` | AVANCE/PLAN sobre org.yaml |
| `/enterprise/presets.mdx` | Documentación de presets |
| `/enterprise/promotion-pipeline.mdx` | Doc sobre flujo de promoción |
| `/enterprise/retention-policies.mdx` | Política de retención por doctype |
| `/enterprise/memory-report.mdx` | Doc del comando memory-report |
| `/enterprise/governance-profiles.mdx` | observability/advisory/enforced |
| `/enterprise/threat-model.mdx` | docs/security/threat-model.md |

### `docs/autopilot/` → docs site

Curar a 6-7 páginas:

| Destino | Fuentes |
| --- | --- |
| `/autopilot/overview.mdx` | Resumen de las 12 fases + manifesto |
| `/autopilot/modes.mdx` | observe/assist/autopilot |
| `/autopilot/policies.mdx` | Budget, Timeout, Enforcement |
| `/autopilot/lifecycle.mdx` | start → preflight → checkpoint → finish |
| `/autopilot/handoff-schema.mdx` | Schema YAML de handoffs |
| `/autopilot/troubleshooting.mdx` | Issues comunes |

### `docs/ops/` → docs site

| Destino | Fuente |
| --- | --- |
| `/guides/ci-cd-integration.mdx` | Cortex-CI-CD-Infrastructure.md |
| `/enterprise/runbook.mdx` | Cortex-Enterprise-Runbook.md |
| `/guides/git-vault-policy.mdx` | Cortex-Git-Vault-Policy.md |

## Tareas detalladas

### 1.1 Setup de migración (0.5 día)

- [ ] Script `apps/docs/scripts/migrate-content.ts` que:
  - Lee archivos originales de `C:\Cortex\docs\`.
  - Aplica transformaciones.
  - Escribe en nuevo path.
- [ ] Lista de archivos a migrar como JSON (`migration-map.json`).
- [ ] Dry-run mode primero.

### 1.2 Migración guides → getting-started + guides + ide (1.5 días)

Para cada archivo de `docs/guides/`:

- [ ] Leer contenido original.
- [ ] **Generar frontmatter** según `02-taxonomia-contenido.md`:
  - `title`: extraer del H1 original.
  - `doc_type`: clasificar (tutorial / how-to / explanation).
  - `summary`: escribir 80-300 chars resumiendo.
  - `audience`: inferir del contenido.
  - `tags`: extraer del cuerpo + agregar manuales.
  - `since_version`: revisar git history.
  - `last_review`: hoy.
  - `status`: `preview` (review needed) o `stable` si está OK.
  - `cli_commands` / `mcp_tools`: extraer del cuerpo.
- [ ] **Reescribir cuerpo**:
  - Estandarizar tono (segunda persona, voseo en ES).
  - Reemplazar bloques de código con `<CodeBlock>` cuando aplique.
  - Reemplazar warnings con `<Callout>`.
  - Reemplazar referencias a otros docs con `<RefCli>`, `<RefMcp>`, etc.
- [ ] Crear versión `en/` (placeholder con frontmatter; traducción en Fase 08).

### 1.3 Migración enterprise (1.5 días)

Es la migración **más compleja** porque las fuentes están dispersas en AVANCE/PLAN files.

- [ ] **Lectura cruzada** de todos los archivos en `docs/enterprise/`.
- [ ] **Sintetizar** información en las 8 páginas destino.
- [ ] **Validar** que cobertura del producto Enterprise es completa.
- [ ] Cada página tiene ejemplos `data-runnable` cuando posible.

### 1.4 Migración autopilot (1 día)

- [ ] Lectura de `docs/autopilot/` (12 fases).
- [ ] Sintetizar en 6 páginas.
- [ ] Verificar que comandos `cortex autopilot ...` están todos documentados.

### 1.5 Migración ops y security (0.5 día)

- [ ] 3 archivos de `ops/` → destinos.
- [ ] `security/threat-model.md` → `/enterprise/threat-model.mdx`.

### 1.6 Cross-referencing (0.5 día)

- [ ] Después de migrar todo, **revisar links internos**.
- [ ] Reemplazar links a archivos antiguos con links al nuevo docs.
- [ ] Validar que `related` en frontmatter apunta a slugs válidos.

### 1.7 QA de migración (0.5 día)

- [ ] Build pasa.
- [ ] Schema valida todos los frontmatters.
- [ ] Linkcheck verde.
- [ ] Lectura manual de top 10 páginas más importantes.
- [ ] Coverage: todos los comandos CLI documentados (al menos placeholder).

## Criterios de aceptación

- ✅ Todos los archivos del mapping migrados.
- ✅ Frontmatter válido en cada archivo.
- ✅ Linkcheck verde.
- ✅ Build pasa.
- ✅ Páginas en español tienen tono consistente (revisión humana).
- ✅ Páginas en inglés tienen placeholders (no traducción aún).
- ✅ Coverage: `pnpm check-cli-coverage` reporta ≥ 90% (placeholders aceptables para resto).

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Migración mecánica pierde contexto | Revisión manual obligatoria de cada archivo |
| Frontmatter requiere data no disponible (since_version) | Default `0.1.0` si no hay info; ajustar en review |
| Links rotos por slugs cambiados | Linkcheck en CI |
| Pierdo contenido importante de los AVANCE files | Mantener copia del original en `docs/canonical-documentation/_archive/` |

## Siguiente fase

→ [Fase 02 — Páginas core](fase-02-paginas-core.md)
