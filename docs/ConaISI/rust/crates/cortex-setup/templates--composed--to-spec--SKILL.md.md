# rust/crates/cortex-setup/templates/composed/to-spec/SKILL.md

## Qué tiene adentro

Skill `to-spec` (fase spec): convertir requisitos en spec con AC verificables, scope, verification hooks. `disable-model-invocation: true`.

## Para qué sirve

Materializar contrato antes de tickets/código.

## Relaciones

### Recibe de

- Grill / conversación / CONTEXT.md.

### Envía a

- `cortex_create_spec` / write spec + checkpoint phase spec.

### Notas de implementación observadas en el código

La spec no describe la solución: define problema y bordes.
