---
title: cortex ci & cortex pr-context
description: Integración de Cortex en pipelines de Integración Continua (CI/CD) y generación de contexto para Pull Requests.
---

Los comandos `cortex ci` y `cortex pr-context` automatizan la validación de calidad de sesiones y la generación de contexto técnico enriquecido para Pull Requests.

---

## `cortex ci`

Valida que los cambios introducidos en una rama o PR cumplan con los contratos de sesión, specs y trazabilidad requeridos por el proyecto.

```bash
cortex ci <COMMAND>
```

### Subcomandos:

#### 1. `cortex ci validate-pr`
Valida un Pull Request contra la sesión de trabajo activa:

```bash
cortex ci validate-pr [OPCIONES]
```

**Opciones:**
* `--base-commit <HASH>`: Commit base del PR.
* `--head-commit <HASH>`: Commit del head del PR.
* `--pr-number <N>`: Número de Pull Request en GitHub/GitLab.
* `--pr-author <USER>`: Autor del Pull Request.
* `--session <SESSION_ID>`: ID de la sesión asociada al trabajo.
* `--format <json|text|pr-comment>`: Formato del informe de salida (por ejemplo, `pr-comment` genera Markdown listo para ser posteado como comentario en GitHub).

```bash
cortex ci validate-pr --base-commit origin/main --head-commit HEAD --format pr-comment
```

#### 2. `cortex ci verify`
Ejecuta el verificador de reclamos de sesión ([`VerificationRunner`](file:///home/chucho/Cortex/rust/crates/cortex-app/src/session/verification.rs)), comprobando que todos los tests declarados como *"pasando"* en los checkpoints efectivamente superen la suite de pruebas local.

---

## `cortex pr-context`

Genera un resumen técnico exhaustivo para la descripción del PR, extrayendo las decisiones de diseño, notas de sesión y archivos modificados.

```bash
cortex pr-context <COMMAND>
```

### Subcomandos:
* **`capture`**: Captura los metadatos del PR (título, autor, rama, commits, etiquetas).
* **`store`**: Persiste el contexto del PR en la memoria episódica.
* **`search`**: Busca PRs previos relacionados por similitud temática.
* **`generate`**: Genera la plantilla de descripción del PR basada en las notas de la sesión.
* **`full`**: Ejecuta el pipeline completo de captura, enriquecimiento y generación en un solo paso.

### Ejemplo de Generación Completa:
```bash
cortex pr-context full --title "Migración de Auth a Rust" --target-branch main
```

Salida generada:
```markdown
## Resumen del PR
Migración del módulo de autenticación a Rust nativo.

## Decisiones Técnicas Relacionadas
* Ver ADR: `vault/adrs/004-auth-argon2id.md`
* Sesión asociada: `sess_20260902_182000_auth`

## Tareas Completadas
- [x] Implementación de hashing Argon2id
- [x] Test unitarios de expiración de tokens
- [x] Verificación de compatibilidad con Cortex Doctor
```
