# ESTADO ACTUAL DEL PROGRAMA

> Actualizar SIEMPRE al terminar una sesión de trabajo. Máximo ~40 líneas.

## Sesión 2026-08-21/22 — TRAMO 0 completo + TRAMO 1 fase P-bugs/P1 completa

- Deep review 12/12: docs/reviews/2026-08-deep-review/. Sello: tag v0.5.0-baseline-seal @ a64e350 (pusheado).
- Rama del programa: feature/transformacion-2026-08.
- Planes ejecutables 01..05 completos en docs/transformacion/.
- TRAMO 0 (commits 798775c, 788c5c4): pin mcp<2, fix tar-slip, suite verde (86 -> 0).
- TRAMO 1 primera ola (5 commits e9b3e4e..bf5bd3b, suite unit+integration exit 0):
  - ide uninstall seguro (pi/codex/cursor) + tests de caracterización TDD
  - session: mutate() transaccional anti lost-update + designer MANAGED + close con fallback git
  - webgraph: cache por scope + 404 limpios + mode validado + legend en API
  - cli: --dry-run real en los 4 setups
  - poda P1: 6 ítems muertos eliminados
- Pendientes P2 clasificados por fix-p1-deadcode: NoActiveSession, ScoringWithDecay/decay API,
  is_known_agent/_KNOWN_AGENTS, extra_notes/forced_reason, F841 de tests e2e.

## Próximo paso

- Obra 02 Fase 0-1: caracterización de los 11 adapters + helpers compartidos de marcadores en base.py
  (los bugs #3/#6 ya resueltos facilitan la Fase 2 de migración al contrato IDEAdapterV2).
- Después: P3 golden tests MCP + split server.py (ALTO riesgo, congelación hasta entonces).
- Nota flake: test_setup_dry_run_creates_nothing mostró 1 fallo no reproducible (pollution de orden);
  vigilar en próximas corridas.
