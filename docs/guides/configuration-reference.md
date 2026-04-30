# Referencia de Configuración

## Archivos de configuración

Cortex usa dos archivos de configuración principales:

| Archivo | Alcance | Propósito |
| --- | --- | --- |
| `config.yaml` | Proyecto | Configuración local del proyecto |
| `.cortex/org.yaml` | Organización | Topología enterprise (opcional) |

---

## `config.yaml` — Configuración del proyecto

Este archivo se crea con `cortex setup agent` y controla el comportamiento de Cortex en tu proyecto.

### Referencia completa

```yaml
# ── Proyecto ──────────────────────────────────────────
project_name: "mi-proyecto"          # Nombre del proyecto
project_root: "."                    # Raíz del proyecto (relativa a config.yaml)

# ── Memoria ───────────────────────────────────────────
vault_path: "vault"                  # Carpeta del vault
memory_path: ".memory"               # Carpeta de ChromaDB
embedding_backend: "onnx"            # onnx (default, sin API key) | local (PyTorch)

# ── Pipeline DevSecDocOps ─────────────────────────────
pipeline:
  abort_early: true                  # Abortar al primer stage fallido
  stages:
    security:
      enabled: true                  # Habilitar stage
      block_on_failure: true         # Enforced (true) o Advisory (false)
      tool: "npm audit"              # Herramienta a ejecutar
    lint:
      enabled: true
      block_on_failure: true
      tool: "ruff check ."
    test:
      enabled: true
      block_on_failure: true
      tool: "pytest"
    documentation:
      enabled: true
      block_on_failure: false        # Generalmente advisory
      tool: "cortex verify-docs"

# ── Integraciones ─────────────────────────────────────
integrations:
  jira:
    enabled: false                   # Habilitar integración Jira (read-only)
    base_url: ""                     # https://TU-DOMINIO.atlassian.net
    email_env: "JIRA_EMAIL"          # Nombre de la env var con el email
    token_env: "JIRA_API_TOKEN"      # Nombre de la env var con el token

# ── LLM (opcional) ────────────────────────────────────
llm:
  provider: "none"                   # none | openai | anthropic | ollama
  model: ""                          # Modelo a usar (ej: gpt-4, claude-3-opus)
  api_key_env: ""                    # Nombre de la env var con la API key
```

### Valores por defecto

Si omitís un campo, Cortex usa estos defaults:
- `embedding_backend`: `"onnx"` (no requiere API key ni PyTorch)
- `vault_path`: `"vault"`
- `memory_path`: `".memory"`
- `pipeline.abort_early`: `true`
- Todos los stages: `enabled: true`, `block_on_failure: true`

---

## `.cortex/org.yaml` — Configuración Enterprise

Este archivo se crea con `cortex setup enterprise` y define la topología organizacional.

### Referencia completa

```yaml
schema_version: 1

# ── Organización ──────────────────────────────────────
organization:
  name: "Mi Empresa"                 # Nombre de la organización
  topology: "small-company"          # small-company | multi-project-team |
                                     # regulated-organization | custom

# ── Vault Enterprise ──────────────────────────────────
vault:
  enterprise_path: "../vault-enterprise"  # Ruta al vault corporativo
  promotion_policy:
    auto_promote: false              # Promover automáticamente (sin review)
    require_review: false            # Requerir aprobación humana
    min_reviewers: 1                 # Mínimo de reviewers (si require_review)

# ── Enforcement ───────────────────────────────────────
enforcement:
  profile: "advisory"               # observability | advisory | enforced
  ci_gates:
    security: true                   # Gate de seguridad en CI
    lint: true                       # Gate de lint en CI
    test: true                       # Gate de tests en CI
    documentation: true              # Gate de documentación en CI

# ── Proyectos (multi-project-team) ────────────────────
projects:
  - name: "frontend"
    path: "../frontend"
  - name: "backend"
    path: "../backend"
  - name: "mobile"
    path: "../mobile"
```

### Perfiles de enforcement

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
