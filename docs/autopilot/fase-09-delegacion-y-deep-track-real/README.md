# Fase 9 - Delegacion y Deep Track Real

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 9 - Delegacion y Deep Track Real`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- Alinea instrucciones y herramientas: no debe quedar una skill pidiendo tools inexistentes.
- Respeta el two-stage review obligatorio definido en esta fase.
- Si no hay runtime de subagente, degrada de forma explicita y registrada.
- Deep Track debe registrar motivo y costo.

## Plan operativo original

## Fase 9 - Delegacion y Deep Track Real

### Objetivo

Cerrar la inconsistencia actual de delegacion.

### Archivos a revisar

```text
cortex/mcp/server.py
.cortex/skills/cortex-SDDwork.md
cortex/setup/cortex_workspace.py
tests/integration/mcp/test_server.py
```

### Opcion A

Exponer tools MCP:

```text
cortex_delegate_task
cortex_delegate_batch
cortex_get_task_result
```

### Opcion B

Quitar esas referencias de Autopilot y depender solo de delegacion nativa de cada IDE.

### Recomendacion

Opcion A, pero marcada como experimental.

### Two-stage review obligatorio

Cualquier resultado de delegacion debe pasar por el protocolo two-stage review definido en la seccion 9.5. El servicio `AutopilotService` debe:

1. Recibir el `DelegationResult` del subagente.
2. Ejecutar Stage 1 (spec compliance) automaticamente.
3. Si pasa, el agente orquestador ejecuta Stage 2 (quality review).
4. Solo si ambos pasan, se registra checkpoint y se acepta.
5. Si falla, se rechaza con `rejection_reason` y se re-despacha o se degrada a manual.

### Checklist

- [ ] La skill y el MCP dicen lo mismo.
- [ ] Si no hay runtime de subagente, Autopilot degrada a Fast Track o pide confirmacion.
- [ ] Deep Track registra motivo y costo.
- [ ] `DelegationResult` incluye diff, archivos, y resultado de tests.
- [ ] Resultados rechazados quedan registrados en el event log con motivo.

### Gate de salida

- No hay instrucciones que pidan tools inexistentes.

---

