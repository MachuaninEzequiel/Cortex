# rust/crates/cortex-mcp/src/lib.rs

## Qué tiene adentro

Declara módulos públicos: backends, handlers_*, pyjson, server, tools_catalog.

## Para qué sirve

Fachada del crate MCP.

## Relaciones

### Recibe de

- Módulos internos.

### Envía a

- `cortex-cli::commands::mcp_cmd` y tests/examples.

### Notas de implementación observadas en el código

El comentario de paridad: gate P9 = catálogo byte-a-byte + dispatch de ping; no bytes exactos del transporte rmcp (tema P12).
