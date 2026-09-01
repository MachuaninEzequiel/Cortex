# Obra 08 Stream B — Herdr Companion — Plan de Implementación

> **Para workers agénticos:** SKILL REQUERIDA: usar `superpowers:subagent-driven-development` (recomendado) o `superpowers:executing-plans` para implementar este plan tarea por tarea. Los pasos usan sintaxis de checkbox (`- [ ]`).
> **Spec:** `docs/transformacion/14-HERDR-COMPANION.md` (el plan argumenta desde la spec; ejecutores leen ambos).

**Goal:** Construir `cortex-companion` — un TUI mouse-first (ratatui) que reúne sesiones, acciones, búsqueda, menú de capacidades y el brain híbrido en una sola superficie — más el plugin de herdr que lo hace sticky en la terminal del dev.

**Architecture:** Crate nuevo `cortex-companion` que inyecta los servicios nativos del CLI in-process (patrón de cortex-tui, sin depender de él), máquina ELM-lite (state/action/effect), aprobación explícita para mutaciones con auditoría en `action_log`, brain como librería con enrutamiento de tools al engine (sin subprocess). Plugin declarativo herdr (`herdr-plugin.toml`) con pane overlay + acciones.

**Tech Stack:** Rust workspace, ratatui + crossterm (ya presentes), cortex-branding, cortex-app, cortex-actions, cortex-brain (lib). Cero deps nuevas.

**Spec:** `docs/transformacion/14-HERDR-COMPANION.md`

## Global Constraints

- **Cero deps nuevas:** workspace Cargo.lock append-only; ratatui/crossterm/serde ya existen (usar versiones del workspace).
- **NO tocar** `rust/crates/cortex-tui/` (WIP P8d vigente + snapshots gateados), ni `cortex-setup/src/ide/**`. El Companion duplica widgets mínimos.
- **`#![forbid(unsafe_code)]`** en todo el crate nuevo.
- **Paridad por construcción:** el engine usa los mismos servicios del CLI ⇒ salidas `--json` byte-idénticas (verificado por test contra el binario CLI).
- **Aprobaciones:** ninguna mutación sin aprobación explícita; cada ejecución audita en `.cortex/action_log` (mismo formato del runner de cortex-actions).
- **Fallo explícito (P6/P9):** lo no mapeado devuelve error con mensaje y sugerencia; nunca silencio, nunca subprocess.
- **Commits:** Conventional en español, `feat|fix|docs|chore(obra08 streamB ...)`.
- **herdr:** los pasos que involucran `herdr plugin ...` corren en la máquina del dueño (herdr 0.8.2 instalada); en CI solo se valida el manifest (TOML parseable + inventario).
- **Gate por commit:** cada task cierra su gate G-Bx referenciado.

---

### Task B1: Scaffolding del crate + Backend trait + InProcessBackend (G-B1)

**Files:**
- Create: `rust/crates/cortex-companion/Cargo.toml`, `rust/crates/cortex-companion/src/lib.rs`, `rust/crates/cortex-companion/src/engine.rs`, `rust/crates/cortex-companion/src/bin/companion.rs` (mínimo), `rust/crates/cortex-companion/tests/parity_cli.rs`
- Modify: `rust/Cargo.toml` (member nuevo, append-only)

**Interfaces:**
- Consumes: `cortex-app` (SessionService, búsqueda híbrida `cortex_app::context`), `cortex-actions` (registry/scheduler/runner), `cortex-config` (CortexConfig), `cortex-workspace` (WorkspaceLayout), `cortex-branding` (logo/banner). Firmas internas reales: explorarlas en Step 1 (buscar cómo cortex-cli/cortex-tui construyen los servicios y replicar ese patrón de construcción; NO depender de cortex-cli como lib si su lib es solo dispatch — confirmar).
- Produces:
  ```rust
  // lib.rs
  pub struct UiRequest { pub screen: Screen, pub project_root: PathBuf }
  pub enum Screen { Home, Menu, Sessions, Actions, Search, Brain }

  // engine.rs
  pub trait Backend: Send + Sync {
      fn session_current(&self) -> Result<Option<SessionSummary>, String>;
      fn session_list(&self) -> Result<Vec<SessionSummary>, String>;
      fn next_actions(&self) -> Result<Vec<ActionProposal>, String>;
      fn search(&self, query: &str, top_k: usize) -> Result<Vec<SearchHit>, String>;
      fn doctor(&self) -> Result<DoctorSummary, String>;
      fn stats(&self) -> Result<StatsSummary, String>;
      // -- mutaciones (siempre detrás de approval) --
      fn close_session(&self, session_id: &str) -> Result<(), String>;
      fn checkpoint_session(&self, note: &str) -> Result<(), String>;
      fn approve_action(&self, action_id: &str) -> Result<(), String>;
  }
  pub struct InProcessBackend { /* servicios construidos como los construye el CLI */ }
  impl InProcessBackend { pub fn open(project_root: &Path) -> Result<Self, String> }
  pub struct SessionSummary { pub id: String, pub status: String, pub mode: String, pub opened_at: String }
  pub struct ActionProposal { pub id: String, pub title: String, pub score: f64, pub cost: String, pub reversible: bool, pub effect: String }
  pub struct SearchHit { pub source: String, pub title: String, pub path: String, pub score: f64, pub snippet: String }
  pub struct DoctorSummary { pub ok: bool, pub checks: Vec<(String, String)> } // (name, ok|warn|fail)
  pub struct StatsSummary { pub episodic: usize, pub semantic: usize, pub vault_path: String }
  ```
  Nota: `Screen` también lo usa la app (B3). Los métodos mutantes se implementan con el patrón del runner de cortex-actions (que ya conoce approvals) o llamando a los servicios de sesión directamente — la aprobación vive en `approval.rs` (B2), NO dentro del backend.

