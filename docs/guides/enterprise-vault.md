# Enterprise Vault — Memoria Corporativa

## ¿Qué problema resuelve?

En equipos y organizaciones, el conocimiento tiende a quedar atrapado en proyectos individuales. Enterprise Memory permite que el conocimiento se **promueva** del nivel de proyecto al nivel corporativo, creando una memoria institucional compartida.

---

## La analogía con Git: local y remote

Si conocés Git, ya entendés Enterprise Memory. El concepto es el mismo:

> **`vault/` es tu repo local y `vault-enterprise/` es tu remote origin.**
> Trabajás en local, promovés (push) lo valioso, y buscás (pull) lo que otros compartieron.

| Concepto Git | Concepto Cortex Enterprise (new-layout) | Concepto Cortex Enterprise (legacy) | Paralelo |
| --- | --- | --- | --- |
| Repo local (`.git/`) | `.cortex/vault/` | `vault/` | Donde trabajás y persistís cambios |
| Repo remoto (origin) | `.cortex/vault-enterprise/` | `vault-enterprise/` | La fuente de verdad compartida |
| `git commit` | `cortex save-session` / `create-spec` | — | Persistir trabajo localmente |
| `git push` | `cortex promote-knowledge` | — | Subir conocimiento al nivel compartido |
| `git pull` / `git fetch` | `cortex search --scope all` | — | Traer conocimiento del nivel corporativo |
| Pull Request (review) | `cortex review-knowledge` | — | Revisión humana antes de integrar |
| Feature branch | Vault de un proyecto individual | — | Espacio aislado de trabajo |
| `main` / `master` | `.cortex/vault-enterprise/` | `vault-enterprise/` | La fuente canónica de verdad |
| `.gitignore` | `.cortex/memory/` | `.memory/` | Lo que NO se comparte |
| `git clone` + rebuild | `cortex sync-vault` | — | Reconstruir estado local desde la fuente |

### Donde la analogía es exacta

- **Promoción = Push + PR**: `local → candidate → review → promote` es equivalente a `commit → push → PR review → merge to main`.
- **Retrieval = Fetch**: `--scope local` es tu branch, `--scope enterprise` es origin/main, `--scope all` es todo junto.
- **`regulated-organization`** con `require_review: true` es como un repo con **branch protection rules**: nadie mergea sin approval.

### Donde Cortex va más allá

En Git, vos decidís qué pusheás. En Cortex, la **promotion policy puede automatizar la selección** de candidatos basándose en la calidad del documento, su relevancia cross-project y las reglas de la organización. Es como si Git tuviera un bot que te dice "este commit es tan valioso que debería estar en el repo de la empresa".

## Modelo de 2 niveles

```
                ┌────────────────────────────┐
                │  vault-enterprise/          │
                │  Conocimiento CORPORATIVO   │
                │  Compartido entre proyectos │
                └────────────┬───────────────┘
                             │ promotion
                ┌────────────┴───────────────┐
                │  vault/                     │
                │  Conocimiento LOCAL         │
                │  Específico del proyecto    │
                └────────────────────────────┘
```

### `vault/` — Nivel local

Todo lo que se genera en un proyecto específico:
- Specs, sessions, decisions, runbooks
- Específico de ese codebase
- Versionado en el repo del proyecto

### `vault-enterprise/` — Nivel corporativo

Conocimiento promovido que aplica a toda la organización:
- Patrones arquitectónicos compartidos
- Decisiones que afectan a múltiples proyectos
- Runbooks corporativos
- Best practices estandarizadas

---

## Flujo de promoción

```
 vault/doc.md  →  candidate  →  review  →  promote  →  vault-enterprise/
     (local)       (propuesto)   (aprobado)  (publicado)   (corporativo)
```

### Paso 1: Identificar candidatos

```bash
cortex promote-knowledge --dry-run
# Muestra qué docs son candidatos a promoción sin ejecutar nada
```

### Paso 2: Promover

```bash
cortex promote-knowledge --apply
# Mueve los docs aprobados al vault enterprise
```

