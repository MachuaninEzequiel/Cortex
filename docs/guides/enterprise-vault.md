# Enterprise Vault — Memoria Corporativa

## ¿Qué problema resuelve?

En equipos y organizaciones, el conocimiento tiende a quedar atrapado en proyectos individuales. Enterprise Memory permite que el conocimiento se **promueva** del nivel de proyecto al nivel corporativo, creando una memoria institucional compartida.

---

## La analogía con Git: local y remote

Si conocés Git, ya entendés Enterprise Memory. El concepto es el mismo:

> **`vault/` es tu repo local y `vault-enterprise/` es tu remote origin.**
> Trabajás en local, promovés (push) lo valioso, y buscás (pull) lo que otros compartieron.

| Concepto Git | Concepto Cortex Enterprise | Paralelo |
| --- | --- | --- |
| Repo local (`.git/`) | `vault/` (proyecto) | Donde trabajás y persistís cambios |
| Repo remoto (origin) | `vault-enterprise/` (organización) | La fuente de verdad compartida |
| `git commit` | `cortex save-session` / `create-spec` | Persistir trabajo localmente |
| `git push` | `cortex promote-knowledge` | Subir conocimiento al nivel compartido |
| `git pull` / `git fetch` | `cortex search --scope all` | Traer conocimiento del nivel corporativo |
| Pull Request (review) | `cortex review-knowledge` | Revisión humana antes de integrar |
| Feature branch | Vault de un proyecto individual | Espacio aislado de trabajo |
| `main` / `master` | `vault-enterprise/` | La fuente canónica de verdad |
| `.gitignore` | `.memory/` (en .gitignore) | Lo que NO se comparte |
| `git clone` + rebuild | `cortex sync-vault` | Reconstruir estado local desde la fuente |

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
  topology: custom
  
vault:
  enterprise_path: "../vault-enterprise"
  promotion_policy:
    auto_promote: false
    require_review: true
    min_reviewers: 2
    
enforcement:
  profile: enforced         # observability | advisory | enforced
  ci_gates:
    security: true
    lint: true
    test: true
    documentation: true
```

---

## ¿Qué va a Git/Master?

| Recurso | ¿Va a Git? | Rama recomendada |
| --- | --- | --- |
| `vault/` (local) | ✅ Sí | La rama del proyecto |
| `vault-enterprise/` | ✅ Sí | Repo separado o rama `main` del org repo |
| `.cortex/org.yaml` | ✅ Sí | La rama del proyecto |
| `.memory/` | ❌ No | En `.gitignore` |

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