- [ ] **Step 1: Explorar el patrón de construcción de servicios**

Run:
```bash
cd /home/chucho/Cortex
rg -n "SessionService::|fn open\(|CliSearchAdapter|ActionContext" rust/crates/cortex-cli/src/ | head -30
rg -n "pub fn" rust/crates/cortex-app/src/session/service.rs | head -20
rg -n "pub fn|pub struct" rust/crates/cortex-actions/src/registry.rs rust/crates/cortex-actions/src/scheduler.rs | head -30
```
Expected: identificar cómo `cortex-cli` (o `cortex-tui` en la inyección `UiRequest { service, search }`) construyen los servicios; replicar ESA construcción en `InProcessBackend::open`. Anotar en el commit qué se reusó.

- [ ] **Step 2: Escribir el test que falla (paridad con CLI)**

`rust/crates/cortex-companion/tests/parity_cli.rs`:
```rust
// Helper: ubicar el binario del CLI (env CORTEX_BIN override, o target/debug/cortex-cli
// construido con `cargo build -p cortex-cli` — documentar el comando en el test).
fn cli_bin() -> PathBuf { /* env CORTEX_BIN o CARGO_TARGET_DIR/debug/cortex-cli */ }

#[test]
fn engine_json_equals_cli_json() {
    // fixture project: usar el patrón de bench/parity/make_fixture_project.py (o un fixture
    // commiteado mínimo: config.yaml + vault/ con 2 notas + .cortex/sessions/ con 1 sesión)
    let fixture = fixture_project();                      // helper local (temp dir)
    let be = InProcessBackend::open(&fixture).unwrap();
    // session list
    let engine = be.session_list_json_for_test().unwrap();  // método #[cfg(test)] o helper pub
    let cli = Command::new(cli_bin()).args(["session","list","--json","--project-root",fixture_str]).output().unwrap();
    assert_eq!(engine, String::from_utf8(cli.stdout).unwrap().trim());
    // search (query "auth")
    let engine_s = be.search_json_for_test("auth", 5).unwrap();
    let cli_s = Command::new(cli_bin()).args(["search","auth","--json","--top-k","5","--project-root",fixture_str]).output().unwrap();
    assert_eq!(engine_s, String::from_utf8(cli_s.stdout).unwrap().trim());
    // next
    let engine_n = be.next_actions_json_for_test().unwrap();
    let cli_n = Command::new(cli_bin()).args(["next","--json","--project-root",fixture_str]).output().unwrap();
    assert_eq!(engine_n, String::from_utf8(cli_n.stdout).unwrap().trim());
}
```
(El helper `*_json_for_test` serializa con el MISMO pyjson/serializador que el CLI — explorar qué serializador usa cortex-cli (`pyjson.rs`) y reusarlo.)
Más un test de `Backend` trait: `session_current` en project sin sesión ⇒ `Ok(None)`.

- [ ] **Step 3: Correr y verificar que falla**

Run: `cargo test -p cortex-companion`
Expected: FAIL de compilación (crate no existe aún). Primero: `cargo metadata -q` para validar el member nuevo.

- [ ] **Step 4: Implementar**

- Agregar member a `rust/Cargo.toml` (append-only, comentario `# Obra 08 (stream B): docs/transformacion/14-HERDR-COMPANION.md`).
- Cargo.toml del crate: deps del workspace (ratatui, crossterm, serde, serde_json, serde_yaml, chrono) + cortex-branding, cortex-app, cortex-actions, cortex-config, cortex-workspace, cortex-brain. `[lib]` + `[[bin]] name = "cortex-companion"`.
- `lib.rs`: `Screen`, `UiRequest`, módulos `engine` (+ stubs de approval/app en B2/B3).
- `engine.rs`: trait + InProcessBackend con los 9 métodos (los 3 mutantes pueden devolver `Err("implementado en B2/B3 con approval")` temporalmente SOLO si el test de paridad no los toca — el test de paridad cubre session list/search/next).
- `bin/companion.rs`: parseo mínimo de `--project-root` + `InProcessBackend::open` + mensaje "Cortex Companion (obra08, WIP)"; salida stdout, rc 0.
- `#![forbid(unsafe_code)]` en lib.rs.

- [ ] **Step 5: Verificar verde + suite + clippy + fmt + RSS**

Run:
```bash
cargo build -p cortex-cli 2>/dev/null   # binario para el test de paridad
cargo test -p cortex-companion
cargo clippy -p cortex-companion -- -D warnings
cargo fmt --check
# medición RSS honesta (objetivo ~15-25 MB con servicios cargados):
cargo build -p cortex-companion
/tmp/rss.sh: ./target/debug/cortex-companion --project-root <fixture> &
# leer VmRSS de /proc/<pid>/status con los servicios construidos y reportar en el commit
```
Expected: tests PASS (paridad JSON byte-idéntica + session_current None); RSS documentado en el mensaje del commit.

