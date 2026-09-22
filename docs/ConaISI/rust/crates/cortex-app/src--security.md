# src/security.rs

## Qué tiene adentro

Puerto de `cortex/security/paths.py`.

`PathSecurityError(String)` con Display = el string interno.

`resolve_lenient`: espejo de `Path.resolve(strict=False)` — canonicaliza el ancestro existente y re-adjunta la cola; relativos se anclan al cwd.

`resolve_safe(root, rel)`: rechaza `rel` absoluto (`"Absolute paths are not allowed: {rel}"`); resuelve `root/rel` y exige `starts_with(root)` (`"Path escapes allowed root ({root}): {rel}"`).

`validate_under_root(path, root)`: valida un path ya construido.

Tests: resolución bajo root, absoluta, `../` escape, `a/../b.md` permitido, absoluto dentro vs relativo al cwd.

## Para qué sirve

Único helper de path traversal. `SemanticIndex::index_file` lo usa para `rel` bajo el vault.

## Relaciones

### Recibe de

- Root y path relativo/absoluto de callers operacionales.

### Envía a

- `PathBuf` resuelto o error con mensaje contrato Python.

### Notas de implementación observadas en el código

`a/../b.md` se permite si el resultado queda dentro del root (igual que Python).
