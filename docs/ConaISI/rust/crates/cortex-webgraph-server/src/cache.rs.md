# rust/crates/cortex-webgraph-server/src/cache.rs

## Qué tiene adentro

Porteo de `cortex/webgraph/cache.py` — caché persistente de snapshots.  El fingerprint replica byte-a-byte el hashlib de Python: json.dumps(config_payload, sort_keys=True) [separadores DEFAULT de Python] + hash_tree(vault) + hash_tree(episodic) + count + token. hash_tree recorre archivos ordenados por PARTES de ruta (comparación Path de Python, no por string completo) con mtime_ns y size.
Archivo de 183 líneas.
Símbolos públicos observados:
- `pub struct WebGraphCache`

## Para qué sirve

Porteo de `cortex/webgraph/cache.py` — caché persistente de snapshots.  El fingerprint replica byte-a-byte el hashlib de Python: json.dumps(config_payload, sort_keys=True) [separadores DEFAULT de Python] + hash_tree(vault) + hash_tree(episodic) + count + token. hash_tree recorre archivos ordenados por PARTES de ruta (comparación Path de Python, no por string completo) con mtime_ns y size.

## Relaciones

### Recibe de

- `use cortex_workspace::WorkspaceLayout`
- Contexto de crate `cortex-webgraph-server`: cortex-core, cortex-app, cortex-workspace, cortex-setup

### Envía a

- Crate `cortex-webgraph-server` envía hacia: HTTP axum, cortex-cli webgraph, brain webgraph.serve

### Notas de implementación observadas en el código

Ruta fuente: `rust/crates/cortex-webgraph-server/src/cache.rs`.
El crate/archivo declara `forbid(unsafe_code)`.
