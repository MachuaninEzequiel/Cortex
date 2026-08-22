# ESTADO ACTUAL DEL PROGRAMA

> **HANDOFF DE SESIÓN**: leé primero `docs/transformacion/HANDOFF.md` — contiene el
> contexto completo, commits, decisiones tomadas y los próximos pasos precisos.

## Estado al cierre de esta sesión (2026-08-23)

- TRAMO 0 ✅ · TRAMO 1 ola 1 ✅ · OBRA 02 COMPLETA ✅ · OBRA 04 COMPLETA (falta cierre) ·
  **OBRA 01: P2 ✅ + P3 ✅** (split server.py completo: golden contract MCP byte-a-byte,
  vault_adapter único, schemas.py, mixins por dominio en tools/, dispatcher tabla;
  server.py 2977 → 491 líneas; -609 l netas adicionales por poda P2).
- Suite unit+integration: VERDE (2279 passed, 13 skipped). Rama:
  feature/transformacion-2026-08. master sellado con v0.5.0-baseline-seal.
- Modelo elegido y documentado: e5-large (ES) / MiniLM (EN) vía backend fastembed.
- Deudas nuevas para P-bugs (preexistentes, detectadas en P2/P3): F821 latente
  cli/main.py:2233 (`cortex_ide`) y enricher.py:65 (`EnrichmentFilters`).
  Candidato de poda: `_sync_vault_text` (mcp/tools/workspace.py, solo test directo).

## Próximos pasos (detalle en HANDOFF.md §5)

1. Cierre Obra 04: reindex del vault real del dueño + decisión default global + int8 opcional.
2. Obra 01: P4 (adelgazar main.py a subapps) → P5-P8. P-bugs puede correr en paralelo.
   P9 (mcp 2.x) ahora evaluable con split+golden como red.
3. Obra 03: benchmarks (T-BENCH-1) antes de cualquier porteo a Rust.
4. Obra 05: puede arrancar (dependencias cumplidas). feedback_loop reservado intacto.
5. Obra 06 (LFM2.5): futuro; investigación profunda pendiente (doc 06).
