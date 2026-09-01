# PROMPT BAJA DEFINITIVA — RUTA 2 (A/B en paralelo)

> **Paquete separado post-RUTA 1** — wirear los leaves CLI de "diseño"
> restantes (doc 12 §7 punto 6 / §9.5). RUTA 1 COMPLETA (commit `56f33a0`,
> gates `cierre_leaves_a/b_golden` 33+26 casos, oráculo 2552/21/0/0). Este
> paquete NO toca la decisión de archivo/borrado de Python ni goldens
> (pendiente del dueño).

## Contexto en 30 segundos

RUTA 1 dejó el passthrough de `cortex-cli` reducido a `CORTEX_PY=1` +
SOLO leaves de diseño: **`hu import`**, **`webgraph serve/doctor`**,
**`autopilot doctor/install/uninstall`**. Verificado contra el oráculo real:

- `autopilot install/uninstall` **fueron ELIMINADOS del oráculo en Fase 04**
  (`cortex/autopilot/cli.py:352` — "Removed in Fase 04 cleanup. Use
  `cortex session hooks install/uninstall --ide <name>`"). NO hay que
  wirearlos: solo verificar que el nativo los rechaza con el mismo
  comportamiento que el CLI Python real (comando desconocido) y documentar.
- `hu import` → nativo `WorkItemService::import_item` YA EXISTE
  (`cortex-app/src/workitems.rs:276`) — solo glue CLI.
- `webgraph serve` → router axum nativo `create_app` YA EXISTE
  (`cortex-webgraph-server/src/server.rs`, gate P12B-2) — solo wrapper
  `run_server` + glue CLI.
- `webgraph doctor` → 5 checks (project_root, config_yaml, vault_dir,
  episodic_store, webgraph_dependencies) sobre layout nativo — glue.
- `autopilot doctor` → port de `run_diagnosis` (6 checks: config,
  sessions_dir, adapters, hooks, last_finish, service_construction)
  sobre nativos (WorkspaceLayout, SessionStorage, HookInstaller,
  AutopilotService) — port pequeño.

**Estructura: DOS MITADES DISJUNTAS (A/B), territorios de archivos 100%
disjuntos. `main.rs`/`commands/mod.rs` ya fueron preparados por el scaffold
de RUTA 1 (brazos `ide`/`remember`/`forget`); `autopilot` y `webgraph` y
`hu` YA están dispatchados. Reflexión: NO se toca main.rs en esta ruta.**

## Inventario total

| Family | Subcomandos | Oráculo | Nativo existente | Tipo |
|---|---|---|---|---|
| `autopilot doctor` | 1 | `cortex/autopilot/cli.py:327-349` + `doctor.py` | checks sobre WorkspaceLayout/SessionStorage/HookInstaller/AutopilotService | port pequeño |
| `autopilot install/uninstall` | 0 (eliminados Fase 04) | — | verificación de rechazo | verificar + documentar |
| `webgraph serve` | 1 | `cortex/webgraph/cli.py:85-116` | `create_app` axum + `server_endpoint` | wrapper + glue |
| `webgraph doctor` | 1 | `cortex/webgraph/cli.py:120-171` + `setup.py` | WorkspaceLayout nativo | glue |
| `hu import` | 1 | `cortex/cli/hu.py:15-26` | `WorkItemService::import_item` (workitems.rs:276) | glue puro |

---

# Reglas compartidas (las dos mitades)

- **R0**: `pgrep -af "pytest|cargo|python"` → matar zombis.
- **R1**: `export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2 CARGO_BUILD_JOBS=4`
- **R2 niveles**: N1 libre: `cargo fmt --all --check && cargo clippy -p
  cortex-cli --all-targets -- -D warnings && cargo test -p cortex-cli` (+
  crates que toques). N2 pre-commit: tu gate build/verify. N3 suite Python
  completa UNA vez por mitad bajo lock R3 (esperada 2552/21/0/0).
- **R3 lock**: `.cortex/heavy.lock` (mkdir loop sleep 30; trap rmdir). Si la
  OTRA mitad lo tiene, esperá. `free -m` available < 4000 ⇒ esperá 60 s.
- **R4** `timeout 1200`. **R5** un proceso pesado. **R6** commit prefijado
  `feat(obra07 baja ruta2 <mitad>): …` con gate verde + registro inmediato.
  **R7** `git add` SOLO tus archivos.
- **Normalizaciones gate** (las pactadas, sin añadir): `{{ROOT}}`, `{{TS}}`,
  `{{ELAPSED}}`, `{{RUN}}`, `{{MEMID}}`, `{{SHA}}`, scores 4 decimales.
  Si el oráculo no tiene `--json`, NO lo inventes: ≥2 casos reales
  (success/error/modos).
- **PROHIBIDO**: `main.rs`, `commands/mod.rs`, `cortex/cli/**` (oráculo
  vivo), `rust/Cargo.lock`/`cortex-cli/Cargo.toml` (cero deps nuevas
  esperadas; si falta algo PARÁ y avisá), `commands/autopilot.rs` de la
  MITAD A... NO — el autopilot.rs es de MITAD A, pero NO el de RUTA 1 T3
  (start/preflight/checkpoint/finish/status ya nativos — NO refactorizarlos,
  solo AÑADIR doctor). territorio de la otra mitad, P13, `uv.lock`,
  `progress.md` raíz, `.p12b-*`, `rust/examples/`.
- **Gate propio**: cada mitad crea SU gate NUEVO
  (`bench/parity/cierre_leaves2_a_golden.py` / `_b_golden.py`), patrón de
  `cierre_cli_golden.py`. El server webgraph NO es un caso de terminal:
  gatearlo con el patrón P12B-2 existente (levantar server, request
  acotada, apagar) o con un smoke acotado.
- **Registro propio**: `docs/transformacion/progreso-baja-2a.md` /
  `progreso-baja-2b.md`.
- **TDD estricto**: test Rust primero (RED contra passthrough/stub),
  implementación mínima (GREEN), refactor. Servicios reales + fixtures
  tmp. Prohibido asserts sobre mocks/grep.

---

# MITAD A — autopilot doctor (+ verificación install/uninstall)

## A.1 `autopilot doctor [--project-root] [--json]` — oráculo cli.py:327-349 + doctor.py

Port del payload EXACTO:
```
project_root (str absoluto), ok (bool), checks: [{name, ok, detail, action}],
warnings: [detail de los checks no-ok]
```
6 checks de `run_diagnosis` (en orden):
1. `config` — AutopilotConfig parsea sin error (→ `cortex_config` o
   `cortex_app::config`; ver oráculo doctor.py:49-64).
2. `sessions_dir` — `.cortex/sessions/` existe y es writable
   (SessionStorage/layout nativo).
3. `adapters` — registry devuelve sus nombres conocidos (HookInstaller
   `list_supported`/`list_available_adapters`).
4. `hooks` — `Installed adapters: {installed}` (HookInstaller status_all,
   nombres instalados).
5. `last_finish` — último SessionRecord en estado sensible
   (SessionStorage list + status).
6. `service_construction` — AutopilotService se construye (autopilot
   nativo T3).
Salida texto: `[OK]/{name}: {detail}` o `[FAIL] ...` con colores rich →
nativo con ANSI como el oráculo (ver `_emit` del oráculo y el precedente
T3 para el formato). Error: rc 1 si `ok=false` (ver oráculo). JSON con
`_emit(payload, json_mode)` — orden de claves del oráculo.

## A.2 `autopilot install/uninstall` — verificación de rechazo (Fase 04)

NO wirear nada nuevo. Verificar que el CLI nativo y el CLI Python REAL
responden igual ante `cortex autopilot install` / `cortex autopilot
uninstall` (comando desconocido / subapp sin ese subcomando). Si el nativo
hoy los manda a passthrough (autopilot.rs:6 "doctor, install y uninstall
caen al passthrough"), corregir para que sea un fallo/rechazo equivalente
al del oráculo (NO ejecutar Python). Documentar en registro: "eliminados en
Fase 04; el oráculo no los expone; el nativo los rechaza igual".

## A.3 Gate de la mitad A

`bench/parity/cierre_leaves2_a_golden.py` — casos:
- `autopilot doctor` texto + `--json` sobre fixture tmp completo
  (proyecto con layout + sesiones + hooks instalados → todos OK).
- `autopilot doctor` sobre fixture degradado (sin `.cortex/sessions/` →
  FAIL con rc 1).
- `autopilot doctor` texto con `--project-root` explícito.
- `autopilot install` / `uninstall` — rechazo nativo == rechazo Python
  (comparar rc y mensaje; si el oráculo no expone el subcomando, el caso
  documenta el comportamiento equivalente sin paridad byte-a-byte).
Cold start N=20.

## Territorio A

`rust/crates/cortex-cli/src/commands/autopilot.rs` (AÑADIR doctor,
retocar install/uninstall → rechazo; NO refactorizar start/preflight/
checkpoint/finish/status existentes), posible `cortex-autopilot/src/` solo
si falta un helper de diagnosis (reportar), tests `t_lea2_a_*.rs`, gate A,
`progreso-baja-2a.md`.

---

# MITAD B — webgraph serve/doctor + hu import

## B.1 `webgraph serve [--project-root] [--host] [--port] [--no-open] [--workspace]`

— oráculo cli.py:85-116

Wrapper sobre el `create_app` axum nativo (P12B-2) + `server_endpoint`:
1. Resolver root/layout (`WorkspaceLayout.discover`).
2. Cargar config, construir `create_app(...)` (firma del server.rs).
3. `run_server` = bind + serve hasta Ctrl+C (mismo host/port/`
  no-open`/`workspace` del oráculo; el `open_browser` puede ser no-op
  documentado si no hay lib nativa de abrir navegador — ver oráculo
  `webbrowser.open` y decidir con fallo explícito/no-op documentado).
Gate: **no es caso de terminal** — patrón P12B-2 (levantar en puerto
efímero, request acotada `GET /` o health, apagar) o smoke en tests Rust
con `tokio`/`tower`. El gate del server ya existe (webgraph_golden_p12b):
NO duplicarlo, solo el wrapper CLI.

## B.2 `webgraph doctor [--project-root]` — oráculo cli.py:120-171

5 checks (en orden): project_root, config_yaml, vault_dir, episodic_store
(¿existe `.cortex/.../chroma`?), webgraph_dependencies (setup nativo o
no-op si no hay deps externas). Salida: `[OK] name: detail` (verde) /
`[FAIL] name: detail` (rojo, stderr) + `WebGraph doctor passed.` (verde) o
`WebGraph doctor found blocking issues. Fix the failing checks and retry.`
(rojo, err) + rc 1.

## B.3 `hu import <external_id> [--provider jira] [--no-remember]`

— oráculo hu.py:15-26

Glue puro: `WorkItemService::import_item(external_id, provider, remember,
now)` (firma workitems.rs:276) → `Tracked item imported -> {path}`.
Errores exactos del oráculo: `Unknown work item provider: {provider}` y
`Provider '{provider}' is not configured.` (ya en el nativo, verificar
byte-a-byte). El gate T1 ya cubre workitems MCP — acá solo el CLI.

## B.4 Gate de la mitad B

`bench/parity/cierre_leaves2_b_golden.py`:
- `webgraph serve` — arranque + request acotada (smoke; ver patrón
  P12B-2) o test Rust con server nativo; documentar como caso especial.
- `webgraph doctor` — fixture completo (todo OK → passed) + fixture
  degradado (sin vault → FAIL rc 1).
- `hu import` — import exitoso (texto, fixture tmp con provider jira
  fake/configurado), error provider desconocido, `--no-remember`,
  `--json`? (solo si el oráculo lo tiene).
Cold start N=20 por comando terminable.

## Territorio B

`rust/crates/cortex-cli/src/commands/webgraph.rs` (AÑADIR serve/doctor;
NO tocar export existente), `rust/crates/cortex-cli/src/commands/hu_cmd.rs`
(AÑADIR import; NO tocar list/show), posible `cortex-webgraph-server/`
solo si falta un helper del wrapper (reportar), tests `t_lea2_b_*.rs`,
gate B, `progreso-baja-2b.md`.

---

# Matriz de territorio (NO PISAR)

| Archivo | Dueño |
|---|---|
| `rust/crates/cortex-cli/src/main.rs` | NADIE (congelado) |
| `rust/crates/cortex-cli/src/commands/mod.rs` | NADIE (congelado) |
| `rust/crates/cortex-cli/src/commands/autopilot.rs` | MITAD A (solo añadir doctor; retocar install/uninstall) |
| `rust/crates/cortex-cli/src/commands/webgraph.rs` | MITAD B (solo añadir serve/doctor) |
| `rust/crates/cortex-cli/src/commands/hu_cmd.rs` | MITAD B (solo añadir import) |
| `rust/crates/cortex-autopilot/src/*` | MITAD A (solo si falta helper, reportar) |
| `rust/crates/cortex-webgraph-server/src/*` | MITAD B (solo si falta helper, reportar) |
| `rust/crates/cortex-cli/tests/t_lea2_a_*.rs` | MITAD A |
| `rust/crates/cortex-cli/tests/t_lea2_b_*.rs` | MITAD B |
| `bench/parity/cierre_leaves2_a_golden.py` | MITAD A |
| `bench/parity/cierre_leaves2_b_golden.py` | MITAD B |
| `docs/transformacion/progreso-baja-2a.md` | MITAD A |
| `docs/transformacion/progreso-baja-2b.md` | MITAD B |

**Dependencias de desarrollo entre mitades: NINGUNA.** Si `cargo check`
falla por archivos de la OTRA mitad (mid-edit), esperá y reintentá; no
arregles su territorio salvo fix mecánico + anotación en su registro.

---

# Cierre del paquete (quien termine ÚLTIMO)

1. Gates A+B en verde (`cierre_leaves2_a_golden` + `_b_golden`).
2. Actualizar `docs/transformacion/12-AUDITORIA-PYTHON-RESIDUAL.md` §9.5
   (marcar ruta 2 resuelta: passthrough restante = CORTEX_PY=1 SOLO) y
   `ESTADO-ACTUAL.md` + `HANDOFF.md` §7, integrando AMBOS registros.
3. Anunciar **"BAJA DEFINITIVA — RUTA 2 COMPLETA"** con métricas.
4. NO ejecutar la decisión de archivo/borrado de Python/goldens (dueño).

## Definición de hecho de la ruta 2

`autopilot doctor` (A), `webgraph serve/doctor` + `hu import` (B) NATIVOS
con gates byte-parity verdes + `autopilot install/uninstall` verificados
como rechazo equivalente al oráculo (Fase 04) + suite Python 100% verde
(2552/21/0/0) + cold start N=20 medido + registros actualizados.
Passthrough de `cortex-cli` = SOLO rollback `CORTEX_PY=1`.