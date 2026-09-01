# PROMPT STREAM B — P13 "integración-y-operación" (pegar en terminal dedicada distinta)

Sos el agente del **Stream B** ("integración-y-operación") de la fase **P13
(Companion Engine)** de Cortex. Ponete en contexto leyendo EN ESTE ORDEN,
sin saltarte ninguno:

1. `docs/transformacion/PROMPT-P13-B.md` (este archivo — son reglas vinculantes)
2. `docs/transformacion/11-COMPANION-ENGINE-P13.md` (LA SPEC COMPLETA — leela ENTERA, incluidos los anexos A-I)
3. `docs/transformacion/HANDOFF.md` (sección "HANDOFF ACTIVO"; §4.8 ya está RESUELTO)
4. `docs/transformacion/progreso-p13b.md` (tu único registro de progreso — si no existe, crealo)

## PRECONDICIÓN DE ARRANQUE (verificar antes de escribir código)

P12 debe estar CERRADA: `P12A-9` (mcp handlers) y `P12B-8` (CLI clap nativo)
commiteados. Verificalo con `git log --oneline -20` y el final de
`progreso-p12a.md` / `progreso-p12b.md`. Si NO está cerrada: STOP, avisá y
no avances.

## TERRITORIO (solo tuyo)

- `rust/crates/cortex-companion/`: `Cargo.toml`, `src/lib.rs` (tipos EXACTOS
  del Anexo B del doc 11), `src/auth.rs`, `src/client.rs`, `src/bin/*`
  (stubs compilables al inicio; client.rs lo completás en tu R7)
- `rust/Cargo.toml`: alta append-only del member nuevo + deps aprobadas
  (`notify`) — validar `cargo metadata -q` tras cada edit
- `rust/crates/cortex-config/`: `CompanionConfig` (§8.1, serde default/skip)
- `rust/crates/cortex-cli/`: subcomandos `pair init [--node]`,
  `pair install-agent`, `pair install-hook`, `remote status/sync/drain`
  + hooks de delegación de reads (§9)
- `rust/crates/cortex-doctor/`: checks `pm_companion_*` ×4 (§11)
- `docs/transformacion/ADR-COMPANION-{0,1,2,3}.md` (nuevos, contenido §14 del doc 11)
- README.md: SOLO la sección nueva "Companion Engine" + fila en COMPARE
- Gates `bench/parity/*p13b*` y ÚNICAMENTE `docs/transformacion/progreso-p13b.md`

PROHIBIDO tocar: `cortex-app`, `cortex-mcp`, `cortex-brain`, dentro del crate
companion los archivos `src/{sync,daemon,agent}.rs` (del stream A — exponé
los tipos que necesita en lib.rs según Anexo B), HANDOFF.md,
ESTADO-ACTUAL.md, docs 09/12, ni nada de `bench/parity/*p13a*`.

## TU PRIMER GATE ES EL QUE HABILITA AL STREAM A (hacelo temprano)

### Gate R0-B — scaffolding + ADRs (commit rápido, primera prioridad)

1. Escribí los 4 ADRs (`ADR-COMPANION-0..3.md`, contenido §14 del doc 11;
   el 0 registra la decisión wire-format YA FIRMADA por el dueño).
2. Alta del member en workspace Cargo.toml + esqueleto del crate:
   `lib.rs` con TODOS los tipos del Anexo B (HelloInfo, HealthInfo,
   ManifestEntry con orden canónico, ManifestRequest/Reply, OpPayload tag
   snake_case, Op, CompanionError), `auth.rs` IMPLEMENTADO (token file
   0600 + constant-time compare + tests), `client.rs` y bins como stubs
   compilables.
3. Verificación OBLIGATORIA: golden P1 intacto — los dumps de config deben
   seguir PASSando SIN recaptura (`load_and_dump` opera sobre Value crudo;
   CompanionConfig nunca materializa defaults). Corré el golden de config
   existente y registrá el resultado en progreso-p13b.md.
4. Commit `feat(obra13 R0-B)` ANUNCIÁNDOLO en tu progreso (el stream A está
   esperando este commit para tocar daemon/sync).

## TU COLA DE GATES (un commit por gate)

