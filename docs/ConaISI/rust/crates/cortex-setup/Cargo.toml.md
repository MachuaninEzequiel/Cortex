# rust/crates/cortex-setup/Cargo.toml

## Qué tiene adentro

Manifiesto P8. Comentarios: paridad byte-a-byte, plantillas include_str, dumper YAML PyYAML. Deps chrono, minijinja, serde, serde_json preserve_order, sha2, unicode-normalization.

## Para qué sirve

Compilar writers/setup/IDE sin crates Cortex vecinos.

## Relaciones

### Recibe de

- Workspace package keys.

### Envía a

- cortex-cli, cortex-services, cortex-mcp, cortex-app, cortex-actions, cortex-enterprise, cortex-webgraph-server.

### Notas de implementación observadas en el código

preserve_order: frontmatter sort_keys=False.
