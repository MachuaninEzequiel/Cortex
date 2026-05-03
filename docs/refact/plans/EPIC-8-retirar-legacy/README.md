# EPIC 8 — Retirar Compatibilidad Legacy

**Semaforo:** 🔴 Rojo  
**Dependencias:** EPIC 7 completa + 1-2 versiones de convivencia  
**Estado:** ⬜ Postergado — No ejecutar en la misma release que la migración

## Objetivo

Eliminar deuda de compatibilidad una vez estabilizado el sistema.

## Condiciones mínimas para autorizar

- Al menos 1-2 versiones de convivencia
- Zero blockers en IDE/MCP/WebGraph
- Guía de migración publicada y validada
- Evidencia de que el layout nuevo es el dominante

## Tasks

| # | Task | Descripción | Estado |
|---|------|-------------|--------|
| 1 | Remover discovery legacy | Eliminar la rama legacy de `WorkspaceLayout.discover()`. Solo buscar layout nuevo. | ⬜ |
| 2 | Remover DeprecationWarning y paths legacy | Eliminar `legacy_*` methods, `DeprecationWarning` en `project_root`, y todos los fallbacks. | ⬜ |
| 3 | Remover tests legacy | Eliminar tests que verifican layout legacy. Actualizar `.gitignore` solo con paths nuevos. | ⬜ |

## Rollback

- No retirar legacy si alguna integración principal todavía depende de él