- [ ] **Step 6: Commit**

```bash
git add rust/Cargo.toml rust/crates/cortex-companion
git commit -m "feat(obra08 streamB engine): scaffolding cortex-companion + Backend trait + InProcessBackend — paridad JSON con CLI en session list/search/next (G-B1); RSS <25MB medido"
```

---

### Task B2: Flujo de aprobación + auditoría (G-B3)

**Files:**
- Create: `rust/crates/cortex-companion/src/approval.rs`, `rust/crates/cortex-companion/tests/approval.rs`
- Modify: `rust/crates/cortex-companion/src/lib.rs` (módulo)

**Interfaces:**
- Consumes: `Backend::close_session/checkpoint_session/approve_action` (B1, mutantes), `ActionLog` del runner de cortex-actions (explorar `cortex-actions/src/runner.rs`/`store.rs` para reusar el mismo archivo/formato).
- Produces:
  ```rust
  pub struct ApprovalRequest { pub title: String, pub effect: String, pub audit_key: String }
  pub trait ApprovalUi: Send {
      fn ask(&mut self, req: &ApprovalRequest) -> bool;   // true = aprobado (clic)
  }
  // Ejecuta la mutación SOLO si la UI aprueba; audita siempre (aprobado/denegado) en action_log.
  pub fn run_guarded<F>(ui: &mut dyn ApprovalUi, log: &mut ActionLog,
                        req: &ApprovalRequest, f: F) -> Result<(), String>
      where F: FnOnce() -> Result<(), String>;
  ```
  Formato de auditoría: misma línea JSONL del runner existente (mirar `cortex-actions` store: `action_log.jsonl`), con campo `approved: bool` + `outcome: "executed"|"denied"|"failed"`.

- [ ] **Step 1: Escribir el test que falla**

```rust
struct RecorderUi { approved: bool, calls: usize }
impl ApprovalUi for RecorderUi { fn ask(&mut self, _: &ApprovalRequest) -> bool { self.calls += 1; self.approved } }

#[test]
fn denied_mutation_never_executes() {
    let mut ui = RecorderUi { approved: false, calls: 0 };
    let mut log = ActionLog::new(temp_file());
    let mut executed = false;
    let r = run_guarded(&mut ui, &mut log, &req("close-session","Cierra SES-x","sess.close"), || { executed = true; Ok(()) });
    assert!(r.is_ok());            // denegar NO es error: es decisión del usuario
    assert!(!executed);            // nunca ejecutó
    assert!(log.last_line().contains("\"approved\":false"));
    assert!(log.last_line().contains("\"outcome\":\"denied\""));
}

#[test]
fn approved_mutation_executes_and_audits() {
    let mut ui = RecorderUi { approved: true, calls: 0 };
    let mut log = ActionLog::new(temp_file());
    let mut executed = false;
    run_guarded(&mut ui, &mut log, &req("close-session","...","sess.close"), || { executed = true; Ok(()) }).unwrap();
    assert!(executed);
    assert!(log.last_line().contains("\"approved\":true"));
    assert!(log.last_line().contains("\"outcome\":\"executed\""));
}

#[test]
fn failure_is_audited_not_silent() {
    // mutación que falla ⇒ outcome "failed" + error propagado
}
```

- [ ] **Step 2: Correr y verificar que falla** — `cargo test -p cortex-companion approval` FAIL (módulo no existe).

- [ ] **Step 3: Implementar**

