---
title: "Cortex — Plan DevSecDocOps: Documentación automática en cada PR"
date: 2026-04-13
tags:
  - cortex
  - plan
  - devsecdocops
  - implementacion
status: in-progress
project: cortex
aliases:
  - Plan DevSecDocOps
  - PR Documentation Pipeline
---
# 📋 Plan DevSecDocOps — Documentación automática en cada PR

## Principio de diseño

> **Todo se ejecuta coordinado en el momento del PR.** El PR es el punto donde confluyen: el código que se cambia, las pruebas que lo validan, la seguridad que lo revisa, y ahora **la documentación que se genera automáticamente**.

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Pull Request a main                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              ci-pull-request.yml (GitHub Actions)            │
│                                                              │
│  1. checkout                                                 │
│  2. setup Node + Python                                      │
│  3. npm ci                                                   │
│  4. [CORT] PR Capture → extrae metadata del PR               │
│  5. eslint (SAST) → [CORT] store lint result                 │
│  6. npm audit (SCA) → [CORT] store audit result              │
│  7. tests           → [CORT] store test result               │
│  8. [CORT] search past context → ¿falló antes? ¿hay fix?    │
│  9. [CORT] generate docs → ADR + HU note + changelog entry  │
│ 10. [CORT] sync vault → re-indexa todo                       │
│ 11. [CORT] upload context artifact                           │
│ 12. Slack notify                                              │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Vault del proyecto (versionado con git)         │
│                                                              │
│  vault/                                                      │
│  ├── architecture/     ← ADRs auto-generados                 │
│  ├── runbooks/         ← Cómo fixear problemas comunes       │
│  ├── decisions/        ← Decisiones de seguridad/diseño      │
│  ├── incidents/        ← Notas de fallos auto-generadas      │
│  ├── hu/               ← Historias de usuario documentadas   │
│  ├── changelog/        ← Entries del changelog por PR        │
│  └── sessions/         ← Resumen de qué hizo cada PR         │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Agentes de IA de los devs (VS Code)             │
│                                                              │
│  - Dev A trabaja en HU de DB → genera memoria                │
│  - Dev B pregunta a su agente: "¿cómo está la DB?"           │
│  - Agente busca en Cortex → encuentra lo que hizo Dev A      │
│  - Dev B integra sin leer el código, solo con contexto       │
└─────────────────────────────────────────────────────────────┘
```

## Componentes a desarrollar

### 1. `cortex/pr_capture.py` — PR Capture Module
**Responsabilidad**: Extraer toda la información relevante del PR actual y estructurarla como datos consumibles por Cortex.

**Qué captura**:
| Dato | Fuente | Formato |
|------|--------|---------|
| PR title | `github.event.pull_request.title` | string |
| PR body/description | `github.event.pull_request.body` | string |
| Author | `github.event.pull_request.user.login` | string |
| Branch source | `github.event.pull_request.head.ref` | string |
| Branch target | `github.event.pull_request.base.ref` | string |
| Commit SHA | `github.event.pull_request.head.sha` | string |
| Files changed | `git diff --name-only main...HEAD` | list[str] |
| Diff summary | `git diff --stat main...HEAD` | string |
| DB migrations | scan de `migrations/` o `*.sql` en diff | list[str] |
| API changes | scan de `routes/`, `controllers/` en diff | list[str] |
| Labels | `github.event.pull_request.labels` | list[str] |

**Output**: Un objeto `PRContext` (Pydantic model) que se serializa a JSON y se pasa a los demás módulos.

### 2. `cortex/doc_generator.py` — Document Generator Module
**Responsabilidad**: A partir del `PRContext` + resultados del pipeline (lint, audit, tests), generar documentación automática.

**Qué genera**:
| Documento | Carpeta vault | Trigger | Contenido |
|-----------|--------------|---------|-----------|
| Session note | `sessions/` | Siempre | Qué hizo este PR, resultados, author, commit |
| HU note | `hu/` | Si el PR body menciona una HU | Qué se implementó, endpoints, DB changes |
| ADR | `architecture/` | Si el label incluye `adr` o `decision` | Decisión de arquitectura con opciones evaluadas |
| Incident note | `incidents/` | Si lint o audit falla | Qué falló, contexto, link al runbook |
| Changelog entry | `changelog/` | Si el PR se mergea | Entry estilo changelog (feat, fix, chore) |
| Security note | `decisions/` | Si npm audit encuentra algo | Vulnerabilidad encontrada, severidad, fix |

**Cómo genera**:
1. **Templates predefinidos** (markdown con placeholders)
2. **Relleno automático** desde `PRContext` + resultados del pipeline
3. **create_note()** en el vault de Cortex
4. **sync_vault()** para re-indexar

### 3. CLI: `cortex pr-context` — PR Context Command
**Responsabilidad**: Comando CLI que orquesta la captura y generación en GitHub Actions.

**Subcomandos**:
```
cortex pr-context capture          → Captura metadata del PR, output JSON
cortex pr-context store            → Guarda en memoria episódica
cortex pr-context generate         → Genera documentos en el vault
cortex pr-context search           → Busca contexto histórico del PR
cortex pr-context full             → Ejecuta capture + store + generate + sync (todo en uno)
```

**Uso en GitHub Actions**:
```yaml
- name: Cortex — PR Context
  run: cortex pr-context full \
    --title "${{ github.event.pull_request.title }}" \
    --body "${{ github.event.pull_request.body }}" \
    --author "${{ github.event.pull_request.user.login }}" \
    --branch "${{ github.event.pull_request.head.ref }}" \
    --commit "${{ github.event.pull_request.head.sha }}"
  env:
    CORTEX_VAULT_PATH: vault/