### Paso 3: Revisar (en organizaciones reguladas)

```bash
cortex review-knowledge
# Flujo de aprobación para candidatos pendientes
```

---

## Topologías organizacionales

La topología se define en `.cortex/org.yaml` y determina cómo se estructura la memoria corporativa:

### `small-company`

- Vault enterprise compartido directamente.
- Sin flujo de review obligatorio.
- Ideal para equipos de 2-10 personas.

```bash
cortex setup enterprise --preset small-company
```

### `multi-project-team`

- Múltiples proyectos comparten un vault enterprise.
- Retrieval cruzado: buscar en tu proyecto + el vault corporativo.
- Ideal para organizaciones con 3-10 repositorios.

```bash
cortex setup enterprise --preset multi-project-team
```

### `regulated-organization`

- Review obligatorio antes de promoción.
- CI enforced para validar documentación.
- Audit trail completo.
- Ideal para empresas reguladas (fintech, healthcare, etc.).

```bash
cortex setup enterprise --preset regulated-organization
```

### `custom`

Configuración manual completa via `org.yaml`:

```yaml
# .cortex/org.yaml
schema_version: 1
organization:
  name: "Mi Empresa"
  slug: "mi-empresa"
  profile: custom

memory:
  mode: layered
  enterprise_vault_path: vault-enterprise
  enterprise_memory_path: memory/enterprise/chroma
  enterprise_semantic_enabled: true
  enterprise_episodic_enabled: false
  project_memory_mode: isolated
  branch_isolation_enabled: false
  retrieval_default_scope: all
  retrieval_local_weight: 1.0
  retrieval_enterprise_weight: 1.2

promotion:
  enabled: true
  allowed_doc_types:
    - spec
    - decision
    - runbook
    - hu
    - incident
  require_review: true
  default_targets:
    - enterprise_vault

governance:
  git_policy: strict
  ci_profile: enforced
  version_sessions_in_git: true

integration:
  github_actions_enabled: true
  webgraph_workspace_enabled: true
  ide_profiles: []
```

---

## ¿Qué va a Git/Master?

| Recurso | New-layout | Legacy | ¿Va a Git? | Rama recomendada |
| --- | --- | --- | --- | --- |
| Vault local | `.cortex/vault/` | `vault/` | ✅ Sí | La rama del proyecto |
| Vault enterprise | `.cortex/vault-enterprise/` | `vault-enterprise/` | ✅ Sí | Repo separado o rama `main` del org repo |
| Org config | `.cortex/org.yaml` | `.cortex/org.yaml` | ✅ Sí | La rama del proyecto |
| Memoria episódica | `.cortex/memory/` | `.memory/` | ❌ No | En `.gitignore` |

### Estrategia para el vault enterprise

**Opción A: Repo separado** (recomendado para multi-project-team y regulated)
- Un repo `empresa/vault-enterprise` que contiene solo documentación corporativa.
- Cada proyecto lo referencia via la ruta en `org.yaml`.

**Opción B: Subcarpeta en un repo mono** (recomendado para small-company)
- `vault-enterprise/` vive en el mismo repo que el código.
- Más simple, menos overhead de gestión.

---

## Retrieval multi-nivel

Con enterprise configurado, las búsquedas pueden abarcar ambos niveles:

```bash
# Solo búsqueda local
cortex search "autenticación JWT"

# Búsqueda en todo (local + enterprise)
cortex search "autenticación JWT" --scope all

# Solo enterprise
cortex search "autenticación JWT" --scope enterprise
```

---

## Reporte de salud

```bash
cortex memory-report                      # Reporte básico
cortex memory-report --scope enterprise   # Reporte enterprise
cortex memory-report --json               # Formato JSON para CI
cortex doctor --scope enterprise          # Diagnóstico de salud enterprise
```

---

## Siguiente lectura

- **Estructura del vault local**: [vault-structure.md](vault-structure.md)
- **Pipeline setup**: [pipeline-setup.md](pipeline-setup.md)
- **Configuración completa**: [configuration-reference.md](configuration-reference.md)
