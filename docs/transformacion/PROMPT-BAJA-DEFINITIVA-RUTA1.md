# PROMPT BAJA DEFINITIVA — RUTA 1 (A/B en paralelo)

> **Paquete separado post-Obra 07** — wirear los leaves CLI de "solo alcance"
> (doc 12 §7 punto 6 / doc 09 §4 punto 8). La Obra 07 está CERRADA
> (T1–T7 ✅, oráculo **2552 passed, 21 skipped, 0 failed, 0 errors**,
> commit `02f6daf`). Este paquete NO toca: la decisión de archivo de
> Python/goldens (pendiente del dueño), webgraph serve/doctor, hu import,
> autopilot doctor/install/uninstall (fui design "de diseño", fuera de ruta 1).

## Contexto en 30 segundos

El `cortex-cli` nativo (Rust) ya wireó el grueso de sus subcomandos (T2-cola,
commit `7d988a7`+`16bb8b7`). Quedan 2 familias "solo alcance" sin wirear que
aún caen a `fallback::passthrough` (Python): **session task/hooks**, **ide**,
**docs validate/restore/list-backups/routing-table** y los comandos raíz
**remember/forget**. Este paquete los wirea con el patrón establecido
(glue in-process sobre crates nativos + gates byte-parity contra el CLI
Python REAL + cold start N=20).

**Estructura: DOS MITADES DISJUNTAS (A y B) para lanzar DOS agentes en
paralelo sobre el MISMO working tree.** Territorios de archivos 100%
disjuntos. El único archivo compartido que ambos necesitarían (`main.rs`
dispatch) se prepara en un **PASO 0 del coordinador** ANTES de lanzar;
después nadie lo toca.

## Inventario total (lo que se wirea entre A y B)

| Family | Subcomandos | Oráculo Python | Nativos existentes |
|---|---|---|---|
| `session task` | list, done, in-progress, skip, block | `cortex/cli/session.py:485-670` | `Task`/`TaskStatus` en `cortex-app::session` (mod.rs:86,152); falta `list_tasks`/`update_task_status` en SessionService → port |
| `session hooks` | list, install, uninstall, status | `cortex/cli/session.py:680-845` | `HookInstaller` COMPLETO en `cortex-setup::session_hooks` (install/uninstall/status/status_all/default_installer) → solo glue |
| `remember` / `forget` | raíz ×2 | `cortex/cli/main.py:1237-1290` y `1900-1915` | `NativeEpisodicStore::append` (cortex-app/episodic/mod.rs:271); falta `delete` → port |
| `ide` | list, setup, remove, status | `cortex/cli/ide.py` (376 líneas) | `cortex-setup::ide` (adapters/prompts/canonical_tools/IdeCtx) + `install_ide` ya portado en T2 (`setup_cmd.rs`); falta remove/status/list → glue+port |
| `docs` | validate, restore, list-backups, routing-table | `docs_migrate.py:93-160` + `docs_subcommand.py:78-110` | `migration::validate_vault` + `ValidatePayload::to_json` (cortex-services/src/migration.rs:290) y `create_backup` (:1082); falta `list_backups`/`restore_backup` (tar) → port; `semantic/routing.rs` tiene DOC_TYPE_ROUTING parcial → completar o fallo explícito |

---

# PASO 0 — SCAFFOLD DE DISPATCH (lo ejecuta el COORDINADOR, no los agentes)

Un único commit ANTES de lanzar A y B, para que ningún agente toque `main.rs`:

1. `rust/crates/cortex-cli/src/commands/ide_cmd.rs` NUEVO:
   ```rust
   //! stub ruta 1 — lo rellena la MITAD B (ide).
   pub fn run(_argv: &[String]) -> bool { false }
   ```
2. `rust/crates/cortex-cli/src/commands/remember_cmd.rs` NUEVO:
   ```rust
   //! stub ruta 1 — lo rellena la MITAD A (remember/forget).
   pub fn run_remember(_argv: &[String]) -> bool { false }
   pub fn run_forget(_argv: &[String]) -> bool { false }
   ```
3. `commands/mod.rs`: `pub mod ide_cmd; pub mod remember_cmd;`
4. `main.rs` — añadir 3 brazos al match de `dispatch_native`:
   ```rust
   "ide" => commands::ide_cmd::run(rest),
   "remember" => commands::remember_cmd::run_remember(rest),
   "forget" => commands::remember_cmd::run_forget(rest),
   ```
5. Verificar: `cargo check --workspace` ✅ + `cargo test -p cortex-cli` ✅
   (los stubs devuelven `false` ⇒ passthrough idéntico al actual, cero
   cambio de comportamiento).
6. Commit: `chore(obra07 baja ruta1): scaffold dispatch ide/remember/forget`

