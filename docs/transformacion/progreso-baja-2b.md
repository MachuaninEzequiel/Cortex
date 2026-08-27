# Progreso MITAD B — BAJA DEFINITIVA RUTA 2 (webgraph serve/doctor + hu import)

> Registro de la MITAD B del paquete `docs/transformacion/PROMPT-BAJA-DEFINITIVA-RUTA2.md`
> (post-Obra 07 + RUTA 1 cerrada en `56f33a0`). La MITAD A (autopilot
> doctor + Fase 04) corre en paralelo sobre el mismo árbol (territorios
> disjuntos; su registro: `progreso-baja-2a.md`, commit `5ad44ab`).
>
> Territorio B: `commands/webgraph.rs` (AÑADIR serve/doctor; NO tocar
> export), `commands/hu_cmd.rs` (AÑADIR import; NO tocar list/show),
> `cortex-webgraph-server/src/server.rs` (helper `run_server` del wrapper —
> permitido por el brief: "posible ... solo si falta un helper del wrapper"),
> tests `tests/t_lea2_b_{webgraph,hu}.rs`,
> gate `bench/parity/cierre_leaves2_b_golden.py`,
> `docs/transformacion/progreso-baja-2b.md`.
> PROHIBIDO: `main.rs`/`commands/mod.rs` (congelados), `Cargo.toml`/
> `Cargo.lock` (cero deps nuevas — verificado: los crates usados ya eran
> deps de cortex-cli/cortex-webgraph-server), `cortex/cli/**` (oráculo
> vivo), territorio A, P13, `uv.lock`, `progress.md` raíz, `.p12b-*`,
> `rust/examples/`.

## Precondiciones de arranque

- ✅ Rama `feature/transformacion-2026-08`, HEAD `56f33a0` (cierre RUTA 1).
- ✅ R0: sin zombis al arranque.
- ✅ Sin `.cortex/heavy.lock`; RAM disponible ≥ 4000 MB.
- ✅ Oráculo corroborado: `hu import` → `cli/hu.py:15-26` +
  `workitems/service.py::_provider` (KeyError/RuntimeError); `webgraph
  doctor` → `cortex/webgraph/cli.py:120-171` (5 checks); `webgraph serve`
  → `cli.py:85-116` + `server.py::run_server` (bind + serve hasta
  Ctrl+C; `webbrowser.open`).

## Alcance cumplido

| Comando | Wire | Detalle |
|---|---|---|
| `webgraph doctor [--project-root]` | PORTE de cli.py:120-171 sobre WorkspaceLayout nativo | 5 checks en orden: project_root (existe), config_yaml (existe), vault_dir (existe), episodic_store (`.cortex/memory/chroma` existe), webgraph_dependencies (no-op documentado: server axum embebido; el oráculo chequea flask/flask-compress). Salida `[OK]/[FAIL] name: detail` + `WebGraph doctor passed.` / `WebGraph doctor found blocking issues...` (stderr) + rc 1. Byte-parity verificado |
| `webgraph serve [--project-root] [--host] [--port] [--no-open] [--workspace]` | Wrapper de `create_app` axum (P12B-2) + helper `run_server` en cortex-webgraph-server | root/layout via `WorkspaceLayout.discover`; config resolviendo host/port default; workspace federada opcional (default `.cortex/webgraph/workspace.yaml`); `--no-open` (open_browser = no-op documentado, precedente `webbrowser.open` sin lib nativa) |
| `hu import <external_id> [--provider jira] [--no-remember]` | GLUE sobre `WorkItemService::import_item` (workitems.rs:276) + providers desde config (`integrations.jira` enabled → JiraProvider nativo file://) | éxito → `Tracked item imported -> {path}`; errores canónicos byte-exactos: `Unknown work item provider: {provider}`, `Provider '{provider}' is not configured.` (ambos ya en nativo workitems.rs). Provider port de `jira.py`: ADF flatten + `_to_tracked_item` + kind map + `urllib.parse.quote`, fetch `file://` (gate hermético; http(s) sin cliente nativo, Cargo.toml congelado — error equivalente documentado) |

### Decisiones documentadas

- **`webgraph serve` NO es caso de terminal**: gate con smoke acotado
  (patrón P12B-2: puerto efímero, `GET /` → 200, kill). El bloque del
  gate registra SOLO el resultado del smoke (status=200 + killed), no los
  logs de arranque (Flask imprime banner/timestamps/ANSI no-portables).
- **`open_browser` = no-op documentado**: sin lib nativa de webbrowser;
  precedente del oráculo `webbrowser.open` (no se intenta abrir nada,
  costo UX mínimo, pactado en el preflight del paquete).
- **`webgraph_dependencies` no-op**: el server nativo es axum embebido;
  el oráculo verifica flask/flask-compress por importlib. En el venv del
  gate ambas están → `ok` en ambos lados (paridad se cumple).
- **`hu import` con jira HTTP(s)**: el nativo sólo lee `file://` (sin
  cliente HTTP; cero deps nuevas). El oráculo con base_url http haría
  REST real; divergencia del fetch documentada — el gate usa `file://`
  para hermetismo.
- **Errores de provider del oráculo = traceback rich no-portable**
  (KeyError/RuntimeError no capturados en hu.py) ⇒ equivalencias en el
  gate (rc + mensaje núcleo en vivo), NO paridad byte-a-byte (precedente
  S19 de RUTA 1 y E01/E02 de la MITAD A).

## TDD estricto — RED → GREEN

### RED (2026-08-27)

- `cargo test -p cortex-cli --test t_lea2_b_webgraph` → **0 passed; 5
  failed**: doctor×3 y serve×2 caían en `WebgraphCmd::Other` ⇒ passthrough
  con `CORTEX_BIN` inexistente ⇒ `rc=127` / connection refused (smoke).
- `cargo test -p cortex-cli --test t_lea2_b_hu` → **2 passed; 5 failed**:
  los 5 casos de import exitoso/proveedor fallan con
  `Unknown work item provider: jira` (providers vacíos ⇒ el servicio
  nunca podía importar); los 2 casos de error canónico ya pasaban.

### GREEN (2026-08-27)

- `t_lea2_b_webgraph`: **5/5** — doctor completa (todo OK, rc 0),
  degradada (FAIL rc 1 + stderr exacto), sin config (FAIL rc 1), serve
  smoke (GET / → 200) y serve sin config (rc 1 mensaje canónico).
- `t_lea2_b_hu`: **7/7** — éxito file:// (nota `HU-PROJ-1.md` canónica
  P8b), descripción markdown, `--no-remember`, error provider
  desconocido exacto, jira disabled (canónico), jira enabled sin
  credenciales (`Provider 'jira' is not configured.`), archivo faltante
  (`Jira connection failed: …`).
