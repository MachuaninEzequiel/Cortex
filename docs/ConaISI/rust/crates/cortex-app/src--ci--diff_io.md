# src/ci/diff_io.rs

## Qué tiene adentro

`DiffResolutionError`. `read_diff_from_args` con prioridad:
1. `--diff <file>` crudo
2. `--base-commit` (+ head opcional): `git diff base..head|HEAD`
3. Auto: `git diff <trunk>..HEAD` con trunk = main|master (el que exista)

## Para qué sirve

Obtener el texto del diff para `ValidationInput`.

## Relaciones

### Recibe de

- Args CLI / git.

### Envía a

- `validate_pull_request`.

### Notas de implementación observadas en el código

Tres modos, no más.
