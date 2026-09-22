# cortex/git_policy.py

## Qué tiene adentro

Constantes de patrones `.gitignore`:
- `RECOMMENDED_GITIGNORE_PATTERNS`: `.memory/`, `*.chroma/`, `vault/sessions/`.
- `NEW_LAYOUT_GITIGNORE_PATTERNS`: `.cortex/memory/`, `.cortex/vault/sessions/`, `.cortex/session.lock`.
- `LEGACY_GITIGNORE_PATTERNS`: `.memory/`, `vault/sessions/`, `.cortex/session.lock`.

Funciones: `recommended_gitignore_snippet(layout=..., project_root=...)` arma el bloque comentado según layout; `gitignore_contains` (resto del archivo) para doctor.

## Para qué sirve

Decir qué estado local **no** debe versionarse (memoria, sesiones, lock).

## Relaciones

### Recibe de

- `WorkspaceLayout` (opcional) para elegir snippet.

### Envía a

- `doctor.py` (checks de gitignore).
- Setup/writers que insertan snippet (vía otros módulos).

---
Fuente: lectura de `cortex/git_policy.py`. No se usó documentación previa.
