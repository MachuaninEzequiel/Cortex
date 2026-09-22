# rust/crates/cortex-setup/src/slug.rs

## Qué tiene adentro

`slugify`: NFKD, ascii ignore, strip/lower, quitar no `\w\s-`, `[\s_]+` → `-`, colapsar `-`.

## Para qué sirve

Nombres de archivo de notas.

## Relaciones

### Recibe de

- Títulos / terms.

### Envía a

- writers, routing FilenameCtx, migration.

### Notas de implementación observadas en el código

`\w` sobre string ya ascii = [a-zA-Z0-9_]. Distinto de `cortex_workspace::slugify` (que acepta `.` y no NFKD).
