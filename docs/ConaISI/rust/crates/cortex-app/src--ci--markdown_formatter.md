# src/ci/markdown_formatter.rs

## Qué tiene adentro

`DEFAULT_MARKER = "<!-- cortex-pr-summary -->"`. `render_pr_comment(result, marker) -> String`.

Salida delimitada por el marcador para `gh pr comment --edit-last` (de-dupe en re-runs). Marcador exacto y estable.

## Para qué sirve

Comentario de PR (CI Level 2).

## Relaciones

### Recibe de

- `ValidationResult`.

### Envía a

- stdout/workflow GitHub.

### Notas de implementación observadas en el código

El marcador es contrato entre releases.
