# Progreso STREAM A — Obra 07 (P6 + P7)

> Registro exclusivo del stream A. La integración documental central
> (ESTADO-ACTUAL.md / HANDOFF.md) se hace en sesión posterior — regla §4b.6.
> Plan maestro: docs/transformacion/08-MIGRACION-TOTAL-RUST.md §4/§4b.

| Fase | Estado | Gate | Evidencia |
|---|---|---|---|
| P6 cortex-actions | ✅ COMPLETA | catálogo/scheduler parity + `next --stats` JSON + pct_motor igual → **16/16 byte-a-byte** | `bench/results/p6-evidencia.json` · goldens `bench/parity/golden_actions/` |
| P7 context (cortex-app) | ✅ COMPLETA | bundles --json idénticos vs oráculo → **3/3 byte-a-byte** (oráculo determinista verify 3/3) | `bench/results/p7-evidencia.json` · goldens `bench/parity/golden_context/` |

---

## P6 — crate `cortex-actions` (2026-08-24)

**Alcance porteado** (fuente: `cortex/action_engine/`, 864 líneas; spec:
`tests/unit/action_engine/`): models, store (ActionLog JSONL +
PreferencesStore YAML formato-compatible), registry, scheduler, signals
(±25%), metrics (pct_motor), runner, learning, ActionContext (layout
legacy/nuevo), catálogo v1 completo (10 acciones).

**Gate de paridad** (`bench/parity/actions_golden_p6.py` + example
`actions_check.rs`): 4 escenarios deterministas (base / preferencias /
git-dirty / sin-config) × 4 salidas (`next --stats`, `next --json`,
`--explain-why-not`, texto) = 16/16 byte-a-byte contra el CLI Python,
incluido el orden de claves y el repr de floats. Normalizaciones pactadas:
`{{ROOT}}` y `{{MS}}`. El modo `verify` regenera fixtures frescos en temp y
compara contra lo commiteado (determinismo probado).

**Verificación**: `cargo test -p cortex-actions` 35 passed · clippy -D
warnings limpio · fmt limpio · suite Python completa verde (2455 passed,
2 corridas consecutivas) · regresión goldens P0 (doctor, next_stats) PASS.

**Decisiones registradas** (detalle en p6-evidencia.json):
1. El CLI `next` no inyecta señales al Scheduler (solo TUI/brain): paridad
   CLI con dominio neutro; lógica ±25% espejada en unit tests.
2. Los 7 tópicos del tutor entran como datos estáticos para `learn.topic`.
3. Rutas reales que dependen de servicios no nativos aún devuelven fallo
   explícito documentado (sync_vault→P12, DocValidator→cola larga, 
   inject_all→P8); precondiciones y dry-runs son 100% nativos.
4. `quality.run_gates` real es un quirk del oráculo (ReviewVerdict ==
   "accept" siempre False): no se finge paridad, se declara.
5. Dependencia única cortex-actions→cortex-app es lectura de sesiones
   (formato P4); sin ciclo posible.

## P7 — módulo `context` en cortex-app (2026-08-24)

**Alcance porteado** (fuente: `cortex/context_enricher/`, ~3184 líneas; spec:
`tests/unit/context_enricher/`; detalle en p7-evidencia.json):
pipeline completo del ContextEnricher sobre las nativas episódica (P3) y
semántica (P2b): estrategias topic/files/keywords/pr_title vía RRF híbrido
adaptativo + entity_search (con cotas y dedup del oráculo), finalize_items
como fuente única sync/async: merge mayor-score por source_id, multi-match
boost ×1.5^(n−1), co-ocurrencia naive + grafo tipado, decay temporal (tags
permanentes, floor), feedback implícito, DocIntent boost, umbral min_score,
sort estable y presupuesto max_items/max_chars. Además: budget_resolver (7
perfiles DATA + fallback), models+pyjson con `to_json` byte-compatible al
ContextPresenter (`indent=2`, `ensure_ascii=False`, repr floats CPython,
orden de claves de inserción), y edits aditivos a episodic/mod.rs
(entity_search/entity_match_score) y lib.rs.

**Gate de paridad** (`bench/parity/context_golden_p7.py` build/verify +
example `context_check.rs`): 3 casos deterministas — caso_a_topic (1 query,
decay mixto), caso_b_multi (4 estrategias + entidades + grafos + feedback:
31 raw hits / 6 items), caso_c_budget_prtitle (perfil deep-code ⇒ top_k=8) —
comparados **byte-a-byte** contra el CLI Python tras las normalizaciones
pactadas: `{{ROOT}}`, floats redondeados a 5 decimales EN AMBOS lados
(ulp-diff onnxruntime vs ort amplificada por boost ×3.375; tolerancia 1e-5;
drift real mayor falla), matched_by ordenado (el oráculo usa list(set)) y
\n final único. Fixture eternamente determinista: timestamps congelados en
2026-01, tags permanentes ⇒ decay 1.0, tipos sin chunking, ids renombrados
mem_p7_NN por orden lexicográfico.

**Fuera de alcance P7 (documentado, no gateado)**: filtros estructurales
(filters.py — parámetro opcional 'Fase 08', el oráculo nunca lo pasa),
observer/telemetría (oráculo usa observer=None), async_enricher (finalize es
fuente única V3 ⇒ una implementación basta), presenter to_text/agrupado
(el gate es --json), domain_detector activo (lo llena el Observer, no enrich).

**Verificación**: oráculo determinista `verify` → 3/3 PASS · paridad Rust
`context_check` → 3/3 byte-a-byte · `cargo test -p cortex-app` 27 passed
(16 nuevos + 11 preexistentes intactos) · clippy -D warnings limpio · fmt
limpio · suite Python completa verde (**2455 passed, 18 skipped**).

**Decisiones registradas**:
1. Entity search cuenta hits en total_raw_hits pero NO genera items
   (EpisodicHit no es UnifiedHit ni tupla ⇒ conversión None en Python);
   espejado con `dropped=true` + test unitario dedicado.
2. Floats a 5 decimales en ambos lados como contrato escrito del oráculo;
   sin eso la paridad ONNX cross-runtime no es alcanzable byte-a-byte.
3. Los hits episódicos de entity_search llevan score propio del match de
   entidad (1.0+frecuencia+recencia, techo 1.0) — solo afecta raw counts.
4. Edits a lib.rs/episodic aditivos; cero cambios de comportamiento
   preexistente (los 11 tests previos del crate pasan sin modificación).

---