> Después de este commit, `main.rs` y `commands/mod.rs` quedan CONGELADOS:
> PROHIBIDO tocarlos a las mitades A y B.

---

# Reglas compartidas (las dos mitades)

- **R0**: al arrancar `pgrep -af "pytest|cargo|python"` → matar zombis.
- **R1**:
  ```bash
  export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
         NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=4
  ```
- **R2 verificación por niveles**: Nivel 1 (libre):
  `cargo fmt --all --check && cargo clippy -p cortex-cli --all-targets -- -D warnings && cargo test -p cortex-cli`.
  Nivel 2 (pre-commit): tu gate build/verify. Nivel 3 (suite Python completa
  `-p no:randomly`, esperada **2552 passed, 21 skipped, 0F 0E**): UNA vez por
  mitad, bajo lock R3. PROHIBIDO en iteración.
- **R3 lock**: `.cortex/heavy.lock` (mkdir loop sleep 30; trap rmdir).
  ⚠️ La OTRa mitad puede estar corriendo su N3: SI EL LOCK ESTÁ TOMADO,
  ESPERÁ (loop). Antes de entrar: `free -m` → available < 4000 ⇒ esperá 60 s.
- **R4**: `timeout 1200` en todo comando pesado. **R5**: un solo proceso
  pesado. **R6**: commit atómico prefijado
  `feat(obra07 baja ruta1 <mitad>): …` CON gate verde + registro inmediato.
  **R7**: `git add` SOLO tus archivos (el otro agente comparte el árbol).
- **Normalizaciones del gate** (las pactadas, sin añadir): `{{ROOT}}`,
  `{{TS}}`, `{{ELAPSED}}`, `{{RUN}}`, `{{MEMID}}`, `{{SHA}}`, scores 4
  decimales. Si un comando de tu mitad no tiene `--json` en el oráculo
  real, NO lo inventes: ≥2 casos observables reales (success/error o
  modos distintos).
- **PROHIBIDO**: `main.rs` y `commands/mod.rs` (post-paso 0),
  `cortex/cli/**` (oráculo vivo — jamás editar), `rust/Cargo.lock` y
  `cortex-cli/Cargo.toml` (cero deps nuevas esperadas: todo lo que
  necesitas ya está en las deps de T2/T6-b; SI descubrís que falta algo,
  PARÁ y avisá al coordinador — no lo agregues solo), `commands/autopilot.rs`,
  territorio de la otra mitad, P13/cortex-companion, `uv.lock`,
  `progress.md` raíz, `.p12b-*` y `rust/examples/`.
- **Gate propio**: cada mitad crea SU archivo de gate NUEVO
  (`bench/parity/cierre_leaves_a_golden.py` / `_b_golden.py`) con el patrón
  de `cierre_cli_golden.py` (build congela salida normalizada del CLI Python
  REAL; verify compara; checker Rust opcional). NO tocar
  `cierre_cli_golden.py` existente.
- **Registro propio**: cada mitad lleva SU progreso
  (`docs/transformacion/progreso-baja-a.md` / `progreso-baja-b.md`),
  patrón de `progreso-cierre.md`: precondiciones, RED→GREEN, salidas
  exactas, cold start N=20, auditoría del passthrough restante.
- **TDD estricto**: test Rust primero (RED contra el stub/passthrough),
  luego implementación mínima (GREEN), refactor. Servicios reales +
  fixtures en tmp. Prohibido asserts sobre mocks/grep de fuente.

---

# MITAD A — session task/hooks + remember/forget

**Respondable por un agente.** Estimación: ~11 subcomandos, 2 portes de
servicio chicos (tasks en SessionService, delete episódico).

## A.1 Session task ×5 — oráculo `session.py:485-670`

Contrato (ver oráculo para strings exactos):
- `list [--session-id] [--status pending|in-progress|done|skipped|blocked]
  [--project-root] [--json]` → rich table ID/STATUS/DESCRIPTION/FILES
  (DESCRIPTION truncada 60, FILES primeras 3 + "(+N)") o `(no tasks)`; JSON
  = `model_dump(mode="json")` de cada tarea.
- `done|in-progress|skip|block <task_id> [--note] [--session-id]
  [--project-root] [--json]` — skip/block tienen `--reason` OBLIGATORIO.
  JSON salida: `{"session_id", "task_id", "status"}`; texto: `{task_id} →
  {status}`. Errores (session no encontrada, task inválida) con `_error_exit`.

Porte nativo necesario (NUEVO en `cortex-app/src/session/service.rs`):
`list_tasks(&self, session_id, status: Option<TaskStatus>) -> Result<Vec<Task>, String>`
y `update_task_status(&self, session_id, task_id, status, note) ->
Result<Task, String>` — el MODELO ya existe (`Task`/`TaskStatus` y
`SessionRecord.tasks`). Referencia de contrato: `cortex.session.service`
Python y el trait `SessionsBackend` de `cortex-mcp/src/handlers_sessions.rs`
(semántica; NO copiar el impl de test `One`).

