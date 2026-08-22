# ESTADO ACTUAL DEL PROGRAMA

> **HANDOFF DE SESIÓN**: leé primero `docs/transformacion/HANDOFF.md` — contiene el
> contexto completo, commits, decisiones tomadas y los próximos pasos precisos.

## Estado al cierre de esta sesión (2026-08-22)

- TRAMO 0 ✅ · TRAMO 1 ola 1 ✅ · OBRA 02 COMPLETA ✅ · OBRA 04 COMPLETA ✅
- Suite unit+integration: VERDE. Rama: feature/transformacion-2026-08. master sellado
  con v0.5.0-baseline-seal.
- Modelo elegido y documentado: e5-large (ES) / MiniLM (EN) vía backend fastembed.

## Próximos pasos (detalle en HANDOFF.md §5)

1. Cierre Obra 04: reindex del vault real del dueño + decisión default global + int8 opcional.
2. Obra 01: P2 → P3 (golden tests MCP + split server.py) → P4-P8.
3. Obra 03: benchmarks (T-BENCH-1) antes de cualquier porteo a Rust.
4. Obra 05: puede arrancar (dependencias cumplidas).
5. Obra 06 (LFM2.5): futuro; investigación profunda pendiente (doc 06).
