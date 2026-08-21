# ESTADO ACTUAL DEL PROGRAMA

> Actualizar SIEMPRE al terminar una sesión de trabajo. Máximo ~40 líneas.

## Sesión 2026-08-21 (creación + TRAMO 0 completo)

- Deep review 12/12 subsistemas: docs/reviews/2026-08-deep-review/ (commiteado).
- Sello del estado previo: tag `v0.5.0-baseline-seal` @ a64e350 (pusheado a origin). master restaurado al sello.
- Rama de trabajo del programa: `feature/transformacion-2026-08`.
- Planes completos y ejecutables de las 5 obras en docs/transformacion/01..05.
- **TRAMO 0 COMPLETO** (commit 788c5c4):
  - pin `mcp>=1.2.0,<2` → 77 fallos resueltos.
  - fix tar-slip en restore_backup (+2 tests).
  - 10 fallos reales restantes corregidos/actualizados al contrato vigente.
  - Suite unit + integration: VERDE (exit 0). Nota: tests/e2e y extras [webgraph] requieren env propio; flask instalado en .venv local.

## Próximo paso

- Iniciar TRAMO 1 en paralelo:
  - Obra 01 fases P1 (podas triviales) y P-bugs (#3 pi.uninstall destructivo, #6 cwd bugs, dry-run fake).
  - Obra 02 Fase 0-1 (tests de caracterización de adapters + helpers compartidos).
- Recordar congelación: server.py/main.py sin tocar hasta P3/P4.
