# ESTADO ACTUAL DEL PROGRAMA

> **HANDOFF DE SESIÓN**: leé primero `docs/transformacion/HANDOFF.md` — contiene el
> contexto completo, commits, decisiones tomadas y los próximos pasos precisos.

## Estado al cierre de esta sesión (2026-08-23, actualización intermedia)

- TRAMO 0 ✅ · ola 1 ✅ · OBRA 02 ✅ · **OBRA 01: P2 ✅ P3 ✅ · P4 EN CURSO**
  (pr-context/hu/common extraídos + embedding/mcp con register(); main.py 2540→2231;
  falta trío documenting → cli/documenting.py).
- **P-bugs**: #3 ✅ (verificado resuelto por Obra 02, marcadores pi) · #4 ✅ (ya resuelto
  en TRAMO 1, test existente) · #5 ✅ (cache key con scope desde ola 1) · #6 ✅
  (storage.mutate() verificado en los 3 puntos de mutación) · #7 ✅ fix commiteado
  (coverage gate escribe/lee /tmp/test-output.txt vía tee+PIPESTATUS; pip-audit sin || true)
  · #8 ✅ (TRAMO 0) · #10 ✅ fix commiteado (get_item_note HU-{external_id} + fallback slug,
  tests golden nuevos). Queda solo #9 ✅ (fix decay_rate commiteado) — P-bugs COMPLETOS.
- Bug #9 ✅: DecayConfig respeta decay_rate explícito ≠ default; path enrichers intacto.
- Deudas: requirements.txt ELIMINADO (fuente única pyproject); _resolve_cache ya usaba
  layout (cerrada con evidencia); CHANGELOG [Unreleased]×8 queda para el momento de
  release (decisión de versión = del dueño).
- Suite unit+integration: VERDE (**2290 passed**, 13 skipped). Rama:
  feature/transformacion-2026-08. master sellado.

## Próximos pasos (detalle en HANDOFF.md §5)

1. Obra 01: terminar P4 (documenting trio) → P5 → P6 (mixins schemas; V7 devsecdocops;
   cerrar V4) → P7 → P8.
2. Obra 03: T-BENCH-1 harness + baseline.
3. Cierre Obra 04 CON EL DUEÑO: reindex vault real + flip default global (int8 pendiente).
4. Obra 05: arrancar fases A-B.
5. Obra 06 (LFM2.5): futuro.
