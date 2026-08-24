# Progreso STREAM A — Obra 07 (P6 + P7)

> Registro exclusivo del stream A. La integración documental central
> (ESTADO-ACTUAL.md / HANDOFF.md) se hace en sesión posterior — regla §4b.6.
> Plan maestro: docs/transformacion/08-MIGRACION-TOTAL-RUST.md §4/§4b.

| Fase | Estado | Gate | Evidencia |
|---|---|---|---|
| P6 cortex-actions | ✅ COMPLETA | catálogo/scheduler parity + `next --stats` JSON + pct_motor igual → **16/16 byte-a-byte** | `bench/results/p6-evidencia.json` · goldens `bench/parity/golden_actions/` |
| P7 context (cortex-app) | 🔄 en curso | bundles --json idénticos vs oráculo | — |

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

---
