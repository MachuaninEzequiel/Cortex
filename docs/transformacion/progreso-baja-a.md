# Progreso MITAD A — BAJA DEFINITIVA RUTA 1 (session task/hooks + remember/forget)

> Registro de la MITAD A del paquete `docs/transformacion/PROMPT-BAJA-DEFINITIVA-RUTA1.md`
> (post-Obra 07). Estado del oráculo al arranque: **2552 passed, 21 skipped, 0F 0E**
> (commit `02f6daf`). La MITAD B corre en paralelo sobre el mismo árbol
> (territorios disjuntos; su registro: `progreso-baja-b.md`).
>
> Territorio A: `session_cmd.rs`, `remember_cmd.rs`, `memory.rs` (no requirió
> cambios), `cortex-app/src/session/service.rs`, `cortex-app/src/episodic/mod.rs`
> (solo método `delete`), gate `bench/parity/cierre_leaves_a_golden.py`,
> `docs/transformacion/progreso-baja-a.md`, tests `tests/t_lea_a_*`.
> PROHIBIDO: `main.rs`/`commands/mod.rs` (paso 0), `Cargo.toml`/`Cargo.lock`,
> `cortex/cli/**`, territorio B (`ide_cmd.rs`, `docs_cmd.rs`, `migration.rs`,
> `routing.rs`, `cortex-setup/src/ide/*`).

## Precondiciones de arranque

- ✅ Rama `feature/transformacion-2026-08`, HEAD `b529f35`
  (`chore(obra07 baja ruta1): scaffold dispatch ide/remember/forget …`).
- ✅ R0: `pgrep -af "pytest|cargo|python"` → sin zombis al arranque.
- ✅ Sin `.cortex/heavy.lock` huérfano; RAM disponible 8804 MB (≥4000).
- ✅ `cargo check --workspace` post-scaffold (paso 0 verificado por el coordinador).
- ✅ Oráculo Python corroborado al cierre de la Obra 07: 2552/21/0/0.

## Alcance cumplido (11 subcomandos)

| Familia | Subcomandos | Wire |
|---|---|---|
| `session task` | list, done, in-progress, skip, block | PORTE `SessionService::list_tasks`/`update_task_status` (modelo `Task`/`TaskStatus` ya existía) + brazos en `session_cmd.rs` (tabla rich-compatible byte-a-byte) |
| `session hooks` | list, install, uninstall, status | glue puro sobre `cortex_setup::session_hooks` (`default_installer` + `install/uninstall/status/status_all` — adapters P8e ya portados) |
| `remember` | raíz | `NativeMemory` + `NativeEpisodicStore::append` (id/timestamp/meta P12A-1) con embedder ONNX compartido con el oráculo; salida `Memory stored -> {id}` + `type:` + `summary:` (content[:120]) |
| `forget` | raíz | PORTE `NativeEpisodicStore::delete(id) -> Result<bool, String>` (borra la entrada del JSONL preservando el resto byte-idéntico); salida `Memory {id} deleted.` / mensaje del oráculo para id inexistente (stderr + rc 1) |

## TDD estricto — RED → GREEN

### RED (registrado 2026-08-26)

1. `cargo test -p cortex-app --no-run` → **33 errores de compilación**:
   `list_tasks` / `update_task_status` (service.rs) y `delete` (episodic) no
   existen (tests de los portes escritos primero; E0422/E0425/E0433/E0599).
2. `cargo test -p cortex-cli --test t_lea_a_ruta1` → **0 passed, 10 failed**:
   todos con `rc=127` / `cortex-cli: no pude ejecutar '/definitely/not/python-cortex'`
   — los comandos derivaban a `fallback::passthrough` (stubs del paso 0).

### GREEN (mismos tests)

- `cargo test -p cortex-app` → **105 passed, 0 failed** (100 previos + 5 nuevos:
  `session::service::task_tests` ×4 + episodico `delete` ×1).
- `cargo test -p cortex-cli --test t_lea_a_ruta1` → **10 passed, 0 failed**.
- Servicios reales + fixtures en tmp (`std::env::temp_dir()` + pid; sin mocks,
  sin grep de fuente): sesión YAML estilo Python con tasks T1/T1.2, JSONL
  episódico con ids fijos `mem_aaaa1111`/`mem_bbbb2222`, ONNX real para remember.

### Notas de portes (contrato exacto del oráculo)

- `update_task_status` replica `service.py`: sesión NO OPEN ⇒
  `Cannot update task in session with status 'closed'` (comillas simples);
  task inexistente ⇒ `Task id 'T99' not found in session '<sid>'`;
  DONE ⇒ `completed_at` automático (si faltaba); PENDING/IN_PROGRESS ⇒
  `completed_at = None`; nota no vacía se escribe.
- `list_tasks` devuelve las tasks de la sesión con filtro opcional por estado.
- `delete` reescribe el JSONL filtrando solo la fila borrada (el resto queda
  byte-idéntico; líneas ilegibles se preservan tal cual); Ok(false) si no existe.
- Tablas rich: port de `rich.table.Table` en consola no-TTY (ancho 80):
  `_calculate_column_widths` (medida natural + padding 2/col, `_extra_width` =
  bordes, `_collapse_widths` + `ratio_reduce` con `round()` half-even de
  CPython) + `Text.wrap(overflow="ellipsis")` (word-wrap, fold-off, truncate
  "…", justify left/center) + caja `┏┳┓/┃/┡╇┩/└┴┘` y separador pesado en la
  fila de headers. Validado byte-a-byte contra el rich REAL en los 3 shapes
  del gate (tabla tasks 1-fila, 3-filas, hooks con fold+ellipsis).
