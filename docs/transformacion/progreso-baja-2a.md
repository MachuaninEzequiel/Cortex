# Progreso MITAD A — BAJA DEFINITIVA RUTA 2 (autopilot doctor + Fase 04)

> Registro de la MITAD A del paquete `docs/transformacion/PROMPT-BAJA-DEFINITIVA-RUTA2.md`
> (post-Obra 07 + RUTA 1 cerrada en `56f33a0`). La MITAD B (webgraph
> serve/doctor + hu import) corre en paralelo sobre el mismo árbol
> (territorios disjuntos; su registro: `progreso-baja-2b.md`).
>
> Territorio A: `commands/autopilot.rs` (AÑADIR doctor; retocar
> install/uninstall → rechazo nativo; NO refactor de start/preflight/
> checkpoint/finish/status de T3), tests `tests/t_lea2_a_ruta2.rs`,
> gate `bench/parity/cierre_leaves2_a_golden.py`,
> `docs/transformacion/progreso-baja-2a.md`.
> PROHIBIDO: `main.rs`/`commands/mod.rs` (congelados), `Cargo.toml`/
> `Cargo.lock` (cero deps nuevas — verificado: todos los crates usados ya
> eran deps de cortex-cli), `cortex/cli/**` (oráculo vivo), territorio B.

## Precondiciones de arranque

- ✅ Rama `feature/transformacion-2026-08`, HEAD `56f33a0` (cierre RUTA 1).
- ✅ R0: `pgrep -af "pytest|cargo|python"` → sin zombis al arranque.
- ✅ Sin `.cortex/heavy.lock`; RAM disponible 8873 MB (≥4000).
- ✅ `cargo check -p cortex-cli` verde pre-cambio (baseline).
- ✅ Oráculo corroborado (Fase 04): `autopilot doctor` =
  `cli.py` + `doctor.py` (6 checks); `install`/`uninstall` ELIMINADOS de
  `cli.py:352` — el oráculo responde "No such command 'install'." rc=2.

## Alcance cumplido

| Comando | Wire | Detalle |
|---|---|---|
| `autopilot doctor [--project-root] [--json]` | PORTE de `cortex.autopilot.doctor.run_diagnosis` sobre nativos | payload EXACTO `{project_root, ok, checks, warnings}`; 6 checks en orden: config (AutopilotConfig), sessions_dir (WorkspaceLayout + writable, self-heal mkdir como el oráculo), adapters (HookInstaller::list_available_adapters), hooks (HookInstaller::status_all), last_finish (SessionStorage::list_all), service (AutopilotService::from_project_root) |
| `autopilot install/uninstall` | RECHAZO NATIVO (Fase 04) | eliminados en Fase 04; el oráculo no los expone; el nativo los rechaza igual ("No such command 'install'." rc=2, sin ejecutar Python) |

## TDD estricto — RED → GREEN

### RED (2026-08-26)

`cargo test -p cortex-cli --test t_lea2_a_ruta2` → **1 passed, 8 failed**:
los 8 casos doctor/install/uninstall salían `rc=127`
(`cortex-cli: no pude ejecutar '/definitely/not/python-cortex'`) porque
caían en `AutopilotCmd::Other` ⇒ passthrough al CLI Python; el único que
pasaba era el test de regresión `unknown_autopilot_subcommand_still_passthrough`.
Sin mocks ni grep de fuente: servicios reales (SessionStorage nativo,
HookInstaller nativo, AutopilotService nativo) + fixtures tmp.

### GREEN (2026-08-26, mismo test)

- `cargo test -p cortex-cli --test t_lea2_a_ruta2` → **9 passed, 0 failed**.
- `cargo test -p cortex-cli` → **18 binarios de test, todos ok** (57 tests
  incl. los 9 nuevos; conteo de binarios = 18).
- `cargo fmt --all --check` ✅ · `cargo clippy -p cortex-cli --all-targets
  -- -D warnings` ✅ (0 warn).
- 0 deps nuevas: `cortex_workspace`, `cortex_app::session`, `cortex_setup::session_hooks`,
  `cortex_autopilot::{config, service}` ya eran deps de `cortex-cli`.

### Verificación oráculo→nativo byte-a-byte (fixtures reales, 2026-08-26)

- `autopilot doctor` texto + `--json` sobre fixture completo (sesión abierta
  vía `SessionService` de Python + hook claude-code instalado): **diff vacío**
  entre `python -m cortex.cli.main` y `cortex-cli`.
- `autopilot doctor` texto + `--json` sobre fixture degradado (sin sesiones
  ni hooks): **diff vacío**.
