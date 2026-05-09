---
name: cortex-autopilot-finish
description: Skill de cierre de sesion para Cortex Autopilot.
---

# Cortex Autopilot Finish

## Cuando usar

- Al finalizar una tarea con cambios observados.
- Cuando el usuario indica explicitamente que la tarea esta completa.
- Antes de cambiar de contexto a un nuevo pedido.

## Proceso de cierre

1. **Verifica el estado**: ejecuta tests/build/lint si aplica.
2. **Registra checkpoint final**: `cortex_autopilot_checkpoint` con resumen de cambios.
3. **Ejecuta finish**: `cortex_autopilot_finish` con `auto=true` para persistir draft.
4. **Confirma al usuario**: indica si se guardo session note o quedo como draft.

## Si falla la tool

- Informa al usuario que el cierre automatico fallo.
- Ofrece guardar nota manualmente o reintentar.
- No inventes que se guardo si la tool reporto error.
