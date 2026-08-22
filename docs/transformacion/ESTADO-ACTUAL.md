# ESTADO ACTUAL DEL PROGRAMA

> **HANDOFF DE SESIÓN**: leé primero `docs/transformacion/HANDOFF.md` — contiene el
> contexto completo, commits, decisiones tomadas y los próximos pasos precisos.

## Estado al cierre de esta sesión (2026-08-23)

- TRAMO 0 ✅ · TRAMO 1 ola 1 ✅ · OBRA 02 COMPLETA ✅ · OBRA 04 COMPLETA (falta cierre) ·
  **OBRA 01 P2 COMPLETA ✅** (poda BORRAR CON TEST: -609 l netas; decay decorativo,
  co_occurrence AST/query muerto, is_known_agent, NoActiveSession, forced_reason/
  extra_notes, --no-graph, F841/F401 rezagados; ruff+vulture en 0).
- Suite unit+integration: VERDE (2271 passed, 13 skipped). Rama:
  feature/transformacion-2026-08. master sellado con v0.5.0-baseline-seal.
- Modelo elegido y documentado: e5-large (ES) / MiniLM (EN) vía backend fastembed.
- Deudas nuevas para P-bugs (preexistentes, detectadas en P2): F821 latente
  cli/main.py:2233 (`cortex_ide`) y enricher.py:65 (`EnrichmentFilters`).

## Próximos pasos (detalle en HANDOFF.md §5)

1. Cierre Obra 04: reindex del vault real del dueño + decisión default global + int8 opcional.
2. Obra 01: P3 (golden tests MCP + split server.py — ALTO riesgo) → P4-P8.
   Pendientes menores anotados en plan 01 §1/§7: knob domain_confidence → P-bugs;
   fix bug #9 (__post_init__ decay_rate) → P6.
3. Obra 03: benchmarks (T-BENCH-1) antes de cualquier porteo a Rust.
4. Obra 05: puede arrancar (dependencias cumplidas). feedback_loop reservado intacto.
5. Obra 06 (LFM2.5): futuro; investigación profunda pendiente (doc 06).