- `approval.rs`: `ApprovalRequest`, trait `ApprovalUi`, `run_guarded` (llama `ask`; si false ⇒ audita `denied` y devuelve Ok sin ejecutar; si true ⇒ ejecuta, audita `executed` o `failed` con el error). Reusar el formato/store de `cortex-actions` para action_log (explorar firmas reales en Step 1 y adaptar; si el store de cortex-actions es privado, escribir el append JSONL con el MISMO formato — test de formato contra una línea real del runner).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB approval): run_guarded — denegado nunca ejecuta, aprobado audita en action_log, fallo explícito (G-B3)"
```

---

### Task B3: App machine ELM-lite + input mouse-first (G-B2a)

**Files:**
- Create: `rust/crates/cortex-companion/src/app.rs`, `rust/crates/cortex-companion/tests/app_input.rs`
- Modify: `rust/crates/cortex-companion/src/lib.rs` (módulo), `bin/companion.rs` (loop de eventos mínimo)

**Interfaces:**
- Consumes: `Screen` (B1).
- Produces:
  ```rust
  // app.rs — máquina ELM-lite (replicar el patrón de cortex-tui/src/app/, SIN depender de él)
  pub enum AppAction {
      Navigate(Screen),
      Click { x: u16, y: u16 },        // hit-testing sobre áreas registradas
      Scroll { down: bool },
      Typed(char), Key(crossterm::event::KeyCode),
      Approve { audit_key: String },   // botón [Ejecutar] / [Aprobar]
      Deny { audit_key: String },
      RunCommand { family: &'static str, args: Vec<String> }, // Menu → engine
      Back, Quit,
  }
  pub struct AppState { pub screen: Screen, pub stack: Vec<Screen>, /* por pantalla: datos + áreas Rect */ }
  pub struct Effect { /* enum: none | open_search | execute_guarded { action, req, ui } | … */ }
  pub fn update(state: &mut AppState, action: AppAction) -> Option<Effect>;
  pub fn hit_test(state: &AppState, x: u16, y: u16) -> Option<AppAction>;  // puro: rects → acción
  // eventos crossterm → AppAction (mouse = input primario; teclado = accesibilidad):
  pub fn translate_event(ev: &crossterm::event::Event) -> Option<AppAction>;
  ```
- [ ] **Step 1: Escribir el test que falla**

```rust
// app_input.rs: inyectar eventos (sin terminal real)
#[test]
fn mouse_click_on_nav_screen_navigates() {
    let mut st = AppState::new(test_ui_request());
    // registrar el rect del botón "Sessions" en Home (área conocida)
    let action = hit_test(&st, HOME_SESSIONS_BTN.x, HOME_SESSIONS_BTN.y).unwrap();
    assert!(matches!(action, AppAction::Navigate(Screen::Sessions)));
    assert!(update(&mut st, action).is_none());
    assert_eq!(st.screen, Screen::Sessions);
}

#[test]
fn scroll_down_on_search_scrolls() {
    // translate_event(Event::Mouse(MouseEventKind::ScrollDown, ..)) => AppAction::Scroll{down:true}
}

#[test]
fn keyboard_esc_is_equivalent_to_back() {
    // translate_event(Key(KeyCode::Esc)) => AppAction::Back
}
```
(El test usa coordenadas de un layout fijo; el layout se define en B4 — en B3 el layout puede ser un stub determinista que el test comparte. Anotar: B4 ajusta si el layout real cambia las rects; los tests de B3 definen las rects canónicas del Home.)

- [ ] **Step 2: Correr y verificar que falla** — `cargo test -p cortex-companion app_input` FAIL.

- [ ] **Step 3: Implementar**

- `app.rs`: `AppAction`, `AppState` (screen + stack + áreas por pantalla), `update` (navegación, back, quit; delegar acciones de datos a effects), `hit_test` puro, `translate_event` (Mouse: Left click → Click, ScrollUp/Down → Scroll; Key: Esc → Back, q → Quit, chars → Typed; Enter → acción de foco actual si aplica — mapeo dual mouse/teclado).
- `bin/companion.rs`: loop `event::read()` → `translate_event` → `update` → efectos (v1: none/quitar), render mínimo "Pantalla: <name>" (el render real llega en B4).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB input): app machine ELM-lite + mouse-first (click/scroll) + dual teclado (G-B2a)"
```

---

### Task B4: Widgets + panel Home (G-B2b)

**Files:**
- Create: `rust/crates/cortex-companion/src/widgets.rs`, `rust/crates/cortex-companion/src/screens/home.rs`, `rust/crates/cortex-companion/tests/screens_snapshot.rs`
- Modify: `rust/crates/cortex-companion/src/lib.rs`, `bin/companion.rs` (render real)

**Interfaces:**
- Consumes: `AppState/AppAction` (B3), `Backend` (B1), `cortex-branding` (logo/wordmark).
- Produces:
  ```rust
  // widgets.rs — mínimo: Panel, Button (Rect + label + enabled), List (items + selected)
  pub struct Button { pub id: &'static str, pub rect: Rect, pub label: String, pub enabled: bool }
  pub fn button(app: &mut ratatui::Frame, b: &Button);   // estilos hover/active via borde
  pub struct Panel { pub title: String, pub rect: Rect }
  pub fn panel(app: &mut ratatui::Frame, p: &Panel, content: &str);
  // screens/home.rs
  pub struct HomeData { pub project: String, pub branch: Option<String>, pub session: Option<SessionSummary>,
                        pub top_action: Option<ActionProposal>, pub doctor: Option<DoctorSummary>,
                        pub stats: Option<StatsSummary> }
  pub fn home_areas(rect: Rect) -> HomeAreas;            // rects canónicas (compartidas con tests B3)
  pub fn render_home(app: &mut ratatui::Frame, area: Rect, data: &HomeData, brand: &BrandAssets, areas: &mut HomeAreas) -> AppRenderInfo;
  pub struct AppRenderInfo { pub buttons: Vec<Button>, pub spent_ms: f32 }
  ```
  Rendering: Home muestra proyecto, rama, sesión activa (o botón "Abrir sesión" → effect Navigate(Sessions)), próxima acción (o botón "Ver acciones"), doctor resumido (`[OK]`/`[FAIL]` con color), conteos de memoria. Presupuesto render <50 ms (medir en el test).
- [ ] **Step 1: Escribir el test que falla**

```rust
// screens_snapshot.rs — render a buffer sin terminal real (backend testTerminal de ratatui)
#[test]
fn home_renders_registered_buttons_and_budget() {
    let data = HomeData { project: "fixture".into(), branch: Some("main".into()),
                          session: None, top_action: Some(proposal("suggest_next_phase", 1.5)),
                          doctor: Some(DoctorSummary{ok:true, checks: vec![]}), stats: None };
    let (buf, info) = render_home_to_buffer(&data);      // helper: Frame sobre Buffer
    let text = buf_to_string(&buf);                       // helper: chars no vacíos
    assert!(text.contains("fixture"));
    assert!(text.contains("Abrir sesión"));               // botón presente cuando no hay sesión
    assert!(info.buttons.iter().any(|b| b.id == "open-session"));
    assert!(info.spent_ms < 50.0, "render {}ms superó presupuesto", info.spent_ms);
}
```
- [ ] **Step 2: Correr y verificar que falla** — FAIL (módulos no existen).

- [ ] **Step 3: Implementar** — widgets (panel/button/lista con estados hover vía `MouseCaptureKind`/focus simple), `home.rs` con las rects canónicas del test B3 (SI el layout real difiere de las rects del test B3, actualizar AMBOS en este commit y anotarlo), render en `bin/companion.rs` con el loop real de ratatui (crossterm backend, `enable_mouse_capture` — mouse es input primario).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS; presupuesto <50 ms.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB home): widgets (panel/button/list) + Home con sesión, top action, doctor-lite (G-B2b); render <50ms"
```

---

### Task B5: Menu — catálogo de capacidades (anti-olvido) (G-B2c)

**Files:**
- Create: `rust/crates/cortex-companion/src/menu.rs`, `rust/crates/cortex-companion/src/screens/menu_screen.rs`, `rust/crates/cortex-companion/tests/menu_catalog.rs`
- Modify: `lib.rs`, `app.rs` (efecto `RunCommand`)

**Interfaces:**
- Consumes: `Backend` (B1 — para ejecutar), `AppAction::RunCommand` (B3).
- Produces:
  ```rust
  // menu.rs — catálogo fijo y agrupado (spec §3, v1 = lista canónica, NO shell)
  pub struct CatalogEntry { pub family: &'static str, pub args: Vec<&'static str>,
                            pub title: &'static str, pub domain: Domain }
  pub enum Domain { Sessions, Memory, Search, Docs, Ci, Setup, Enterprise }
  pub fn catalog() -> Vec<CatalogEntry>;   // 27 familias reales del CLI agrupadas (spec §0: session, next, search, context, remember, forget, docs, ci, setup, ide, hu, pr-context, mcp-server, webgraph, autopilot, tutor, hint, doctor, org-config, promote-knowledge, review-knowledge, memory-report, install-skills, agent-guidelines, stats, reindex)
  // menu_screen.rs
  pub fn render_menu(app, area, selected: usize, entries: &[CatalogEntry], areas) -> AppRenderInfo;
  // Ejecución: AppAction::RunCommand { family, args } → effect que llama al Backend
  // (leer salida --json y mostrarla en un panel de salida dentro de la misma pantalla; mutaciones NO van por aquí)
  ```
  Regla: el Menu SOLO ejecuta lecturas (o dry-run); si la entrada es mutante (finish/checkpoint/remember), el click abre el flujo de aprobación (B2) — nunca ejecución directa.
  Clasificación de entradas (también del efecto):
  ```rust
  pub enum CommandEffect { Direct, Guarded }  // Guarded = mutante ⇒ run_guarded (B2)
  pub fn command_effect(e: &CatalogEntry) -> CommandEffect;
  // Direct: families de lectura conocidas (search, context, docs search, doctor, stats,
  //        memory-report, session list/current/show, next, org-config, webgraph export --dry-run…)
  // Guarded: session finish/close/checkpoint, remember, forget, ide remove, promote --apply,
  //          review-knowledge approve, docs restore/validate (si escribe)
  ```
- [ ] **Step 1: Escribir el test que falla**

```rust
#[test]
fn catalog_has_all_27_families_grouped() {
    let cat = catalog();
    let families: HashSet<_> = cat.iter().map(|e| e.family).collect();
    assert_eq!(families.len(), 27);
    assert!(families.contains("session") && families.contains("next") && families.contains("webgraph"));
    // agrupación: al menos una entrada por dominio
    for d in [Domain::Sessions, Domain::Memory, Domain::Search, Domain::Docs, Domain::Ci, Domain::Setup, Domain::Enterprise] {
        assert!(cat.iter().any(|e| e.domain == d), "dominio {d:?} vacío");
    }
}

#[test]
fn menu_entry_mutation_requires_approval_flow() {
    // entry args que contienen "finish" ⇒ el effect resultante es guarded (B2), no directo
    let e = CatalogEntry { family: "session", args: &["finish"], .. };
    let fx = command_effect(&e);
    assert!(matches!(fx, CommandEffect::Guarded{..}));
}
```
- [ ] **Step 2: Correr y verificar que falla** — FAIL.

- [ ] **Step 3: Implementar** — catálogo fijo (27 entradas reales del CLI con sus flags base), render del Menu con dominios agrupados + selección por click, efecto `RunCommand`: lecturas directas al backend (con su serializador pyjson) mostradas en panel de salida; mutantes → `run_guarded` (B2) con `ApprovalUi` del modal.

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB menu): catalogo 27 familias agrupadas + ejecucion con run_guarded en mutantes (G-B2c)"
```

---

### Task B6: Panels Sessions + Actions (aprobación por clic) (G-B3 UI)

**Files:**
- Create: `rust/crates/cortex-companion/src/screens/sessions_screen.rs`, `rust/crates/cortex-companion/src/screens/actions_screen.rs`, `rust/crates/cortex-companion/tests/approval_flow_ui.rs`
- Modify: `app.rs` (efectos), `lib.rs`

**Interfaces:**
- Consumes: `Backend::session_list/next_actions/close_session/approve_action` (B1), `run_guarded` (B2), widgets (B4).
- Produces:
  - `Sessions`: lista en vivo (filtro por status), click en fila → detalle (panel con checkpoints/tasks), botón [Cerrar sesión] → `run_guarded(close_session)`.
  - `Actions`: propuestas `next_actions` con score/costo/reversibilidad; click [Aprobar] por acción → `run_guarded(approve_action)`; botón [Aprobar lote auto-ok] (solo reversible+cost=instant) → aprobación en lote (cada una audita por separado).
- [ ] **Step 1: Escribir el test que falla**

```rust
// approval_flow_ui.rs — flujo completo con RecorderUi + FakeBackend (backend de test con contadores)
#[test]
fn click_approve_on_action_executes_and_audits() {
    let (mut st, fb) = setup_with(Actions, vec![proposal("p1",1.0,reversible=true)]);
    // simular click en el botón [Aprobar] de p1
    let act = hit_test(&st, ACTIONS_APPROVE_BTN.x, ACTIONS_APPROVE_BTN.y).unwrap();
    // el effect ejecuta run_guarded con ApprovalUi que aprueba
    let fx = update(&mut st, act).unwrap();
    apply_effect(fx, &mut fb);                       // helper de test
    assert_eq!(fb.approved_count, 1);
    assert!(fb.action_log_contains("p1", "approved:true"));
}

#[test]
fn click_deny_on_modal_never_executes() {
    // ApprovalUi = modal simulado denegando ⇒ fb.approved_count == 0, log denied
}

#[test]
fn batch_auto_ok_only_batchable_items() {
    // propuestas [reversible+instant, irreversible] ⇒ batch aprueba SOLO la primera
}
```
- [ ] **Step 2: Correr y verificar que falla** — FAIL.

- [ ] **Step 3: Implementar** — pantallas Sessions y Actions con los flujos de clic → modal de aprobación (widget modal: título + efecto + [Aprobar]/[Denegar]) → `run_guarded`. El modal muestra SIEMPRE el efecto exacto (spec §5).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB sessions-actions): paneles Sessions+Actions con aprobacion por clic y lote auto-ok (G-B3 UI); modal muestra efecto exacto"
```

---

### Task B7: Panel Search + feedback (G-B2d)

**Files:**
- Create: `rust/crates/cortex-companion/src/screens/search_screen.rs`, `rust/crates/cortex-companion/tests/search_screen.rs`
- Modify: `app.rs` (efecto open_search), `lib.rs`

**Interfaces:**
- Consumes: `Backend::search` (B1), widgets (B4).
- Produces: pantalla Search — input (teclado) + hits (click para abrir/selected), botón [Útil] por hit que persiste feedback en `.cortex/feedback.jsonl` (MISMO formato que la TUI actual / Action Engine — explorar `cortex-app/src/context/feedback.rs` o el formato que escribe `cortex tui` con `y`; reusar ese escritor).

- [ ] **Step 1: Escribir el test que falla**

```rust
#[test]
fn search_runs_hybrid_and_marks_useful() {
    let (mut st, fb) = setup_with(Search, vec![]);
    // Typed chars + Enter ⇒ effect Search{query}
    let fx = update(&mut st, AppAction::Typed('a')).unwrap();  // etc.
    // tras results: click [Útil] del hit 0 ⇒ feedback.jsonl contiene {hit, useful:true}
}
#[test]
fn empty_query_does_not_search() { /* sin query no hay llamada al backend */ }
```
- [ ] **Step 2: Correr y verificar que falla** — FAIL.

- [ ] **Step 3: Implementar** — input + resultados (misma pipeline híbrida vía backend, top-k default 5), feedback con formato del Action Engine (append JSONL, idempotente por hit).

- [ ] **Step 4: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB search): panel Search con feedback 'util' persistido en feedback.jsonl (G-B2d)"
```

