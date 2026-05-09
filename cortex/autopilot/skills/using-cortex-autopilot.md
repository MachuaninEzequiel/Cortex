---
name: using-cortex-autopilot
description: Meta-skill minima de bootstrap para Cortex Autopilot.
---

# Using Cortex Autopilot

## Prioridad de instrucciones

1. Instrucciones explicitas del usuario (AGENT.md, system-prompt.md, requests directos) — maxima prioridad
2. Skills de Cortex Autopilot — sobreescriben comportamiento default del sistema
3. Prompt de sistema del IDE — minima prioridad

Si el usuario dice "no uses preflight" y Autopilot dice "siempre usa preflight", segui al usuario. El usuario tiene el control.

## Regla de memoria

NO uses herramientas de memoria externa (`engram_*`, `mem_*`, `save_memory`). Usa solo `cortex_*`.

## Cuando activar preflight

- El usuario pide modificar, crear o borrar archivos.
- Hay ambiguedad en el pedido (mas de una interpretacion posible).
- El pedido menciona dominios desconocidos o nuevos.

## Cuando evitar preflight

- Pregunta puramente informativa sin cambios de archivos.
- El usuario da instrucciones explicitas de saltarlo.
- Modo `autopilot` con request claro y bajo riesgo (usa criterio propio).

## Presupuesto de contexto

| Caso | Max items | Max chars |
|---|---:|---:|
| question-only | 0 | 0 |
| docs-only | 3 | 1200 |
| fast code | 5 | 2000 |
| deep task | 8 | 3500 |
| finish auto | n/a | 2000 |

Llama `cortex_context` en formato compacto. No ejecutes `sync-vault` salvo instalacion, reparacion o comando explicito.

## Regla de documentacion final

Todo cambio observado requiere cierre con `cortex_autopilot_finish` o un checkpoint. Si no documentas, queda auto-draft incompleto.

## Tracks

- **Fast Track por defecto**: tareas de 1-2 archivos, cambios simples.
- **Deep Track solo si**: complejidad alta, multiples sistemas, o el usuario pide SDD explicitamente.

## Manejo de fallas de tool

Si una tool falla:
1. Informa el error en el checkpoint.
2. No inventes resultado.
3. Decide si continuar, degradar a Fast Track, o pedir confirmacion al usuario.

## Senales de que estas saltando el flujo

Si te encontras pensando alguna de estas cosas, PARA. Estas racionalizando.

| Pensamiento | Realidad |
|-------------|----------|
| "Es una pregunta simple, no necesito preflight" | Si modifica archivos, necesita al menos un checkpoint |
| "Ya se la respuesta, no busco contexto" | El contexto tiene informacion que no recordas. Usa cortex_context |
| "Documento despues" | El cierre automatico no inventa. Si no documentas, queda auto-draft |
| "No vale la pena una session note" | Si hubo cambios observados, vale la pena |
| "Cortex ya tiene toda la info" | Verifica con cortex_context antes de asumir |
| "Es solo un fix rapido" | Los fix rapidos sin contexto son los que mas rompen |
| "Puedo saltar el checkpoint" | Si cambiaste archivos, el checkpoint protege tu trabajo |
| "No necesito verificar, se que funciona" | Ejecuta el comando de verificacion. Confianza != evidencia |
| "Esto es muy simple para el flujo completo" | Lo simple con proceso es rapido. Lo simple sin proceso se complica |

## Regla de verificacion

Antes de afirmar que un cambio funciona:

1. Identifica que comando prueba tu afirmacion (test, build, lint).
2. Ejecuta el comando COMPLETO (no parcial, no de memoria).
3. Lee la salida completa. Verifica exit code.
4. Solo entonces afirma el resultado.
5. Si no ejecutaste verificacion, escribi "No verificado" en el checkpoint.

NO es aceptable:
- Decir "deberia funcionar" sin haber corrido tests
- Decir "listo" sin verificar que compila
- Confiar en el reporte de un subagente sin verificar el diff
- Usar "probablemente", "seguramente" o "deberia" para describir estado