| Gate | Contenido | Criterio de pase |
|---|---|---|
| R0-B | ADRs ×4 + scaffolding crate + auth.rs + golden P1 intacto | cargo metadata ok · clippy/fmt · tests auth · golden config PASS sin recaptura |
| R7 | `CompanionConfig` + subcomandos pair/remote + delegación reads + fallback | G-R3 del doc 11: fallback local <1 s con WARN explícito; `cortex search --json` remoto==local; exit codes idénticos; handshake mismatch ⇒ fallo `COMPANION_VERSION_MISMATCH` documentado |
| R9a | doctor checks pm_companion_{reachable,version_match,replica_lag,outbox} | enabled=false ⇒ `skipped`; estados OK/WARN/FAIL según §11 |
| R8 | brain en Node: guía SSH en README + alias sugerido por `pair init --node` | eval manual scriptada documentada (chat + tool suggestion sobre réplica) |
| R9b | README sección Companion Engine + runbook pair (Anexo E) + fila COMPARE con RAM liberada medida | suite completa verde · docs completas |

Prefijo de commits: `feat(obra13 R0-B/R7/… B)`.

Nota de coordinación para R7: la delegación de reads consume `client.rs`
(tuyo) contra un cortexd REAL montado por el stream A en sus gates R2-R4.
Si al llegar a R7 el daemon de A aún no corre en loopback, probá tu CLI con
un stub de server mínimo EN TUS TESTS (no toques sus archivos); la paridad
final se valida cuando ambos lados estén en trunk.

## ⚠️ GUARDARRAILES DE RECURSOS (VINCULANTES — sesiones anteriores murieron por RAM)

Máquina: 11 GiB RAM / 20 cores, DOS streams en paralelo. Obligatorio:

- **R0.** Al arrancar: `pgrep -af "pytest|cargo|python"` — matá zombis heredados.
- **R1.** Exportá al inicio:
  ```bash
  export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
         NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=6
  ```
- **R2. Verificación POR NIVELES:** Nivel 1 (iteración libre):
  `cargo fmt --all --check && cargo clippy -p <tu-crate> --all-targets -- -D warnings && cargo test -p <tu-crate>`.
  Nivel 2 (pre-commit): tu golden build/verify. Nivel 3 (oráculo Python
  `.venv/bin/python -m pytest tests/unit tests/integration --no-cov`): UNA vez
  por tarea, justo antes del commit, SIEMPRE bajo lock R3. PROHIBIDO durante iteración.
- **R3. LOCK de operaciones pesadas:**
  ```bash
  while ! mkdir .cortex/heavy.lock 2>/dev/null; do sleep 30; done
  trap 'rmdir .cortex/heavy.lock' EXIT
  ```
  Antes de entrar: `free -m` → available < 4000 MB ⇒ esperá 60 s y reintentá.
- **R4.** Todo comando potencialmente pesado envuelto en `timeout 1200 <cmd>`.
- **R5.** Un solo proceso pesado a la vez.
- **R6. COMMIT TEMPRANO:** gate verde ⇒ commit atómico INMEDIATO + actualizar
  `progreso-p13b.md`. Lo no commiteado se pierde si morís.
- **R7.** `git add` SOLO tus archivos. Fuera de todo commit: `uv.lock`,
  `progress.md`, artefactos runtime.

## Reglas heredadas vigentes

Paridad bit-exacta como contrato · fallo explícito ante cualquier condición
no soportada (patrón P6/P9) · un gate por commit · sin dependencias nuevas
sin ADR (notify queda aprobada por tu ADR-COMPANION-2) · suite Python =
ORÁCULO compartido (lock R3) · wire-format MCP resuelto: omisión rmcp
canónica (Anexo A doc 11) · el addon es OPCIONAL: con `[companion] enabled=false`
el comportamiento de TODO el CLI debe ser byte-idéntico al actual.

## Definición de hecho de tu stream

R0-B, R7, R9a, R8, R9b commiteados con gates verdes + suite Python oráculo
verde en cada commit + `progreso-p13b.md` con evidencia por gate. Al
terminar: anunciá "STREAM B P13 COMPLETO" y dejá registrado qué falta del
lado A para el cierre integral.