---

### Task B8: Brain panel híbrido (G-B4)

**Files:**
- Create: `rust/crates/cortex-companion/src/brain_panel.rs`, `rust/crates/cortex-companion/tests/brain_panel.rs`
- Modify: `lib.rs`, `app.rs` (efectos del chat)

**Interfaces:**
- Consumes: `cortex-brain` como LIB (router, catálogo de tools, `LlmBackend`, `DeterministicBackend` y `ScriptedBackend` — explorar firmas reales en Step 1), `Backend` (B1), `run_guarded` (B2).
- Produces:
  ```rust
  // brain_panel.rs
  pub enum BrainMode { Deterministic, Llm }   // Llm = feature llama (compilación opcional)
  pub struct BrainPanel { pub messages: Vec<BrainMsg>, pub mode: BrainMode }
  pub enum BrainMsg { User(String), Brain(String), Proposal { command: String, audit_key: String } }
  // Enrutamiento de tools del brain → engine in-process (spec §2.2); mapa 1:1:
  pub fn route_brain_tool(name: &str, args: &serde_json::Value, be: &dyn Backend) -> Result<String, String>
  //   memory.search   → be.search(query, 5)
  //   session.current → be.session_current()
  //   actions.propose → be.next_actions()
  //   cortex.health   → be.doctor()
  //   vault.stats     → be.stats()
  //   docs.related    → be.search con filtro doc_type si el backend lo soporta; si no ⇒ Err explícito
  //   webgraph.serve  → Err explícito ("no mapeada en v1 — corré `cortex webgraph serve`")  [P6/P9]
  //   CUALQUIER otra  → Err explícito con el nombre
  // Las tools READ se ejecutan sin aprobación; una PROPUESTA de mutación del brain
  // (comando CLI sugerido) se muestra como BrainMsg::Proposal con botón [Ejecutar] → run_guarded.
  ```
