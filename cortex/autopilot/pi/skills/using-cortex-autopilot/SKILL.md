---
name: using-cortex-autopilot
description: Bootstrap minimo para usar Cortex Autopilot en Pi sin cargar todo el workflow manual.
---

# Using Cortex Autopilot in Pi

Pi esta gobernado por Cortex Autopilot cuando esta skill esta instalada.

## Reglas

1. **Usa solo herramientas Cortex** (`cortex_*` o `cortex_autopilot_*`) para memoria.
2. **No uses memoria externa** (`engram_*`, `mem_*`, `save_memory`, `session_summary`).
3. **Directo por defecto**: implementar sin subagentes para tareas cotidianas.
4. **Subagentes / SDD solo si** el usuario lo pide explicitamente.
5. **No declares una tarea completa** sin que Autopilot o `cortex-documenter` hayan persistido la sesion.
6. **Mantene el contexto compacto**: no cargues todo el vault si no hace falta.
7. **Si Autopilot falla**, informa el bloqueo y continua en modo manual Cortex.

## Presupuesto de contexto

| Caso | Max items | Max chars |
|---|---:|---:|
| question-only | 0 | 0 |
| docs-only | 3 | 1200 |
| fast code | 5 | 2000 |
| deep task | 8 | 3500 |
| finish auto | n/a | 2000 |

Llama `cortex_context` en formato compacto. No ejecutes `sync-vault` salvo instalacion, reparacion o comando explicito.