```

### 4. `cortex/models.py` — Extended Pydantic Models
**Nuevos modelos**:
```python
class PRContext(BaseModel):
    title: str
    body: str
    author: str
    source_branch: str
    target_branch: str
    commit_sha: str
    files_changed: list[str]
    diff_summary: str
    db_migrations: list[str] = []
    api_changes: list[str] = []
    labels: list[str] = []
    lint_result: str | None = None
    audit_result: str | None = None
    test_result: str | None = None

class GeneratedDoc(BaseModel):
    doc_type: Literal["session", "hu", "adr", "incident", "changelog", "security"]
    title: str
    content: str
    vault_path: str  # subfolder relativo
    filename: str
```

### 5. Vault structure templates
Se crean las carpetas con un archivo `.gitkeep` en cada una:
```
vault/
├── architecture/.gitkeep
├── runbooks/.gitkeep
├── decisions/.gitkeep
├── incidents/.gitkeep
├── hu/.gitkeep
├── changelog/.gitkeep
└── sessions/.gitkeep
```

### 6. Markdown templates para generación automática
Cada tipo de documento tiene su template en `cortex/templates/`:

**`session.md`**:
```markdown
---
title: "{{title}}"
date: {{date}}
pr: #{{pr_number}}
author: {{author}}
branch: {{source_branch}}
commit: {{commit_sha}}
tags: [session, {{labels}}]
---
# {{title}}

## Resumen
{{body_summary}}

## Cambios
{{diff_summary}}

## Pipeline
- Lint: {{lint_result}}
- Audit: {{audit_result}}
- Tests: {{test_result}}

## Archivos modificados
{{files_list}}
```

**`hu.md`**:
```markdown
---
title: "HU: {{hu_title}}"
hu_id: {{hu_id}}
pr: #{{pr_number}}
date: {{date}}
tags: [hu, {{status}}]
---
# HU: {{hu_title}}

## Descripción
{{hu_description}}

## Implementación
{{implementation_details}}

## Endpoints afectados
{{endpoints}}

## Cambios en DB
{{db_changes}}

## Tests
{{test_summary}}
```

**`adr.md`**:
```markdown
---
title: "ADR-{{number}}: {{title}}"
date: {{date}}
pr: #{{pr_number}}
status: {{status}}
tags: [adr, architecture]
---
# ADR-{{number}}: {{title}}

## Contexto
{{context}}

## Decisión
{{decision}}

## Opciones evaluadas
{{options}}

## Consecuencias
{{consequences}}
```

### 7. Orquestador: `scripts/devsecdocops.sh`
Script bash que se ejecuta en GitHub Actions y coordina todo:

```bash
#!/usr/bin/env bash
set -euo pipefail

# DevSecDocOps Orchestrator
# Se ejecuta en el workflow de PR y coordina:
# 1. Captura del PR → 2. Pipeline checks → 3. Doc generation → 4. Vault sync

VAULT_PATH="${CORTEX_VAULT_PATH:-vault}"

echo "🧠 DevSecDocOps Orchestrator starting..."

# Step 1: Capture PR context
echo "📸 Capturing PR context..."
cortex pr-context capture \
  --title "$PR_TITLE" \
  --body "$PR_BODY" \
  --author "$PR_AUTHOR" \
  --branch "$PR_BRANCH" \
  --commit "$PR_COMMIT" \
  --output .pr-context.json

# Step 2: Run pipeline checks (called from workflow directly)
# ... eslint, audit, tests ...

