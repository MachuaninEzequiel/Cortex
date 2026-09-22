# rust/crates/cortex-workspace/src/git_policy.rs

## Qué tiene adentro

Constantes de patrones: `RECOMMENDED_GITIGNORE_PATTERNS`, `NEW_LAYOUT_GITIGNORE_PATTERNS`, `LEGACY_GITIGNORE_PATTERNS`. Función `recommended_gitignore_snippet(layout)` y `gitignore_contains(root, pattern)`.

## Para qué sirve

Decidir qué líneas deberían ir en `.gitignore` según layout, y chequear si un patrón ya está presente (líneas vacías y comentarios ignorados).

## Relaciones

### Recibe de

- `Option<&WorkspaceLayout>` (si new → snippet nuevo; sin layout o legacy → snippet legacy conservador).
- Archivo `root/.gitignore`.

### Envía a

- `cortex-setup::setup_templates::recommended_gitignore_snippet` (hay un renderer paralelo en setup).
- CLI setup / consumers que escriben gitignore.

### Notas de implementación observadas en el código

Sin layout se usa el snippet **legacy** (superset conservador), igual que Python.