- [ ] **Step 1: Explorar las firmas reales de cortex-brain**

Run:
```bash
rg -n "pub fn|pub enum|pub trait" rust/crates/cortex-brain/src/router.rs rust/crates/cortex-brain/src/chat.rs rust/crates/cortex-brain/src/tools.rs | head -40
```
Expected: identificar router (intento→Intent), catálogo de tools, `LlmBackend::generate` y los backends existentes; anotar en el commit cómo se reusan.

- [ ] **Step 2: Escribir el test que falla**

```rust
// brain_panel.rs (tests) — ScriptedBackend del brain como LLM falso + FakeBackend
#[test]
fn read_tool_executes_directly_no_approval() {
    // script: "TOOL: memory.search auth" → route_brain_tool → FakeBackend.search llamado,
    // run_guarded NUNCA invocado (sin modal)
}

#[test]
fn mutate_proposal_shows_execute_button_and_guards() {
    // brain propone comando mutador (p.ej. "cortex session checkpoint ...") ⇒ BrainMsg::Proposal
    // → click [Ejecutar] ⇒ run_guarded; deny ⇒ no ejecutó; approve ⇒ ejecutó + auditado
}

#[test]
fn unmapped_tool_fails_explicitly() {
    assert!(route_brain_tool("webgraph.serve", &json!({}), &fb).unwrap_err().contains("no mapeada"));
}

#[test]
fn deterministic_router_zero_tokens() {
    // DeterministicBackend responde sin modelo: "?session" ⇒ intent session, respuesta sin TOOL:
}
```
- [ ] **Step 3: Correr y verificar que falla** — FAIL.

