# Referencia de Configuración

## Archivos de configuración

Cortex usa dos archivos de configuración principales:

| Archivo | Alcance | Propósito |
| --- | --- | --- |
| `.cortex/config.yaml` | Proyecto (new-layout) | Configuración local del proyecto |
| `config.yaml` | Proyecto (legacy) | Configuración local del proyecto (legacy layout) |
| `.cortex/org.yaml` | Organización | Topología enterprise (opcional) |

> **Layout:** En **new-layout** (default), `config.yaml` vive dentro de `.cortex/`. En **legacy**, `config.yaml` vive en la raíz del repo. El comportamiento funcional es idéntico; solo cambia la ubicación del archivo.

---

## `config.yaml` — Configuración del proyecto

Este archivo se crea con `cortex setup agent` y controla el comportamiento de Cortex en tu proyecto.

### Referencia completa

```yaml
# ── Episodic Memory (vector DB) ──────────────────────────────
episodic:
  persist_dir: .memory/chroma       # where ChromaDB stores data
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2 # local, no API key needed
  embedding_backend: onnx           # onnx | local | openai

# ── Semantic Memory (markdown vault) ─────────────────────────
semantic:
  vault_path: vault                  # path to your .md notes folder

# ── Hybrid Retrieval ─────────────────────────────────────────
retrieval:
  top_k: 5                           # results per source
  episodic_weight: 1.0               # RRF weight for episodic results
  semantic_weight: 1.0               # RRF weight for semantic results

# ── LLM (for memory summarization) ───────────────────────────
llm:
  provider: none                     # none | openai | anthropic | ollama
  model: ""                          # e.g. "gpt-4o-mini" or model name

# ── Context Enricher (proactive context injection) ───────────
context_enricher:
  min_score: 0.1                     # Minimum score to consider relevant
  domain_confidence: 0.5             # Min confidence for domain detection
  max_items: 8                       # Max context items to show
  max_chars: 2000                    # Max characters of injected context
  multi_match_boost: 1.5             # Boost per extra strategy match
  co_occurrence_boost: 0.3           # Max boost from file co-occurrence
  strategies:
    topic: true                      # Search by domain/topic
    files: true                      # Search by file names
    keywords: true                   # Search by extracted keywords
    pr_title: true                   # Search by PR title
    graph_expansion: true            # Co-occurrence boost

# ── Pipeline (DevSecDocOps CI/CD gates) ──────────────────────
pipeline:
  abort_early: true                  # Abort on first blocking gate failure
  stages:
    security:
      enabled: true
      block_on_failure: true         # Fails on HIGH/CRITICAL vulnerabilities
      audit_level: high              # low | moderate | high | critical
    lint:
      enabled: true
      block_on_failure: true         # Lint errors block the merge
    test:
      enabled: true
      block_on_failure: true
      min_coverage: 0                # 0 = no coverage enforcement
    documentation:
      enabled: true
      block_on_failure: false        # Missing docs warns but does not block
```

### Valores por defecto

Si omitís un campo, Cortex usa los defaults definidos en el schema Pydantic de `CortexConfig`:
- `embedding_backend`: `"onnx"` (no requiere API key ni PyTorch)
- `episodic.persist_dir`: `".memory/chroma"` (new-layout: `.cortex/.memory/chroma`; legacy: `.memory/chroma`)
- `semantic.vault_path`: `"vault"`
- `retrieval.top_k`: `5`
- `pipeline.abort_early`: `true`
- Todos los stages: `enabled: true`, `block_on_failure: true` (excepto documentation que defaultea a `false`)

---

## `.cortex/org.yaml` — Configuración Enterprise

Este archivo se crea con `cortex setup enterprise` y define la topología organizacional.

### Referencia completa

```yaml
schema_version: 1

# ── Organización ──────────────────────────────────────
organization:
  name: "Mi Empresa"
  slug: "mi-empresa"
  profile: "small-company"           # small-company | multi-project-team |
                                    # regulated-organization | custom

# ── Memoria ───────────────────────────────────────────
memory:
  mode: "layered"
  enterprise_vault_path: "vault-enterprise"
  enterprise_memory_path: "memory/enterprise/chroma"
  enterprise_semantic_enabled: true
  enterprise_episodic_enabled: false
  project_memory_mode: "isolated"    # isolated | shared
  branch_isolation_enabled: false
  retrieval_default_scope: "local"   # local | enterprise | all
  retrieval_local_weight: 1.0
  retrieval_enterprise_weight: 1.0

# ── Promoción ─────────────────────────────────────────
promotion:
  enabled: true
  allowed_doc_types:
    - spec
    - decision
    - runbook
    - hu
    - incident
  require_review: true
  default_targets: ["enterprise_vault"]

# ── Gobernanza ────────────────────────────────────────
governance:
  git_policy: "balanced"             # balanced | strict | custom
  ci_profile: "advisory"             # observability | advisory | enforced
  version_sessions_in_git: false

# ── Integración ───────────────────────────────────────
integration:
  github_actions_enabled: true
  webgraph_workspace_enabled: true
  ide_profiles: []
```

### Perfiles de organización

| Perfil | Uso |
| --- | --- |
| `small-company` | 2-10 personas, sin review obligatorio por default |
| `multi-project-team` | 3-10 repos, retrieval cruzado, peso enterprise ligeramente mayor |
| `regulated-organization` | Review obligatorio, CI enforced, branch isolation |
| `custom` | Configuración manual completa |

### Perfiles de CI

| Perfil | Comportamiento |
| --- | --- |
| `observability` | Ejecuta los checks, reporta resultados, no bloquea nada |
| `advisory` | Reporta y advierte con warnings, pero no bloquea merges |
| `enforced` | Bloquea merges si algún gate falla |

---

## Presets disponibles

```bash
# Equipo chico, configuración simple
cortex setup enterprise --preset small-company

# Múltiples proyectos con retrieval cruzado
cortex setup enterprise --preset multi-project-team

# Organización regulada con review obligatorio
cortex setup enterprise --preset regulated-organization

# Vista previa sin ejecutar
cortex setup enterprise --preset small-company --dry-run

# No interactivo (para CI/scripts)
cortex setup enterprise --preset small-company --non-interactive
```

---

## Siguiente lectura

- **Primeros pasos**: [getting-started.md](getting-started.md)
- **Pipeline setup**: [pipeline-setup.md](pipeline-setup.md)
- **Enterprise vault**: [enterprise-vault.md](enterprise-vault.md)
