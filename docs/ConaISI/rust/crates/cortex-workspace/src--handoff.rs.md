# rust/crates/cortex-workspace/src/handoff.rs

## Qué tiene adentro

Enums literales: `AgentName` (cortex-sync, cortex-SDDwork, cortex-code-explorer, cortex-code-implementer, cortex-documenter, cortex-security-auditor, cortex-test-verifier), `HandoffStatus` (complete/partial/blocked), `ArtifactAction` (created/modified/deleted/renamed). Structs `ArtifactProduced` y `AgentHandoff`. Métodos `to_yaml` (emisor `pyyaml`) y `from_yaml` (serde_yaml + validación).

## Para qué sirve

Contrato YAML **legacy** de handoff entre subagentes. El código lo marca deprecado a favor de `SessionRecord`, pero vigente para IDEs sin checkpoints. MCP `cortex_validate_handoff` lo consume.

## Relaciones

### Recibe de

- Texto YAML (tool MCP / agentes).
- `crate::pyyaml::{to_pyyaml_string, Node}` para serializar.

### Envía a

- YAML byte-parity hacia quien persista o valide el handoff.
- `cortex-mcp` `handlers_sessions::validate_handoff_text`.

### Notas de implementación observadas en el código

Campos desconocidos se ignoran (default pydantic). Raíz no-mapping ⇒ `"Handoff YAML must be a mapping at the root"`. Orden de claves en `to_yaml` es el de `model_dump`.