- [ ] **Step 4: Implementar** — brain_panel con chat (mensajes, input, render), router+búsqueda de libreto del brain (reusar módulos de cortex-brain), enrutamiento `route_brain_tool`, propuestas con botón → run_guarded. Feature `llama` opcional heredada del brain (compilación default sin LLM).

- [ ] **Step 5: Verificar verde + suite + clippy + fmt**

Run: `cargo test -p cortex-companion && cargo clippy -p cortex-companion -- -D warnings && cargo fmt --check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add rust/crates/cortex-companion rust/Cargo.toml 2>/dev/null || git add rust/crates/cortex-companion
git commit -m "feat(obra08 streamB brain): panel Brain hibrido — reads directas, propuestas con [Ejecutar] guarded, tools no mapeadas fallo explicito (G-B4)"
```

---

### Task B9: Binario + plugin herdr + INSTALL.md (G-B5, G-B6a)

**Files:**
- Create: `integrations/herdr/herdr-plugin.toml`, `integrations/herdr/INSTALL.md`, `rust/crates/cortex-companion/tests/plugin_manifest.rs`
- Modify: `bin/companion.rs` (pulido del entrypoint: `--project-root`, defaults, no-TTY snapshot)

**Interfaces:**
- Consumes: binario `cortex-companion` completo (B1–B8).
- Produces: manifest EXACTO (spec 14 §4):
  ```toml
  id = "cortex.companion"
  name = "Cortex Companion"
  version = "0.1.0"
  min_herdr_version = "0.8.0"
  description = "Companion de Cortex: sesiones, acciones, búsqueda y brain en un pane"
  platforms = ["linux", "macos"]

  [[panes]]
  id = "companion"
  title = "Cortex"
  placement = "overlay"
  command = ["cortex-companion"]

  [[actions]]
  id = "open"
  title = "Open Cortex Companion"
  contexts = ["workspace"]
  command = ["herdr", "plugin", "pane", "open", "--plugin", "cortex.companion", "--entrypoint", "companion", "--placement", "overlay"]

  [[actions]]
  id = "next"
  title = "Cortex: next actions"
  contexts = ["workspace"]
  command = ["cortex", "next", "--json"]

  [[actions]]
  id = "status"
  title = "Cortex: session status"
  contexts = ["workspace"]
  command = ["cortex", "session", "current", "--json"]

  [[actions]]
  id = "doctor"
  title = "Cortex: doctor"
  contexts = ["workspace"]
  command = ["cortex", "doctor"]
  ```
  INSTALL.md: instalación herdr (`herdr plugin link <repo>/integrations/herdr` o `herdr plugin install herdrdev/cortex` cuando exista release), verificación (`herdr plugin list`, `herdr plugin action list --plugin cortex.companion`, `herdr plugin pane open ...`), uso standalone (`cortex-companion`), troubleshooting (pane sin mouse ⇒ `--placement split`), nota de seguridad (modelo de confianza: el plugin corre como el dev).
- [ ] **Step 1: Escribir el test que falla**

