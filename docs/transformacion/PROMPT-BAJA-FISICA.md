# PROMPT BAJA DEFINITIVA — FASE FÍSICA (paquete final)

> **Paquete separado post-RUTA 2** — ejecutar la baja física de Python según
> doc 12 §7 punto 6 / §9.6: CORTEX_PY=1 → rollback histórico, passthrough
> eliminado, goldens archivados, README a binarios, wheel Python = legado
> congelado. Precondiciones cumplidas: Obra 07 + RUTA 1 + RUTA 2 completas,
> passthrough = SOLO CORTEX_PY=1 + catch-all (head `6612449`).

## Contexto en 30 segundos

El CLI nativo wireó TODO lo que el oráculo expone. Restan mecanismos de
la transición que hay que liquidar:

1. **`main.rs` pasos 1 y 4** → `fallback::passthrough` (delegar a Python):
   - paso 1: `CORTEX_PY=1` → passthrough total (rollback)
   - paso 4: catch-all de comandos no wireados → passthrough
2. **`memory_cmds.rs:762`**: `reindex` sin `--dry-run` → passthrough
   (el `--dry-run` ya es nativo).
3. **Goldens `bench/parity/*_golden*.py`** (~30 scripts + dirs de salida)
   — oráculos de paridad contra Python: LIVING pero ya sin contraparte de
   desarrollo (todo wireado). Se ARCHIVAN.
4. **README** instalación → binario nativo; **wheel Python** → legado.
5. **`init`**: en el oráculo es alias de `setup agent` (`main.py:796`).
   Hoy cae al catch-all → passthrough. Se wirea como alias nativo trivial.

## Decisiones de diseño (verificadas, vinculantes)

- **`CORTEX_PY=1` → histórico**: el paso 1 de main.rs imprime un aviso
  (`CORTEX_PY=1 es rollback histórico de la migración — el CLI es 100%
  nativo; eliminá la variable`) y CONTINÚA el flujo nativo (no delega).
- **Catch-all → error Typer-como**: comando desconocido →
  `No such command '{first}'.` + rc 2 (exactamente el comportamiento de
  Typer con un comando inexistente; precedente: rechazo de install/
  uninstall en autopilot.rs). Elimina `fallback::passthrough` y el módulo
  `fallback.rs` (o lo deja como histórico documentado si algún test lo
  referencia — ver abajo).
- **`reindex` real → fallo explícito P6/P9**: NO existe escritor de
  vector-cache persistente nativo (verificado: sin `NativeVectorCache` en
  Rust) → el modo real (sin `--dry-run`) imprime mensaje explícito
  "reindex real no nativo en build Rust (requiere escritor de vectors
  persistente; usá --dry-run o el CLI Python con CORTEX_PY=1 legacy)" y
  rc != 0. El `--dry-run` sigue nativo byte-parity.
- **`init`**: wirear como alias de `setup agent --non-interactive`? NO —
  el oráculo `init` sola NO pasa `--non-interactive` (lo deja opcional).
  Wirear `init [--non-interactive]` → despacha a `setup_cmd` agente con
  el flag. Verificar el oráculo `init` (main.py:796-806) para flags.
- **Archivo de goldens**: `git mv bench/parity/*_golden*.py` +
  `bench/parity/golden*/` etc. → `bench/parity/archive/` + README-archivo.md
  histórico (qué validaban, cómo reactivarlos). Se conserva la suite
  Python (oráculo CI vivo: `ci-gates.yml` corre pytest unit+integration
  y cargo; NO corre goldens — verificado).
- **README**: sección instalación pasa a `cargo install --path
  rust/crates/cortex-cli` (o build release + copiar binario); el wheel
  Python `cortex-memory` queda documentado como legado congelado
  (oráculo de CI, no distribución). Igual en README.es.md si existe.
- **pyproject.toml**: NO se toca funcionalmente (CI lo usa). Solo si se
  quiere, un comment de "legado" en description — opcional, no romper.

## Alcance (una sola mitad coherente — NO A/B)

