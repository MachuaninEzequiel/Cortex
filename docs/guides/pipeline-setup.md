# Pipeline CI/CD — Guía de Setup

## Visión general

El pipeline DevSecDocOps de Cortex ejecuta **4 stages** secuenciales en cada Pull Request:

```
Security → Lint → Test → Documentation
```

Cada stage actúa como una **puerta de calidad**: puede bloquear el merge (modo enforced) o solo advertir (modo advisory).

---

## Configuración en `.cortex/config.yaml` (new-layout)

Todas las opciones de pipeline se configuran en el `config.yaml` de tu proyecto:

```yaml
pipeline:
  # Si true, aborta al primer stage que falle (no ejecuta los siguientes)
  abort_early: true

  stages:
    security:
      enabled: true
      block_on_failure: true         # true = enforced, false = advisory
      audit_level: high              # low | moderate | high | critical
    lint:
      enabled: true
      block_on_failure: true
    test:
      enabled: true
      block_on_failure: true
      min_coverage: 0                # 0 = sin enforcement. Ej: 85 para 85%
    documentation:
      enabled: true
      block_on_failure: false        # Generalmente advisory
```

> **Nota:** En **legacy layout**, el archivo se llama `config.yaml` y vive en la raíz del repo. El schema es idéntico.

### Campos por stage

| Campo | Tipo | Default | Descripción |
| --- | --- | --- | --- |
| `enabled` | bool | `true` | Si el stage se ejecuta |
| `block_on_failure` | bool | `true` | `true` = bloquea merge. `false` = solo advierte |
| `audit_level` | string | `high` | (security only) Umbral de severidad que bloquea |
| `min_coverage` | int | `0` | (test only) Cobertura mínima exigida (0 = sin enforcement) |

---

## Modos de enforcement

### Modo Advisory (`block_on_failure: false`)

El stage se ejecuta y reporta resultados, pero **no bloquea** el merge aunque falle. Útil para:
- Equipos en transición que están adoptando nuevas reglas
- Stages experimentales
- Documentation checks que no deberían frenar delivery

### Modo Enforced (`block_on_failure: true`)

El stage **bloquea el merge** si falla. Es el default para Security, Lint y Test. Garantiza que el código cumple los estándares antes de llegar a la rama principal.

---

## Setup rápido

```bash
# Generar archivos de pipeline (GitHub Actions workflows)
cortex setup pipeline

# Setup completo (agent + pipeline)
cortex setup full
```

Esto crea los workflows en `.github/workflows/` con los stages configurados en tu `config.yaml`.

---

## Siguiente lectura

- **Intercambiar módulos**: [pipeline-custom-modules.md](pipeline-custom-modules.md)
- **Estructura del Vault**: [vault-structure.md](vault-structure.md)
- **Configuración completa**: [configuration-reference.md](configuration-reference.md)