```rust
// plugin_manifest.rs — validación estructural en CI (sin herdr)
#[test]
fn manifest_parses_as_valid_toml_with_required_fields() {
    let toml: toml::Value = toml::from_str(include_str!("../../../integrations/herdr/herdr-plugin.toml")).unwrap();
    assert_eq!(toml["id"].as_str(), Some("cortex.companion"));
    for k in ["name","version","min_herdr_version"] { assert!(toml.get(k).is_some()); }
    assert!(toml["panes"].as_array().unwrap().iter().any(|p| p["id"].as_str() == Some("companion") && p["placement"].as_str() == Some("overlay")));
    assert!(toml["actions"].as_array().unwrap().len() >= 4);
}
```
(toml crate: ¿está en el workspace? si no, usar `serde_yaml` NO sirve — verificar `rg toml rust/Cargo.lock`; si no existe como dep del workspace, el test parsea con un mini-parser manual SOLO campos clave, o agregar `toml` dev-dep SI ya está en Cargo.lock vía otra dep — regla: cero paquetes NUEVOS en Cargo.lock.)

- [ ] **Step 2: Correr y verificar que falla** — FAIL (manifest no existe).

- [ ] **Step 3: Implementar** — crear manifest + INSTALL.md; entrypoint pulido (sin TTY ⇒ snapshot render, rc 0; default project_root = cwd, en herdr respetar el cwd del pane).

- [ ] **Step 4: Verificar en la máquina del dueño (herdr real)**

Run (en la máquina con herdr 0.8.2):
```bash
herdr plugin link /home/chucho/Cortex/integrations/herdr
herdr plugin list
herdr plugin action list --plugin cortex.companion
herdr plugin pane open --plugin cortex.companion --entrypoint companion --placement overlay
```
Expected: plugin listado; 4+ acciones; pane abre con el Companion (verificación manual del dueño: clics funcionan). Documentar el resultado en el commit.

- [ ] **Step 5: Commit**

```bash
git add integrations/herdr rust/crates/cortex-companion
git commit -m "feat(obra08 streamB herdr): plugin manifest + INSTALL.md + validacion estructural CI (G-B5); link/actions/pane verificados en herdr 0.8.2"
```

---

### Task B10: Gate final del stream B — suite + standalone + docs (G-B6b)

**Files:**
- Modify: `docs/transformacion/ESTADO-ACTUAL.md`, `docs/transformacion/HANDOFF.md`, `docs/transformacion/14-HERDR-COMPANION.md` (marcar resuelto)

**Interfaces:**
- Consumes: B1–B9.

- [ ] **Step 1: Suite completa**

Run: `cargo test --workspace 2>&1 | tail -3 && cargo clippy --workspace -- -D warnings && cargo fmt --check`
Expected: workspace verde (o solo WIP ajeno documentado); clippy/fmt limpios.

- [ ] **Step 2: Verificación standalone (sin herdr)**

Run en terminal normal (no-TTY y TTY):
```bash
./target/debug/cortex-companion --project-root /tmp/fixture 2>&1 | head -5   # no-TTY snapshot rc 0
# manual: correr en una terminal: navegación por clic si el terminal soporta mouse, Esc/q para salir
```
Expected: snapshot sin crash; navegación básica manual OK (documentar).

- [ ] **Step 3: Cold start N=20**

Correr el patrón del repo con el binario release: medir arranque a primer render (documentar mediana; objetivo: el pane overlay abre <100 ms a primer frame).

- [ ] **Step 4: Docs de cierre**

- ESTADO-ACTUAL.md: sección Obra 08 stream B (features, gates G-B1…G-B6 PASS, uso: `herdr plugin link` + pane; divergencias declaradas: widgets duplicados vs cortex-tui, deuda de reuso).
- HANDOFF.md: §7 update (estado stream B + fase 2 documentada: web hub, backend MCP/remoto P13, reuso widgets).
- 14-…: marcar `> Estado: RESUELTO por obra 08 stream B (2026-08-27)`.

- [ ] **Step 5: Commit**

```bash
git add docs/transformacion/ESTADO-ACTUAL.md docs/transformacion/HANDOFF.md docs/transformacion/14-HERDR-COMPANION.md
git commit -m "docs(obra08 streamB): cierre — suite verde, standalone OK, cold start medido, docs de cierre (G-B6b)"
```

---

## Self-Review (stream B)

- **Cobertura spec:** §2.1→B1, §2.2→B1 (+ nota enrutamiento en B8), §2.3→B8, §3→B4-B7, §4→B9, §5→B2/B3/B6/B9 (seguridad/errores), §6→gates B1-B10, §7→estimación, §8→riesgos mitigados en tasks, §9 fase 2→queda documentada en B10 (fuera de alcance), §10→intacto por constraint global.
- **Tipos consistentes:** `Screen` (B1) usado en app (B3) y pantallas (B4-B8); `Backend` (B1) consumido por menu (B5), sessions/actions (B6), search (B7), brain (B8); `run_guarded` (B2) usado en B5/B6/B8; `hit_test` (B3) usado en B4-B8. `AppAction::RunCommand{family,args}` (B3) consumido en B5.
- **Sin placeholders:** donde el plan dice "explorar firmas reales" hay comandos rg exactos y el criterio de adaptación; los contenidos de templates/manifest están especificados al nivel de contrato con el contenido clave inline.
- **Nota de ejecución:** B9 Step 4 (herdr real) corre en la máquina del dueño — si el subagente no tiene herdr en su entorno, marcar el paso como pendiente manual del dueño e informarlo; NO bloquear el resto del stream.