Archivos: `cortex-app/src/session/service.rs` (+ tests unit si aplica),
`cortex-cli/src/commands/session_cmd.rs` (brazos dentro de `run()`, TODO DISPONIBLE: session ya está dispatchado).

## A.2 Session hooks ×4 — oráculo `session.py:680-845`

Contrato: `list [--project-root] [--json]` → rich table IDE/INSTALLED
(✓/—)/SUPPORTED (✓/—)/DETAIL; JSON `[{ide, installed, supported, detail}]`.
`install <ide> [--project-root]`, `uninstall <ide> [--project-root]`,
`status <ide> [--project-root]` — ver strings exactos del oráculo.

Nativo: `cortex_setup::session_hooks::default_installer()` +
`install/uninstall/status/status_all` en `HookInstaller`. Puro glue.

## A.3 remember/forget — oráculo `main.py:1237-1290` y `1900-1915`

- `remember <content> [--type/-t general] [--tag …(repeat)] [--file …(repeat)]
  [--branch] [--repo] [--commit] [--summarize]` → usando el glue
  `NativeMemory` (patrón `pr-context store` de T2): `NativeEpisodicStore::append`.
  Salida: `Memory stored -> {id}` + `   type: {memory_type}` +
  `   summary: {content[:120]}` (truncar a 120 chars).
- `forget <memory_id>` → NUEVO port: `NativeEpisodicStore::delete(id) ->
  Result<bool, String>` (borrar entrada del JSONL episódico por `mem_*`).
  Salida: `Memory {id} deleted.` o error si no existe (string del oráculo).
  Referencia: `cortex/memory/episodic.py` (o donde viva `forget`).

Archivos: `cortex-app/src/episodic/mod.rs` (delete — SOLO añadir método,
no tocar otra cosa), `cortex-cli/src/commands/remember_cmd.rs` (llenar
stubs `run_remember`/`run_forget`), glue en `cortex-cli/src/memory.rs` si
necesario (añadir función buscadora de tienda episódica, no refactor).

## A.4 Gate de la mitad A

`bench/parity/cierre_leaves_a_golden.py` — ≥2 casos reales por subcomando
(texto + `--json` cuando exista). Casos mínimos:
session task list (texto+json, con/sin --status), done, in-progress, skip
(con --reason), block (con --reason), error de sesión; hooks list
(texto+json), install/uninstall/status sobre fixture tmp; remember
(texto, memoria real en tmp + {{MEMID}}), forget (ok + id inexistente).
Cold start N=20 por subcomando liviano (<100ms; ONNX solo si remember
indexa — medir honesto).

---

# MITAD B — ide + docs validate/restore/list-backups/routing-table

**Respondable por un agente.** Estimación: ~8 subcomandos, 2 portes de
servicio medianos (backups tar, routing) + glue ide.

## B.1 ide ×4 — oráculo `cortex/cli/ide.py` (376 líneas)

Contrato: `list [--project-root] [--json]` (collect_status → tabla
ADAPTER/PROJECT/STATUS), `setup <ide> [--project-root]` (run_setup:
install adapters + hooks, non-interactive), `remove <ide> [--project-root]`
(run_remove + uninstall hooks), `status <ide> [--project-root] [--json]`.
Strings de salida y errores EXACTOS del oráculo (`_fail`,
`Unknown IDE '<name>'.` etc.).

Nativo: `cortex_setup::ide` (adapters, prompts, IdeCtx — el patrón de
`install_ide` ya portado en `setup_cmd.rs` ronda 1/5 T2; replicar para
remove/status; `HookInstaller::uninstall/status` para el lado hooks).
Puedes ampliar `cortex-setup/src/ide/*` SOLO si falta un adapter/método
(y reportarlo); prioridad: glue en `ide_cmd.rs`.

## B.2 docs ×4 — oráculo `docs_migrate.py:93-160` + `docs_subcommand.py:78-110`

- `validate [--project-root] [--json]` → `migration::validate_vault` +
  `ValidatePayload::to_json` (YA NATIVO). Texto: formato `format_report`
  del oráculo (ver docs_migrate.py:106-120); JSON = payload.
- `restore <backup> [--target] [--project-root]` →
  NUEVO port en `cortex-services/src/migration.rs`:
  `list_backups(vault) -> Vec<PathBuf>` (leer `vault/.cortex/backups/*.tar.gz`)
  y `restore_backup(path, target) -> PathBuf` (extraer tar — patrón de
  `create_backup` :1082, que ya delega en `tar czf`; usar `tar xzf`).
  Oráculo: `cortex/services/migration.py` (o donde vivan
  `list_backups/restore_backup`). Strings: `Restored: {path}`;
  backup no encontrado = error del oráculo.
