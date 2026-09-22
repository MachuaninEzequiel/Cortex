# rust/crates/cortex-cli/src/commands/hu_cmd.rs

## Qué tiene adentro

`hu import|list|show`. `JiraProvider` nativo: solo esquema `file://` (sin HTTP en cortex-cli). Config `integrations.jira` + env email/token. WorkItemService.

## Para qué sirve

Importar work items read-only al vault/hu.

## Relaciones

### Recibe de

- `cortex_app::workitems`, `cortex_config::JiraIntegrationConfig`.
- JSON local file://.

### Envía a

- Notas HU + stdout path.

### Notas de implementación observadas en el código

Sin providers configurados → mensaje canónico igual que Python. HTTP → `"unsupported URL scheme (native CLI only reads file://)"`.