- `hooks install/uninstall/status --json`: objeto único (install/uninstall) o
  array (list/status) — `json.dumps(ensure_ascii=False)` con `, ` separators.
- IDE desconocido ⇒ `str(KeyError)` del oráculo: `"unknown IDE adapter
  'bogus'; available: claude-code, cursor, opencode, pi"` (comillas dobles
  externas) en stderr + rc 1.
- `forget` inexistente ⇒ stderr exacto del oráculo (`✗ Memory '<id>' not
  found.` + hint) + rc 1.

## Gate de la mitad A — `bench/parity/cierre_leaves_a_golden.py`

- Patrón de `cierre_cli_golden.py` (build congela el CLI Python REAL;
  verify compara el binario nativo post-normalización; `bench` mide cold start).
- Normalizaciones SOLO las pactadas: `{{ROOT}}`, `{{TS}}`, `{{ELAPSED}}`,
  `{{RUN}}`, `{{MEMID}}`, `{{SHA}}`, scores a 4 decimales.
- **27 casos reales** (≥2 por subcomando, texto + `--json` cuando el oráculo
  lo tiene): task list texto/json/filtros ×6, done/in-progress/skip/block
  texto+json, errores (status inválido, task inexistente, sesión inexistente);
  hooks list texto/json, install×2 (modos distintos), uninstall, status
  (individual + todos), errores de IDE desconocido; remember ×2 (type+files,
  type+branch), forget ok + inexistente.
- `build` → `bench/parity/.p12-cierre-leaves-a/goldens_leaves_a.txt` (160 líneas).
- `verify` → `[PASS] cierre_leaves_a byte-parity post-normalización (160 líneas)`
  / `✅ PARIDAD MITAD A — BAJA DEFINITIVA RUTA 1`.
- Iteración verificación renderer: divergencia detectada en el fold del
  `DETAIL` de hooks (fabrica `…` cuando fold=false) y en el separador pesado
  de headers (`┃` vs `│`) — corregido en el port, luego PASS.

## Cold start release N=20 (binario release, fixture del gate)

| Subcomando | avg | p95 | max | Nota |
|---|---|---|---|---|
| `session task list` | 3.6 ms | 4.6 ms | 5.0 ms | <100 ms ✅ |
| `session hooks list` | 2.4 ms | 2.8 ms | 3.1 ms | <100 ms ✅ |
| `remember` | 186.7 ms | 203.2 ms | 260.3 ms | ONNX (embedding + índice semántico) — medición honesta |
| `forget` | 117.4 ms | 125.7 ms | 127.9 ms | índice semántico del vault — medición honesta |

## Verificación obligatoria (ronda final)

1. `cargo fmt --all --check` → **limpio** (workspace completo; B formateó sus
   archivos en paralelo justo a tiempo).
2. `cargo clippy -p cortex-cli --all-targets -- -D warnings` → **limpio**.
3. `cargo test -p cortex-cli` → **todas las suites verdes** (incluye
   `t_lea_a_ruta1` ×10 y las suites previas T2/T6-b; también las de B en su
   estado actual).
4. `cargo test -p cortex-app` → 105 passed.
5. Gate `cierre_leaves_a_golden.py build|verify` → **verde** (160 líneas).
6. Suite Python completa UNA vez bajo lock `.cortex/heavy.lock` (R3, threads=2):
   `timeout 2400 .venv/bin/python -m pytest tests/unit tests/integration
   tests/e2e --no-cov --tb=no -p no:randomly` →
   **2552 passed, 21 skipped, 9 warnings in 126.37s** — 0F 0E. ✅

## Auditoría del passthrough restante (mitad A)

- `session task` ×5: NATIVO (was passthrough).
- `session hooks` ×4: NATIVO (was passthrough).
- `remember` / `forget`: NATIVOS (was passthrough).
- `session` corriente: 100% nativo (current/checkpoint/switch/diff/abandon/
  list/show/watch/tui ya wireados en T2/T6-b).
- Passthrough residual global post-ruta-1 = SOLO leaves "de diseño"
  documentados (webgraph serve/doctor, hu import, autopilot doctor/install/
  uninstall) + territorio B mientras cierra. `CORTEX_PY=1` sigue vigente
  hasta la ruta 2 / decisión del dueño.

## Riesgos residuales

- `pyjson::write_compact` emite `ensure_ascii=True`; el oráculo usa
  `ensure_ascii=False` para `task list --json` / `hooks --json`. Con
  contenido ASCII (fixtures del gate) es idéntico byte-a-byte; con contenido
  no-ASCII (tildes/emoji en descriptions o rutas) el nativo escaparía `\uXXXX`
  y Python no — divergencia documentada, fuera del territorio (pyjson no está
  en la matriz A).
- `session task list` con descripción >60 caracteres: nativo trunca a 60
  exactamente como el oráculo (`content[:60]` por chars).
- El `--json` de `task list` y `hooks` replica `json.dumps(…, ensure_
  ascii=False)` con los separadores `, ` / `: ` exactos.
- Errores de parseo de args (p.ej. `skip` sin `--reason`) quedan como
  self-golden (clap ≠ Typer por diseño) — no son casos del gate (igual que
  el precedente T2).