- `list-backups [--project-root] [--json]` → tabla/JSON de backups
  (orden y campos del oráculo).
- `routing-table [--doc-type] [--json]` → NUEVO: `semantic/routing.rs` tiene
  la tabla canónica; completar el `RouteSpec` serializable si falta
  (oráculo `cortex/documentation/routing.py`), o fallo explícito
  documentado (patrón P6/P9) para los campos no portados. `--doc-type`
  inválido → mensaje `Unknown doc_type: …` con la lista de válidos.

## B.3 Gate de la mitad B

`bench/parity/cierre_leaves_b_golden.py` — ≥2 casos reales por subcomando
(texto + `--json` cuando exista). Casos mínimos: docs validate
(texto+json, vault válido + vault con 1 doc inválido), restore
(backup real en tmp → `Restored: …` + error backup inexistente),
list-backups (texto+json con 0 y ≥1 backups), routing-table (texto+json,
`--doc-type adr` + doc_type inválido); ide list/status (texto+json sobre
fixture tmp), setup/remove (non-interactive, verificar hooks escritos en
`.cortex/`). Cold start N=20 por subcomando (<100ms).

---

# Matriz de territorio (NO PISAR)

| Archivo | Dueño |
|---|---|
| `rust/crates/cortex-cli/src/main.rs` | NADIE (paso 0, congelado) |
| `rust/crates/cortex-cli/src/commands/mod.rs` | NADIE (paso 0, congelado) |
| `rust/crates/cortex-cli/src/commands/ide_cmd.rs` | MITAD B |
| `rust/crates/cortex-cli/src/commands/remember_cmd.rs` | MITAD A |
| `rust/crates/cortex-cli/src/commands/session_cmd.rs` | MITAD A |
| `rust/crates/cortex-cli/src/commands/docs_cmd.rs` | MITAD B |
| `rust/crates/cortex-cli/src/memory.rs` | MITAD A (solo añadir, no refactor) |
| `rust/crates/cortex-app/src/session/service.rs` | MITAD A |
| `rust/crates/cortex-app/src/episodic/mod.rs` | MITAD A (solo método `delete`) |
| `rust/crates/cortex-services/src/migration.rs` | MITAD B |
| `rust/crates/cortex-app/src/semantic/routing.rs` | MITAD B |
| `rust/crates/cortex-setup/src/ide/*` | MITAD B (solo si falta, reportar) |
| `bench/parity/cierre_leaves_a_golden.py` | MITAD A |
| `bench/parity/cierre_leaves_b_golden.py` | MITAD B |
| `docs/transformacion/progreso-baja-a.md` | MITAD A |
| `docs/transformacion/progreso-baja-b.md` | MITAD B |
| `tests/` nuevo en cortex-cli | cada mitad SUS tests (nombres `t_lea_a_*.rs` / `t_lea_b_*.rs`) |

**Dependencias de desarrollo entre mitades: NINGUNA.** A no consume nada
de B y viceversa. Si `cargo check` falla por archivos de la OTRA mitad
(mid-edit), esperá y reintentá (regla del dual-stream); no arregles su
territorio salvo fix mecánico + anotación en su registro.

---

# Cierre del paquete (quien termine ÚLTIMO)

1. Verificar que ambos gates quedaron en verde (`cierre_leaves_a_golden`
   + `cierre_leaves_b_golden` build/verify).
2. Actualizar `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9.2
   (marcar ítems 1 resueltos totales) y `ESTADO-ACTUAL.md` (deuda residual
   reducida: quedan solo leaves "de diseño") — integrando AMBOS registros
   (progreso-baja-a.md + progreso-baja-b.md).
3. Anunciar **"BAJA DEFINITIVA — RUTA 1 COMPLETA"** con métricas:
   subcomandos wireados por mitad, cold start, estado del oráculo.
4. NO ejecutar la decisión de archivo/borrado de Python (pendiente del
   dueño) ni la ruta 2 (leaves de diseño: webgraph serve/doctor, hu
   import, autopilot doctor/install/uninstall).

## Definición de hecho de la ruta 1

session task ×5 + hooks ×4 + remember/forget (A) y ide ×4 + docs
validate/restore/list-backups/routing-table (B) NATIVOS con gates
byte-parity verdes + suite Python 100% verde (2552/21/0/0) + cold start
N=20 medido + registros actualizados. Passthrough restante = SOLO
leaves "de diseño" documentados. `CORTEX_PY=1` aún vigente hasta la
ruta 2 / decisión del dueño.