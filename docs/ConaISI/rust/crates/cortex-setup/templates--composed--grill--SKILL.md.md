# rust/crates/cortex-setup/templates/composed/grill/SKILL.md

## Qué tiene adentro

Skill `grill` (fase grill): aclarar requisitos con preguntas de experto una por vez. Frontmatter name/description/when-to-use, `disable-model-invocation: true`. Checkpoint obligatorio al cerrar. Tabla anti-racionalización.

## Para qué sirve

Primera fase COMPOSED.

## Relaciones

### Recibe de

- Pedido humano, CONTEXT.md.

### Envía a

- `cortex_session_checkpoint` phase grill; luego to-spec.

### Notas de implementación observadas en el código

No materializa spec.
