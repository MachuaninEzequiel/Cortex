# ESTADO ACTUAL DEL PROGRAMA

> **PRÓXIMA SESIÓN = MIGRACIÓN RUST.** Leé primero `HANDOFF.md` §TAREA-RUST (tarea
> explícita con pasos R0-R6) + `07-AUDITORIA-2026-08-24.md` (auditoría de realidad
> con todos los hallazgos resueltos). Plan técnico: `03-MIGRACION-RUST.md`.

## Estado al cierre de la sesión de auditoría y pulido (2026-08-24)

- TRAMO 0 ✅ · ola 1 ✅ · OBRA 02 ✅ · OBRA 01: **P2 ✅ P3 ✅ P4 ✅ P5 ✅ P6 ✅ P7 ✅ P8 ✅**
  · **P-BUGS COMPLETOS** (#3,#4,#5,#6 verificados resueltos; #7,#9,#10 arreglados con test)
  · Deudas: requirements.txt eliminado, _resolve_cache ya OK, V4 cerrada (factory), V7 ✅,
  V11 cerrada (lazy-deprecation existente), V12 ✅ GC tmp.
- **OBRA 03 A1 ✅**: bench/bench_harness.py + vault-synth-1k determinista commiteado +
  baseline-2026-08-23.json (webgraph O(n²) n1000=3.2s · full_sync_1k=37s · retrieve p99=129ms).
- **OBRA 04**: recomendación default global documentada (per-language; flip+reindex=dueño);
  int8 con plan concreto pendiente de ejecución.
- **OBRA 05 Fase A 1/4 ✅**: FeedbackStore JSONL + hook opcional en collector.
  **Fase A COMPLETA 4/4**: + telemetría cableada (rotación JSONL),
  + APIs públicas SessionService (cero ._storage externo), + guide_path revivido.
  **Fase B COMPLETA**: paquete cortex/action_engine/ (models/store/registry/
  scheduler/runner/learning) + catálogo v1 completo (10 acciones) + comando
  **Fase C COMPLETA**: nivel-0 start/finish + aliases ocultos; help raíz = 8
  visibles exacto; B3/B4 search arreglados (--format honrado siempre);
  **Fase D COMPLETA**: cortex/tui/core.py (Home <300ms + pantallas
  acciones/búsqueda, decisión→Learner→Runner reales), `cortex` sin
  argumentos abre el Home, session --watch deprecado. Sigue Fase E:
  aprendizaje cerrado + pulido i18n.
- Refactors de este tramo: main.py 2540→1894 l (pr-context/hu/embedding/mcp/documenting);
  enricher sync/async unificados vía _finalize_items (V3) con DOS bugs reales corregidos
  (closure de lambdas: todas las estrategias buscaban la última query + drift Fase 08);
  schemas ×13 → mixins (V5); skills embebidos → workspace_files/*.md (V8, -1400 l);
  V9 ciclo session↔documenter roto con TYPE_CHECKING + guardia de arquitectura.
- Suite unit+integration: VERDE (**2347 passed**, 13 skipped). Rama:
  feature/transformacion-2026-08. master sellado.
- Deudas restantes registradas: F821 cli/main.py `cortex_ide` (P-bugs),
  F821 ×5 WorkspaceLayout en templates.py (TYPE_CHECKING, cosmético),
  `_sync_vault_text` candidato de poda, CHANGELOG para momento de release.

## Próximos pasos (detalle en HANDOFF.md §5)

1. Obra 01: terminar P4 (documenting trio) → P5 → P6 (mixins schemas; V7 devsecdocops;
   cerrar V4) → P7 → P8.
2. Obra 03: **T-BENCH-1 ✅** (baseline-2026-08-23.json commiteado). Sigue T-EVAL-1 (queries anotadas, junto Obra 04) y T-CARGO-1 (workspace rust).
3. Cierre Obra 04 CON EL DUEÑO: reindex vault real + flip default global (int8 pendiente).
4. Obra 05: arrancar fases A-B.
5. Obra 06 (LFM2.5): futuro.
