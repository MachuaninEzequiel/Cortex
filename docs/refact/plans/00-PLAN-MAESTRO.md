# Plan de Ejecución — REFAC-WORKSPACE-STRUCT v2.0

**Documento padre:** `docs/refact/REFAC-WORKSPACE-STRUCT.md`  
**Fecha:** 2026-05-03  
**Estado:** Listo para ejecutar  

---

## Estructura del Plan

```
docs/refact/plans/
├── 00-PLAN-MAESTRO.md          ← Este archivo: visión general, dependencias, orden
├── EPIC-0-contrato-layout/     ← Fase 0
│   ├── README.md               ← Objetivo, gate de salida, riesgos
│   └── TASK-*.md               ← Una task por entregable concreto
├── EPIC-1-compatibilidad-dual/
├── EPIC-2-centralizar-paths/
├── EPIC-3-runtime-critico/
├── EPIC-4-setup-generadores/
├── EPIC-5-ide-mcp-webgraph/
├── EPIC-6-docs-doctor-tests/
├── EPIC-7-activar-default/
└── EPIC-8-retirar-legacy/
```

## Reglas de Ejecución

1. **Una fase a la vez.** No avanzar a la siguiente sin cerrar el gate de salida de la actual.
2. **Cada task se verifica con su checklist.** Si el checklist pasa, la task está done.
3. **El gate de salida de la fase = todos los checklists de sus tasks + los criterios del documento.**
4. **Si una task bloquea, documentar el bloqueo en la task y no avanzar de fase.**
5. **Se ejecuta en orden 0→1→2→3→4→5→6→7.** Fase 8 se ejecuta 1-2 versiones después.
6. **Cada task se commitea en su propia rama** `refac/epic-N-task-M-descripcion`.

## Dependencias entre Fases

```
EPIC 0 ──→ EPIC 1 ──→ EPIC 2 ──→ EPIC 3 ──→ EPIC 4 ──→ EPIC 5 ──→ EPIC 6 ──→ EPIC 7
 (Rojo)     (Rojo)     (Rojo)    (Amarillo)  (Amarillo)  (Amarillo)  (Amarillo)   (Verde)
                                                                                      
                                                                                        ──→ EPIC 8
                                                                                         (1-2 versiones después)
```

## Progreso Global

| Epic | Fase | Semaforo | Estado | Tasks | Hechas |
|------|------|----------|--------|-------|--------|
| EPIC 0 | Contrato de Layout | 🔴 Rojo | ✅ Completada | 4 | 3 |
| EPIC 1 | Compatibilidad Dual | 🔴 Rojo | ✅ Completada | 5 | 5 |
| EPIC 2 | Centralizar Paths | 🔴 Rojo | ✅ Completada | 6 | 6 |
| EPIC 3 | Runtime Crítico | 🟡 Amarillo | ✅ Completada | 6 | 6 |
| EPIC 4 | Setup y Generadores | 🟡 Amarillo | ✅ Completada | 5 | 5 |
| EPIC 5 | IDE, MCP, WebGraph | 🟡 Amarillo | ✅ Completada | 5 | 5 |
| EPIC 6 | Docs, Doctor, Tests | 🟡 Amarillo | ✅ Completada | 6 | 5 |
| EPIC 7 | Activar Default | 🟢 Verde | ✅ Completada | 3 | 2 |
| EPIC 8 | Retirar Legacy | 🔴 Rojo | ⬜ Postergado | 3 | 0 |

**Total: 43 tasks**

## Convención de Nombres de Ramas

```
refac/epic-0-task-1-layout-module
refac/epic-0-task-2-discovery-api
refac/epic-0-task-3-layout-tests
refac/epic-0-task-4-freeze-contract
```

## Cómo Leer y Usar Este Plan

1. Abrir el README de la epic actual
2. Verificar el gate de salida
3. Ejecutar las tasks en orden (cada task dice qué archivo tocar y qué cambiar)
4. Al terminar cada task, tachar su checklist
5. Al terminar todas las tasks de una epic, verificar el gate de salida
6. Si el gate pasa, marcar la epic como ✅ y avanzar a la siguiente

## Cómo se Relaciona con el Documento de Refactoring

- El documento `REFAC-WORKSPACE-STRUCT.md` es la **especificación** — dice qué y por qué
- Este plan es la **ejecución** — dice cómo y en qué orden tocar los archivos
- Si hay contradicción, el documento de refactoring tiene precedencia