- `autopilot install/uninstall`: rc=2 ambos lados; core msg
  `No such command 'install'/'uninstall'.` presente en ambos (formato
  clap/typer distinto ⇒ equivalencia documentada, sin paridad byte-a-byte).

### Desviaciones del brief detectadas contra el oráculo REAL (documentadas)

1. **rc del doctor**: el brief pedía "rc 1 si ok=false", pero el oráculo de
   Fase 04 (`cli.py::doctor` → `_emit`) NO sale 1 ante checks fallidos:
   siempre rc=0. Se implementó paridad con el oráculo (rc=0) porque el gate
   es byte-parity contra el CLI Python REAL; documentado en el gate y acá.
2. **Fixture degradado "sin .cortex/sessions/"**: el check `sessions_dir`
   del oráculo hace `mkdir(parents=True, exist_ok=True)` ANTES de chequear
   writable — se auto-repara y queda OK. El fixture degradado que produce
   `ok: False` es el que NO tiene sesiones ni hooks instalados (check
   `hooks` → "No Cortex session hooks detected"). Se implementó la misma
   auto-reparación (side-effect parity verificada: tras el doctor, el
   `.cortex/sessions/` existe).
3. **Nombre del último check**: el oráculo lo llama `service`
   (doctor.py `_check_service_construction` → `DoctorCheck(name="service")`),
   no `service_construction` como sugería el brief. El payload EXACTO del
   oráculo manda (`"name": "service"`).
4. **Formato de salida texto del doctor (divergencia implícita)**: el
   brief pedía `[OK]/[FAIL] name: detail`; el oráculo real
   (`cli.py::_emit`, cli.py:65) emite líneas `key: value` planas sobre el
   payload (`project_root`, `ok`, `checks` con `str()` de Python,
   `warnings`). El nativo sigue al oráculo byte-a-byte (el gate así lo
   exige): las `[OK]/[FAIL]` nunca existieron en el CLI Python real.

### Fix round 1/5 (2026-08-27) — Finding A-I-1 + divergencia #4

El review aprobó la implementación con UNA finding Important:

- **`last_finish` tie-break**: el reduce usaba `>` (empate ⇒ gana el
  ÚLTIMO); el oráculo (`max(records, key=lambda r: r.opened_at)`) gana el
  PRIMERO. Fix de una línea: `>` → `>=` en `commands/autopilot.rs`
  (semántica primer-máximo documentada en el doc-comment de
  `check_last_finish`).
- **Test nuevo** `doctor_last_finish_tie_keeps_first_like_python_max`
  (dos archivos de sesión con idéntico `opened_at`; orden determinista por
  nombre de archivo en ambos lados ⇒ gana `aa-first`, no `bb-second`).
  RED-checkeado contra `>` (falla) → GREEN con `>=`.
- **Divergencia #4** documentada arriba (formato texto `key: value` del
  oráculo, no `[OK]/[FAIL]`).

## Gate — `bench/parity/cierre_leaves2_a_golden.py`

- 5 casos byte-parity (build congela el lado Python; verify compara el
  nativo normalizado): A01 doctor texto completo, A02 doctor --json
  completo, A03 doctor texto degradado (ok=False), A04 doctor --json
  degradado, A05 doctor texto con `--project-root` explícito desde cwd ajeno.
- 2 casos de equivalencia Fase 04 (sin paridad byte-a-byte, pactado):
  E01/E02 install/uninstall — rc y core msg comparados en vivo contra el
  oráculo (ambos rc=2, core msg presente, stdout vacío).
- **PASS build + verify** (115 líneas parity + 2 equivalencias).
- Cold start N=20 (release): `autopilot doctor` **avg=2.6ms p95=3.3ms
  max=3.5ms**.

## Suite Python (N3, una vez, bajo lock R3)

`timeout 2400 .venv/bin/python -m pytest tests/unit tests/integration tests/e2e
--no-cov --tb=no -p no:randomly` →
**2552 passed, 21 skipped, 9 warnings, 0F 0E** (124.37s). Lock
`.cortex/heavy.lock` adquirido y liberado (trap rmdir).

## Entregable

Commit atómico `feat(obra07 baja ruta2 A): …` con `git add` SOLO del
territorio A (ver matiz del paquete): `commands/autopilot.rs`,
`tests/t_lea2_a_ruta2.rs`, `bench/parity/cierre_leaves2_a_golden.py`,
`.superpowers/sdd/PROMPT-BAJA-DEFINITIVA-RUTA2/task-a-report.md`,
`docs/transformacion/progreso-baja-2a.md` + goldens `.p12-cierre-leaves2-a/`.