| # | Archivo | Cambio |
|---|---|---|
| 1 | `rust/crates/cortex-cli/src/main.rs` | paso 1 → aviso histórico + seguir nativo; paso 4 → error `No such command` rc 2; after_help actualizado; `init` → brazo nativo |
| 2 | `rust/crates/cortex-cli/src/fallback.rs` | eliminar o reducir a doc histórico (si muere su último uso) |
| 3 | `rust/crates/cortex-cli/src/memory_cmds.rs` | reindex real → fallo explícito documentado (--dry-run intacto) |
| 4 | `rust/crates/cortex-cli/src/commands/setup_cmd.rs` o `misc.rs` | `init` alias nativo (flags del oráculo main.py:796-806) |
| 5 | `rust/crates/cortex-cli/tests/*` | actualizar tests que dependían del passthrough (ver inventario) |
| 6 | `bench/parity/` | archivar goldens + README-archivo.md |
| 7 | `README.md` (+ `README.es.md` si existe) | instalación por binario; Python = legado |
| 8 | `rust/Cargo.lock`/`Cargo.toml` | NO TOCAR (cero deps) |
| 9 | `main.rs` root_command help | ajustar after_help texto |

## Tests a revisar/actualizar (referencian passthrough/CORTEX_BIN)

- `tests/passthrough.rs`, `tests/cli_dispatch.rs`,
  `tests/cli_memory_report.rs`, `tests/cli_webgraph_autopilot.rs`,
  `tests/cli_self_golden.rs`, `tests/t2_tail_native.rs`,
  `tests/t6b_session_watch.rs`, `tests/t_lea_a_ruta1.rs`,
  `tests/t_lea_b_ide.rs`, `tests/t_lea_b_docs.rs`,
  `tests/t_lea2_a_ruta2.rs`, `tests/t_lea2_b_hu.rs`,
  `tests/t_lea2_b_webgraph.rs` + los de ruta 1/2 restantes.
  Cada uno: si el test asumía passthrough (CORTEX_BIN=/bin/echo, rc 127 o
  rc 0 vía Python), actualizar al nuevo contrato (error nativo rc 2 /
  aviso histórico / fallo explícito). NO debilitar asserts: el nuevo
  contrato ES el comportamiento esperado post-baja.

## Verificación obligatoria

1. `cargo fmt --all --check` · `cargo clippy --workspace --all-targets -- -D warnings` · `cargo test --workspace` (¡todo el workspace, no solo cortex-cli!).
2. ARCHIVADO de goldens: ningún workflow de CI los referencia (verificado:
   `ci-gates.yml` corre pytest+cargo, no goldens). Verificar de nuevo tras
   el movimiento.
3. Suite Python COMPLETA bajo lock R3: **2552 passed, 21 skipped, 0F 0E**
   (la suite Python NO depende del binario nativo — correr para confirmar
   cero regresión).
4. Smoke manual: `cortex-cli bogus` → `No such command 'bogus'.` rc 2;
   `CORTEX_PY=1 cortex-cli session current` → aviso histórico + salida
   nativa; `cortex-cli reindex` (sin --dry-run) → fallo explícito;
   `cortex-cli init --non-interactive` → setup agent nativo.
5. `git mv` de goldens preserva historial.

## Git

BASE: `6612449`. Commits atómicos:
- `feat(obra07 baja fisica): passthrough eliminado — CORTEX_PY=1 histórico, catch-all 'No such command' rc2, reindex real fallo explicito P6/P9, init nativo alias setup agent` (+ tests actualizados)
- `chore(obra07 baja fisica): goldens archivados en bench/parity/archive + README historico`
- `docs(obra07 baja fisica): README instalacion por binario, wheel Python legado congelado`
`git add` SOLO tus archivos. NO tocar: `cortex/cli/**` (oráculo vivo),
`pyproject.toml` funcional, Cargo.toml/lock, `.github/`.

## Reporte

`.superpowers/sdd/PROMPT-BAJA-FISICA/task-1-report.md` — estado por ítem,
tests actualizados uno-por-uno (cuál y por qué), verificación exacta,
smokes, self-review, concerns. NO despaches subagentes.

## Definición de hecho

`main.rs` sin passthrough (CORTEX_PY=1 = aviso histórico; catch-all =
`No such command` rc 2), `fallback.rs` muerto, reindex real = fallo
explícito, init nativo, goldens en `bench/parity/archive/` con README,
README a binarios, workspace tests verdes, oráculo Python 2552/21/0/0,
CEROS passthrough a Python en el CLI nativo. Quedan SOLO para el dueño:
decisión de borrado físico de `cortex/`+`tests/`+`pyproject` (si algún día
se quiere) y release wheels solo-Rust (publicación, no repo).