- `cargo test -p cortex-cli`: **todos los targets de test en verde** (19
  binarios de integración + unit + doc-tests — 20 líneas `test result: ok`,
  0 fallos; incluye `t_lea2_a_ruta2` de la MITAD A y los 12 nuevos
  `t_lea2_b_*`).
- `cargo build -p cortex-webgraph-server` + `cargo test
  -p cortex-webgraph-server`: ok (run_server helper no rompe nada).

## Verificación obligatoria

1. ✅ `cargo fmt --all --check`.
2. ✅ `cargo clippy -p cortex-cli -p cortex-webgraph-server --all-targets -- -D warnings`.
3. ✅ `cargo test -p cortex-cli` (+ `-p cortex-webgraph-server`): todo ok.
4. ✅ Gate propio: `cierre_leaves2_b_golden.py build` (5 casos byte-parity
   desde el CLI Python REAL, 1 smoke serve, 2 equivalencias) y `verify`
   ×3 → `[PASS] cierre_leaves2_b … + smoke serve + equivalencias` /
   `✅ PARIDAD MITAD B — BAJA DEFINITIVA RUTA 2`.
5. ✅ Suite Python UNA vez bajo lock R3:
   `timeout 2400 .venv/bin/python -m pytest tests/unit tests/integration tests/e2e --no-cov --tb=no -p no:randomly`
   → **2552 passed, 21 skipped, 0F 0E** (oráculo intacto; 9 warnings no
   relevantes).
6. ✅ Cold start N=20 (binario RELEASE, `cierre_leaves2_b_golden.py bench`):
   - `webgraph doctor` completa: `avg=2.0ms p95=2.4ms max=2.7ms`
   - `hu import` éxito: `avg=2.5ms p95=2.8ms max=2.8ms`
   - `webgraph serve` arranque (hasta GET / 200): `55ms`

## Commit

- `feat(obra07 baja ruta2 B): webgraph serve/doctor + hu import nativos — …`
  (único commit atómico; `git add` SOLO territorio B).

## Concern / pendiente del cierre (lo resuelve quien termina ÚLTIMO)

- Falta el anuncio "BAJA DEFINITIVA — RUTA 2 COMPLETA" + actualización de
  `12-AUDITORIA-PYTHON-RESIDUAL.md` §9.5, `ESTADO-ACTUAL.md` y
  `HANDOFF.md` §7 integrando AMBOS registros (A+B) cuando ambas mitades
  estén en verde.
- La decisión de archivo/borrado de Python/goldens sigue siendo del dueño
  (NO ejecutar).