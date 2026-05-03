# EPIC 0 — Definir el Contrato de Layout

**Semaforo:** 🔴 Rojo  
**Dependencias:** Ninguna (primera epic)  
**Documento padre:** Sección 7 del REFAC-WORKSPACE-STRUCT.md  

## Objetivo

Congelar una única verdad semántica para el nuevo workspace antes de tocar los consumidores. Crear el módulo `cortex/workspace/layout.py` con la API completa de `WorkspaceLayout`.

## Gate de Salida

- [ ] El layout final está documentado sin contradicciones
- [ ] Existe una regla única y declarativa para resolver cualquier path interno
- [ ] `WorkspaceLayout` implementado con discovery, resolución y compatibilidad legacy
- [ ] Tests unitarios de `WorkspaceLayout` pasan con ambos layouts (nuevo y legacy)
- [ ] El documento REFAC está actualizado con el contrato final

## Tasks

| # | Task | Archivos principales | Estado |
|---|------|---------------------|--------|
| 1 | Crear módulo `cortex/workspace/` con API de `WorkspaceLayout` | `cortex/workspace/__init__.py`, `cortex/workspace/layout.py` | ✅ |
| 2 | Implementar discovery con precedencia (nuevo → legacy → bootstrap) | `cortex/workspace/layout.py` | ✅ |
| 3 | Escribir tests unitarios de `WorkspaceLayout` | `tests/unit/workspace/test_layout.py` | ✅ |
| 4 | Congelar documento y verificar contrato | `docs/refact/REFAC-WORKSPACE-STRUCT.md` | ⬜ |

## Riesgos

- Elegir una base de resolución equivocada y propagar el error a todo el sistema
- Dejar fuera del contrato piezas reales (workspace.yaml, scripts_dir, logs_dir)

## Notas

- Esta fase es de definición. No se toca ningún archivo consumidor.
- El contrato define `workspace_root = repo_root / ".cortex"` y todos los paths relativos se resuelven contra ese root.