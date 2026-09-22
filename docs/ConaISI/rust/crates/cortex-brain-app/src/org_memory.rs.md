# rust/crates/cortex-brain-app/src/org_memory.rs

## Qué tiene adentro

Memoria organizacional para la GUI:

- `OrgKnowledgeItem`, `OrgMemoryPayload`
- Vault local: `vault/` o `.cortex/vault` o `WorkspaceLayout::vault_path()`
- `get_project_org_memory`: escanea markdown (doc_type por carpeta decisions/adrs/specs/guides/rfc); fusiona `.cortex/enterprise/records.jsonl`
- Frontmatter `title`/`status`; fallback H1
- `approve_org_knowledge` / `reject_org_knowledge` (copia/promulgación + registro)

## Para qué sirve

Cola de revisión y promulgación desde `OrgMemoryModal`.

## Relaciones

### Recibe de

- `cortex_workspace::WorkspaceLayout`
- vault local + `records.jsonl`
- `cortex-enterprise` vía layout (ruta enterprise vault)

### Envía a

- commands `get_org_memory`, `approve_org_candidate`, `reject_org_candidate`

### Notas de implementación observadas en el código

`updated_at` del scan se setea a `chrono::Utc::now()` al enumerar (no es mtime del archivo).
