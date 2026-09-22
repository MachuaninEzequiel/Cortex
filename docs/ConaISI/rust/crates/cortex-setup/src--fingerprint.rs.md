# rust/crates/cortex-setup/src/fingerprint.rs

## Qué tiene adentro

`compute_fingerprint(content) -> hex SHA-256 64 chars lowercase`. Test vector `""` → e3b0c442...

## Para qué sirve

Campo `fingerprint:` del frontmatter canónico.

## Relaciones

### Recibe de

- Cuerpo markdown.

### Envía a

- writers + migration.

### Notas de implementación observadas en el código

Idéntico a `cortex.documentation.common.compute_fingerprint`.
