# rust/crates/cortex-companion/tests/plugin_manifest.rs

## Qué tiene adentro

Archivo de 248 líneas.
B9 — validación estructural del manifest del plugin herdr (G-B5, CI).  `toml` NO está en Cargo.lock (Ruling R3: cero paquetes nuevos), así que el test parsea el manifest línea por línea con un mini-parser acotado al subconjunto TOML que usamos: claves `clave = valor` en el bloque raíz y bloques `[[seccion]]` con sus claves. Los valores se guardan crudos (incluidos arrays inline) para comparar contra el contrato de la spec 14 §4 byte-a-byte. No es un parser TOML completo: si el manifest ganara sintaxis fuera de ese subconjunto, el propio assert de claves lo detecta. Bloques `[[section]]` con sus claves, más las claves del bloque raíz. (nombre de sección, claves) en orden de aparición — preserva los duplicados de `[[actions]]`.
Tests: `manifest_has_required_top_level_fields_verbatim`, `manifest_declares_companion_pane_overlay`, `manifest_declares_four_actions_with_canonical_commands`, `manifest_ids_are_legal_for_herdr`

## Para qué sirve

B9 — validación estructural del manifest del plugin herdr (G-B5, CI).  `toml` NO está en Cargo.lock (Ruling R3: cero paquetes nuevos), así que el test parsea el manifest línea por línea con un mini-parser acotado al subconjunto TOML que usamos: claves `clave = valor` en el bloque raíz y bloques `[[seccion]]` con sus claves. Los valores se guardan crudos (incluidos arrays inline) para comparar contra el contrato de la spec 14 §4 byte-a-byte. No es un parser TOML completo: si el manifest ganara sintaxis fuera de ese subconjunto, el propio assert de claves lo detecta. Bloques `[[section]]` con sus claves, más las claves del bloque raíz. (nombre de sección, claves) en orden de aparición — preserva los duplicados de `[[actions]]`.

## Relaciones

### Recibe de

- Sin imports Cortex en el extracto (manifiesto, lock, html, gitignore o JSON).

### Envía a

- Suite de tests / cargo / bundler según el tipo de archivo.
- El crate o app que lo contiene (ver `00-estructura.md`).

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-companion/tests/plugin_manifest.rs`. 248 líneas.