# Step 3: Store results in memory
echo "📝 Storing pipeline results..."
cortex pr-context store \
  --context .pr-context.json \
  --lint-result "$LINT_STATUS" \
  --audit-result "$AUDIT_STATUS" \
  --test-result "$TEST_STATUS"

# Step 4: Search past context
echo "🔍 Searching past context..."
cortex pr-context search \
  --context .pr-context.json \
  --output .past-context.json

# Step 5: Generate documentation
echo "📄 Generating documentation..."
cortex pr-context generate \
  --context .pr-context.json \
  --past-context .past-context.json \
  --vault "$VAULT_PATH"

# Step 6: Sync vault
echo "🔄 Syncing vault..."
cortex sync-vault

echo "✅ DevSecDocOps Orchestrator complete"
```

## Flujo completo del PR

```
PR abierto
    │
    ▼
┌─ checkout ───────────────────────────────────────────────┐
│                                                           │
│  1. Setup (Node + Python + deps)                         │
│                                                           │
│  2. CORTEX: pr-context capture                           │
│     → Extrae title, body, author, branch, diff            │
│     → Detecta DB migrations, API changes, labels          │
│     → Output: .pr-context.json                            │
│                                                           │
│  3. ESLint (SAST)                                        │
│     → [CORT] store lint result en memoria episódica      │
│                                                           │
│  4. npm audit (SCA)                                      │
│     → [CORT] store audit result                           │
│     → Si falla → search past failures → suggest fix      │
│                                                           │
│  5. Tests (integration + unit)                            │
│     → [CORT] store test result                            │
│                                                           │
│  6. CORTEX: pr-context search                            │
│     → Busca: "¿este PR se parece a alguno de antes?"      │
│     → Si hay incidents previos → los incluye en contexto  │
│                                                           │
│  7. CORTEX: pr-context generate                          │
│     → Genera session note (siempre)                       │
│     → Genera HU note (si hay HU en el body)               │
│     → Genera ADR (si hay label de decisión)               │
│     → Genera incident note (si algo falló)                │
│     → Genera changelog entry                              │
│                                                           │
│  8. CORTEX: sync-vault                                   │
│     → Re-indexa todo el vault con las nuevas notas        │
│                                                           │
│  9. Upload context artifact (para debugging)              │
│                                                           │
│ 10. Slack notify con resumen                             │
│                                                           │
└───────────────────────────────────────────────────────────┘
    │
    ▼
Vault actualizado con documentación nueva (commiteable)
    │
    ▼
Agentes de IA de los devs pueden consultar la memoria
```

## Orden de implementación

| # | Componente | Depende de | Prioridad |
|---|-----------|-----------|-----------|
| 1 | `PRContext` model en `models.py` | — | 🔴 Alta |
| 2 | `GeneratedDoc` model en `models.py` | — | 🔴 Alta |
| 3 | `pr_capture.py` module | PRContext model | 🔴 Alta |
| 4 | Markdown templates | GeneratedDoc model | 🟡 Media |
| 5 | `doc_generator.py` module | Templates, PRContext | 🟡 Media |
| 6 | CLI `pr-context` command | pr_capture, doc_generator | 🟡 Media |
| 7 | Vault structure (carpetas) | — | 🟢 Baja |
| 8 | `devsecdocops.sh` orchestrator | Todo lo anterior | 🟢 Baja |
| 9 | Actualizar `ci-pull-request.yml` | Orchestrator | 🟢 Baja |
| 10 | Tests de los nuevos módulos | Todo lo anterior | 🟢 Baja |
| 11 | Documentación Obsidian | Todo completado | 🟢 Baja |

## Criterios de aceptación

- [ ] `cortex pr-context full` ejecuta captura + store + generate + sync sin errores
- [ ] Cada PR genera al menos una session note en `vault/sessions/`
- [ ] Si el PR body contiene referencia a HU, se genera nota en `vault/hu/`
- [ ] Si algo del pipeline falla, se genera incident note en `vault/incidents/`
- [ ] El vault se re-indexa automáticamente después de generar docs
- [ ] Los nuevos módulos tienen tests con cobertura ≥ 80%
- [ ] El workflow de PR se ejecuta completo sin bloquear el merge
- [ ] Documentación de Obsidian actualizada con la sesión

---

## Enlaces relacionados

- [[Cortex-IA-Documentacion-Integrada]]
- [[Cortex-Vision-DevSecOps-a-DevSecDocOps]]
- [[Cortex-Memoria-Hibrida]]
- [[Cortex-DevSecOps-Integracion]]
