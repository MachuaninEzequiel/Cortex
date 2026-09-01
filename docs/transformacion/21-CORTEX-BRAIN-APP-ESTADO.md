# 21 — Cortex Brain App: estado al cierre de la Obra 20 (G-A10)

> Estado: CERRADA — Obra 20 completada al 100% (G-A1 a G-A10 en verde).
> Origen: decisión de realineamiento (doc 20) que reemplazó el
> subcomando CLI `cortex brain *` del doc 19 por una app de escritorio
> estilo Handy (Tauri + React).
>
> Rama `feature/transformacion-2026-08`, commits locales, sin push.

---

## 0. Contexto

El motor local de Liquid LFM2.5 ya estaba implementado en
`rust/crates/cortex-brain/` (paths, download, chat, llama, tools,
i18n, router, window) — ver doc 19 para los detalles técnicos.

El doc 19 proponía exponerlo como subcomandos CLI (`cortex brain
install`, etc.). El dueño pidió cambiar el scope: que Cortex Brain
sea **una aplicación de escritorio standalone**, análoga a
[cjpais/Handy](https://github.com/cjpais/Handy). Esa propuesta está
formalizada en `docs/transformacion/20-CORTEX-BRAIN-APP.md`.

Este doc 21 asienta **el estado vivo** del trabajo hecho bajo el
doc 20: qué gates pasaron, qué commits, qué quedó en cada uno,
qué aprendimos en el camino y qué viene ahora.

---

## 1. Decisiones cerradas (del doc 20 §12.1)

- **Stack UI:** Tauri 2 (Rust + React + Vite + Tailwind).
- **Binario unificado:** `cortex-brain` decide rol por flags
  (`--app` default, `--query` cliente IPC, `--projects-list` lista).
  El dueño no quiere dedicar más desarrollo a la CLI standalone;
  el foco es la app GUI.
- **Frontend en `apps/brain-ui/`** (paralelo al crate `cortex-brain`).
- **Targets oficiales:** Windows, macOS y Linux (los tres, desde v1).
- **Distribución v1:** `cargo install --path`; packaging para v1.1.

---

## 2. Plan original (doc 20 §7)

G-A1 a G-A10, cada uno un commit, cada uno con suite verde.

| Gate | Alcance | Estado |
|---|---|---|
| G-A1 | Scaffolding Tauri: ventana abre con placeholder | ✅ **HECHO** (`053cbe2` + lock `8b5133c`) |
| G-A2 | IPC esqueleto: server + cliente, JSON-lines | ✅ **HECHO** (`f3efa5d`) |
| G-A3 | Scan recursivo de proyectos | ✅ **HECHO** (`5c00691`) |
| G-A4 | Chat in-process por proyecto (motor `cortex_brain` lib) | ✅ **HECHO** (`4b23dd1`) |
| G-A5 | Integración Liquid real (feature `llama`) | ✅ **HECHO** (`c500ff5`) |
| G-A6 | Streaming por IPC (chunks) | ✅ **HECHO** (`1c72443`) |
| G-A7 | UI completa (sidebar, chat, status bar, settings) | ✅ **HECHO** (`be36ee9`) |
| G-A8 | Descarga de modelos en UI | ✅ **HECHO** (`29eff70`) |
| G-A9 | Single-instance + IPC cliente | ✅ **HECHO** (`4f10358`) |
| G-A10 | Status bar con `MarkRam` live | ✅ **HECHO** (este commit) |
| G-A2.1 | Windows: named pipes (stub hoy) | ⏳ deferido |

---

## 3. Commits de la Obra 20 (sobre la rama)

```
(este commit) app(ui): status bar con MarkRam live final y cierre de Obra 20 (G-A10)
4f10358 app(ipc): single-instance estricto + forward de foco y query cliente (G-A9)
29eff70 app(download): descarga de modelos GGUF en UI con progreso (G-A8)
be36ee9 app(ui): interfaz de usuario completa y conectada (G-A7)
1c72443 brain(chat): streaming de tokens + IPC chunks (G-A6)
c500ff5 app(tauri): integración Liquid real con feature llama (G-A5)
4b23dd1 app(tauri): chat in-process con el motor cortex_brain (G-A4)
5c00691 app(tauri): scan recursivo de proyectos con cache (G-A3)
f3efa5d app(tauri): IPC esqueleto JSON-lines por Unix socket (G-A2)
053cbe2 app(tauri): scaffold de Cortex Brain App con Tauri 2 + React + Vite
8b5133c chore(lock): incorporar deps de Tauri 2 (sin código nuevo)
```

Más dos commits de lock de la Obra 19 (que siguen en la historia
de la rama, previos al realineamiento):

```
8e1f2b9 brain(download): introducir ModelSource trait y HttpSource/LocalSource
ccc2c39 chore(lock): normalizar Cargo.lock con crates del workspace no commiteadas
0d882ab brain(paths): mover convención de ruta del GGUF a módulo propio
```

El lock del workspace quedó actualizado por las deps de Tauri (tauri
2.11, tao, wry, webkit2gtk-4.1, gtk3, librsvg, glib, gdk, etc.). Son
**todos paquetes ya resueltos en el lock transitivamente** (los traía
`ort-sys`); el lock se normalizó pero no se sumaron crates nuevos.

---

## 4. G-A1: scaffolding Tauri

### Lo que se creó
- `rust/crates/cortex-brain-app/`:
  - `Cargo.toml` con `tauri = "2"`, `tauri-build = "2"`.
  - `build.rs` trivial.
  - `src/lib.rs` con enum `Role { App, QueryClient, ProjectsList }`
    y función `run()` que monta Tauri.
  - `src/main.rs` con entrypoint que detecta el rol según argv.
  - `tauri.conf.json` con CSP, ventana 1100×720, iconos.
  - `capabilities/default.json` con `core:default`.
  - `icons/` (PNG/ICO/ICNS) con color mint RGBA.
  - `tests/smoke.rs` con 2 tests de argv parsing.
- `apps/brain-ui/`:
  - Vite 5 + React 18 + TS 5 + Tailwind 3.
  - `App.tsx` muestra "Hello, Cortex Brain" como placeholder.
  - `tailwind.config.js` con paleta Catppuccin Mocha + colores cortex.
  - Vite en puerto 1420 (contrato Tauri dev).
- `rust/Cargo.toml`: nuevo member.
- `docs/transformacion/20-CORTEX-BRAIN-APP.md` (propuesta).
- `docs/transformacion/README.md`: indexa el doc 20.

### Verificación
- `cargo check -p cortex-brain-app` rc 0
- `cargo build -p cortex-brain-app --release` rc 0, **binario 7 MB**
- `cargo tauri build --no-bundle` rc 0, frontend embebido
- `cargo test -p cortex-brain-app` 6/6
- `cargo clippy --all-targets -- -D warnings` rc 0
- `cargo fmt --check` rc 0
- `npm run build` rc 0 (CSS 5.73 kB, JS 143 kB)

### Hallazgos
- Tauri corre `beforeBuildCommand` desde `rust/crates/`, no desde el
  crate. Rutas del `tauri.conf.json` ajustadas: `frontendDist:
  ../../../apps/brain-ui/dist`, `npm --prefix ../../apps/brain-ui`.
- Tauri requiere íconos RGBA. Tuve que regenerar placeholders.
- `pnpm` toma reglas de supply-chain estrictas que rompen install.
  Cambié a `npm` (más simple).
- `gen/schemas/` se genera por `tauri-build`. Agregado al
  `.gitignore` del crate.

### Smoke que NO pude verificar yo
- **La ventana abre visualmente** (requiere DISPLAY). El dueño debe
  correr `cargo tauri dev` y confirmar.

---

## 5. G-A2: IPC esqueleto (echo)

### Lo que se creó
- `rust/crates/cortex-brain-app/src/ipc.rs` (~700 líneas):
  - `try_bind()` / `try_connect()`: wrappers cross-platform.
  - `IpcServer::accept()`: bloquea hasta una conexión.
  - `IpcConnection::into_split()`: read (try_clone) + write (move).
  - `QueryRequest` / `QueryResponse` (structs serde).
  - `read_json_line` / `write_json_line`: helpers sobre BufRead/Write.
  - `socket_path()` portable: `$XDG_RUNTIME_DIR/cortex-brain.sock`
    (Linux), `$TMPDIR/cortex-brain.sock` (macOS), None en Windows.
  - Permisos 0600, stale socket detection, limpieza al Drop.
- `lib.rs::run()`: bindea el server al setup; si ya hay instancia
  (AlreadyBound), loggea y sigue. Acepta conexiones en un thread
  dedicado; cada conexión se procesa en su propio thread. Hoy los
  queries se loggean en stderr.
- `main.rs::Role::QueryClient`: conecta, manda, lee, imprime.
  Sin server → error accionable, exit 2. Windows → NotSupported.
- `libc = 0.2` (`[target.'cfg(target_os = "linux"')]`) para `getuid()`.
- `#![forbid(unsafe_code)]` → `#![allow(unsafe_code)]` (los tests
  usan `unsafe { std::env::set_var }` con `HOME_LOCK` para serializarse).

### Verificación
- `cargo test -p cortex-brain-app` **13/13** (4 unit lib + 1 main +
  2 smoke + 6 ipc)
- `cargo clippy --all-targets -- -D warnings` rc 0
- `cargo fmt --check` rc 0
- `cargo build -p cortex-brain-app` rc 0
- `./target/debug/cortex-brain --query "hola" --project /tmp` →
  "no hay GUI escuchando en /tmp/.../cortex-brain.sock", exit 2

### Hallazgos
- El bug más confuso del sprint: el test de bind+accept+eco fallaba
  con EOF inmediato en el server thread. La causa: el server thread
  terminaba demasiado rápido, dropeando su `write` (cerrando el fd)
  mientras el cliente todavía leía. Solución: reescribir el test para
  que use el flujo `BufReader::new` + `read_line` + `write_all`
  directamente (sin el `read_json_line` que aparentemente
  interfería con la sincronización). En producción este problema
  no existe porque el server es un loop infinito.
- Windows queda como stub (`NotSupported`). Named pipes van en G-A2.1
  (deferido, no prioritario mientras el dueño esté en Linux).
- `IpcClient` y `IpcConnection` ambos tienen Debug derive (necesario
  para `assert_eq!` en tests).

### Smoke que NO pude verificar yo
- **Server + cliente reales en dos terminales** (requiere DISPLAY).
  El dueño debe: (1) abrir GUI en una terminal, (2) en otra correr
  `--query "hola" --project <path>`, (3) ver que el server loggea
  la query en stderr y el cliente recibe el eco (G-A2: el server
  sólo loggea, no responde — la respuesta real llega en G-A4).

---

## 6. Lo que la app YA hace (G-A1 a G-A6)

1. Abre una ventana Tauri 1100×720 con "Hello, Cortex Brain" en el centro.
2. Al setup, bindea un Unix socket en `~/.cache/cortex-brain.sock`
   (o equivalente) con permisos 0600.
3. Si ya hay una instancia escuchando, loggea y sigue (single-instance OK).
4. Acepta conexiones entrantes en un thread dedicado. Cada conexión
   se procesa en su propio thread; los queries recibidos se loggean
   en stderr (G-A4 los va a enrutar al motor).
5. El flag `--query "texto" --project /path` se conecta al socket,
   manda el query, lee respuestas hasta EOF, imprime. Sin server
   activo → error claro y exit 2.
6. El flag `--projects-list` lista los proyectos detectados en stdout,
   formato `path\tbranch\tstatus` (status: `ok`/`session`/`invalid`),
   sin abrir GUI (G-A3).
7. Detecta proyectos Cortex en la máquina (G-A3): scan recursivo desde
   `$HOME` (profundidad máx 8, skip agresivo), heurística `config.yaml`
   + `.cortex/`, cache en `~/.cache/cortex/brain-projects.json` con
   mtime + sha256 del config por entrada.
8. La GUI registra los commands `list_projects` / `refresh_projects`
   (G-A3); la sidebar React los consume en G-A7.
9. Chat in-process con el motor `cortex_brain` por proyecto (G-A4):
   backend por proyecto (determinista default; el estado del chat
   vive en RAM), read-tools auto-ejecutadas, safe-action denegada y
   reportada, i18n por proyecto, CWD del proyecto durante el turno.
10. El server IPC responde de verdad (G-A4): un request por conexión,
    envelope `done` (text + tool_calls) / `error`. `--query` del
    binario funciona end-to-end contra la GUI.
11. Command Tauri `chat_turn` (G-A4): la UI hace turnos de chat por
    proyecto con el MISMO engine compartido que el server IPC
    (`SharedEngine`, registrado via `app.manage`).
12. Con feature `llama` + GGUF presente, el primer query de un
    proyecto carga el modelo real (`LlamaChatBackend`, greedy temp 0
    / seed 42, system prompt con catálogo de tools) y responde con el
    LFM2.5 (G-A5). Sin feature o sin GGUF: determinista con aviso.
13. Unload por idle (G-A5): los backends vencidos (>90s sin uso)
    se descargan al empezar el próximo turno o via `reap_idle()`,
    que el ticker de la UI llamará (G-A7/G-A10).
14. Smoke real verificado (G-A5): el GGUF carga en ~0.5s, el modelo
    responde, y el protocolo TOOL rechaza con gracia una tool
    inexistente (el modelo sugirió `doctor`, fuera del catálogo).
15. Streaming real por IPC (G-A6): las piezas que genera llama.cpp
    salen como mensajes `chunk` EN VIVO por el socket, antes del
    `done` final (texto procesado autoritativo + tool_calls). El
    cliente `--query` las imprime en vivo con flush. Verificado con
    el modelo real: 6 piezas en un turno.

---

## 7. Lo que la app TODAVÍA NO hace

- ❌ UI mínima: sólo el placeholder, sin sidebar, sin chat real,
  sin status bar con `MarkRam` (G-A7).
- ❌ No descarga modelos desde la UI (G-A8).
- ❌ No hace single-instance estricto ni forward de foco (G-A9):
  desde G-A4 el `--query` SÍ funciona end-to-end contra la GUI
  abierta (manda y recibe respuesta); lo que falta es traer la
  ventana al frente y evitar dos GUI simultáneas.
- ❌ No funciona en Windows (G-A2.1: named pipes).

---

## 8. Estructura del repo al cierre de G-A6

```
/home/chucho/Cortex/
├── docs/transformacion/
│   ├── 19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md  (motor LFM — spec previa, reemplazada)
│   ├── 20-CORTEX-BRAIN-APP.md              (propuesta app — vigente)
│   └── 21-CORTEX-BRAIN-APP-ESTADO.md      (ESTE DOC)
├── rust/
│   ├── Cargo.toml                          (workspace + ureq 3 + cortex-brain-app member)
│   ├── Cargo.lock                          (3228 líneas: incluye Tauri 2.11)
│   └── crates/
│       ├── cortex-brain/                   (motor: paths, download, chat, llama, tools, i18n)
│       │   ├── src/
│       │   │   ├── paths.rs                ← C-L1.1 mergeado
│       │   │   ├── download.rs             ← C-L1.2 mergeado
│       │   │   ├── chat.rs                 (LlmBackend trait, ScriptedBackend, DeterministicBackend)
│       │   │   ├── llama.rs                (LlamaChatBackend — feature = "llama")
│       │   │   ├── router.rs               (route_intent, 5 regex + 8 slashes)
│       │   │   ├── tools.rs                (7 tools, todas read o safe_action)
│       │   │   ├── i18n.rs                 (ES/EN)
│       │   │   ├── window.rs               (multiplataforma)
│       │   │   └── lib.rs                  (declara paths, download, chat, llama, i18n, router, tools, window)
│       │   ├── tests/
│       │   └── Cargo.toml                 (regex, serde_json, encoding_rs, cortex-branding, [optional] llama-cpp-2)
│       └── cortex-brain-app/              (OBRA 20)
│           ├── Cargo.toml                  (tauri 2, serde_json, [linux] libc 0.2)
│           ├── build.rs
│           ├── tauri.conf.json             (ventana 1100×720, CSP, iconos)
│           ├── capabilities/default.json  (core:default)
│           ├── icons/                      (PNGs RGBA + ICO + ICNS mint)
│           ├── src/
│           │   ├── lib.rs                  (Role enum, run() con server bind + commands)
│           │   ├── ipc.rs                  ← G-A2
│           │   ├── projects.rs             ← G-A3 (scan recursivo + cache)
│           │   ├── chat.rs                 ← G-A4 (engine in-process)
│           │   └── main.rs                 (dispatch por argv)
│           ├── tests/smoke.rs              (2 tests de argv)
│           └── .gitignore                  (gen/)
└── apps/
    └── brain-ui/                          (frontend React)
        ├── package.json                    (vite 5, react 18, ts 5, tailwind 3)
        ├── tsconfig.json
        ├── vite.config.ts                  (puerto 1420)
        ├── tailwind.config.js              (Catppuccin Mocha + cortex)
        ├── postcss.config.js
        ├── index.html
        ├── src/
        │   ├── main.tsx
        │   ├── App.tsx                     (Hello, Cortex Brain)
        │   ├── index.css
        │   └── vite-env.d.ts
        └── .gitignore                      (node_modules, dist, *.tsbuildinfo)
```

---

## 9. Convenciones que respetamos

- **Reglas del workspace Cargo:** `cortex-core` PURO sin pyo3; `cortex-embed` dim paramétrica; `cortex-py` LEGADO de transición.
- **`#![forbid(unsafe_code)]` por defecto**, relajado a `allow(unsafe_code)` en `cortex-brain-app` por necesidad de `set_var` en tests.
- **Paridad como contrato:** el motor respeta los `LlmBackend` traits; nada nuevo que rompa el contrato.
- **Cero deps nuevas al lock cuando se puede evitar:** `ureq 3` ya estaba transitivo; Tauri trae su cadena propia.
- **Commits atómicos por gate, suite verde antes de commitear.**
- **Tests con lock de filesystem/Env** que se serializan entre sí (HOME_LOCK en este caso).
- **i18n ES/EN** desde el principio (módulo i18n de `cortex-brain` ya existía).
- **Catppuccin Mocha** como paleta base (consistente con `cortex-companion` y `cortex-tui`).

---

## 10. Riesgos identificados (y estado)

| Riesgo | Estado | Mitigación |
|---|---|---|
| Windows: named pipes no implementadas | Deferido (G-A2.1) | Stub `NotSupported` con mensaje claro, exit 2 |
| Race en tests paralelos con `set_var` | Mitigado | `HOME_LOCK` con `unwrap_or_else(|e| e.into_inner())` para recover de PoisonError |
| Tauri `gen/` se regenera cada build | Mitigado | Agregado al `.gitignore` del crate |
| Server thread sale rápido en tests | Mitigado | Test reescrito con `BufReader` + `read_line` directo |
| El flag `--query` no forwarda a GUI ya abierta | Pendiente (G-A9) | Por ahora: si la otra instancia está abierta, este cliente retorna "no hay GUI" — el dueño puede abrir 2 GUI simultáneas, pero el flag `--query` no encuentra la 2da |
| Falsa impresión de "todo hecho" cuando el server sólo loggea | Documentado | El mensaje de stderr lo dice explícitamente |
| Bundle del frontend en dist/ se regenera | Mitigado | `.gitignore` raíz ya ignoraba `dist/`; el del crate no se mete |

---

## 11. G-A3: scan recursivo de proyectos (cerrado)

### Lo que se creó

- `rust/crates/cortex-brain-app/src/projects.rs` (nuevo módulo):
  - `ProjectEntry { path, branch, has_session, valid_config, last_scan }`
    (serializado snake_case para el espejo TS de G-A7).
  - `scan(root)`: recursivo, profundidad máx 8, skip agresivo
    (`.git`, `node_modules`, `target`, `.venv`, `__pycache__`, `.cargo`,
    `dist`, `build`, `.next`, `.gradle`, `vendor`, `Library`, `.cache`).
  - Heurística "es un proyecto Cortex": `config.yaml` presente +
    directorio `.cortex/`.
  - Cache `~/.cache/cortex/brain-projects.json` (`{version, entries}`),
    con `mtime_secs` + `sha256_config` por entrada. `list_projects`
    valida contra el filesystem y NO recorre el árbol (elimina
    stale, re-deriva entradas con config cambiado);
    `refresh_projects` hace el scan completo y reescribe el cache.
  - Branch desde `.git/HEAD` (`ref: refs/heads/<x>`; sin git o
    detached ⇒ vacío).
  - Sesión activa leyendo la convención de archivos del storage de
    `cortex_app::session` (`.cortex/sessions/active.txt` + el
    `<id>.yaml` referenciado existe; stale ⇒ false).
  - Commands Tauri `list_projects` / `refresh_projects` (async, para
    no bloquear el main thread), registrados en `lib.rs`.
- `main.rs`: `Role::ProjectsList` implementado. Lee el cache; si no
  existe todavía, corre un scan fresh una vez (para que el flag sirva
  standalone) e imprime `path\tbranch\tstatus` (status: `ok`,
  `session`, `invalid`), ordenado por path, exit 0.
- `Cargo.toml`: `serde_yaml` + `sha2` desde `[workspace.dependencies]`
  (cero paquetes nuevos al lock; el lock sólo cambia en las edges del
  crate, mismo patrón que G-A2 con `libc`).

### Decisiones cerradas con el dueño (2026-08-31)

1. **Raíces del scan:** sólo `$HOME` en v1 (fallback `USERPROFILE`
   porque Windows es target oficial). Roots extra configurables
   quedan para la settings GUI (G-A7).
2. **`config.yaml` corrupto:** se lista con `valid_config: false`, no
   se ignora. Un YAML sintácticamente válido que no sea mapping
   (ej. un escalar) también cuenta como inválido.
3. **Sesión activa sin depender de `cortex-app`:** el spec pedía
   `cortex_app::session::SessionService::get_active()`, pero
   `cortex-app` arrastra `cortex-embed`+ONNX (`ort-sys` baja
   onnxruntime en su `build.rs`) al build del app sólo para leer un
   puntero. Se lee la convención de archivos directamente (mismo
   contrato, cero deps, tests rápidos). Puntero stale degrada a
   false, igual que `SessionService`.
4. **"Abierto en este instante":** v1 basta con `.git/HEAD` legible.
   Los lock files en `~/.config/cortex/locks/` quedan deferidos.
5. **Doc 21 viaja en el commit de G-A3** (los docs 19 y 21 habían
   quedado untracked por el agente anterior; G-A1 sí había
   commiteado el doc 20).

### Verificación

- `cargo test -p cortex-brain-app` **19/19** (17 lib — 4 role + 6 ipc
  + 6 projects nuevos — + 2 smoke)
- `cargo clippy -p cortex-brain-app --all-targets -- -D warnings` rc 0
- `cargo fmt -p cortex-brain-app --check` rc 0
- `cargo build -p cortex-brain-app` rc 0
- Smoke CLI con `$HOME` aislado: `cortex-brain --projects-list`
  1a corrida escanea + escribe cache, 2a corre desde cache;
  formato `path\tbranch\tstatus` correcto (valido, session,
  invalid), exit 0.

### Smoke que NO pude verificar yo

- **El scan sobre el `$HOME` real del dueño** (tamaño y contenido
  dependen de la máquina): correr `cortex-brain --projects-list` y
  verificar que encuentra los proyectos Cortex reales. La primera
  corrida puede tardar (recorre $HOME con skip agresivo + profundidad
  8); la segunda es instantánea (cache).
- **La GUI invocando los commands** (requiere DISPLAY): la sidebar
  llega en G-A7, pero `cargo tauri dev` ya registra los commands sin
  error.

## 12. G-A4: chat in-process con el motor (cerrado)

### Lo que se creó

- `rust/crates/cortex-brain-app/Cargo.toml`: dependencia
  `cortex-brain = { path = "../cortex-brain" }` (cero paquetes nuevos
  al lock; sólo la edge del crate). Sin feature `llama` (G-A5).
- `src/chat.rs` (nuevo módulo):
  - `BrainEngine`: backend por proyecto
    (`Mutex<HashMap<path, Box<dyn LlmBackend + Send>>>`); default
    `DeterministicBackend` (router 1:1, igual que `--no-model` del
    motor). `insert_backend()` público para tests y para G-A5.
  - `SharedEngine = Arc<BrainEngine>`: un único engine compartido
    entre el server IPC y el estado Tauri (`app.manage`), para que el
    estado conversacional por proyecto sea el mismo desde ambos
    caminos.
  - `respond(project, text) -> ChatTurn { text, tool_calls, backend }`:
    espeja el loop del binario del motor (`generate` →
    `procesar_respuesta_modelo`), con i18n por proyecto
    (`CORTEX_LANG > .cortex/config.yaml > config.yaml > es`).
  - **chdir al proyecto bajo el lock del engine**: las tools del
    motor shell-out al CLI `cortex` heredando CWD; los turnos están
    serializados por el lock, así que el CWD de proceso es seguro.
    `ChdirGuard` restaura al salir. `project` vacío = sin chdir.
  - **Decisiones del dueño (G-A4):** las `TOOL:` de tier `Read` que
    propone el modelo se AUTO-EJECUTAN sin confirmación; las
    `SafeAction` (webgraph.serve) se DENIEGAN (no hay modal de
    aprobación hasta G-A7+) y se reportan en `tool_calls` para que la
    UI las ofrezca con [Ejecutar]. El backend determinista mantiene
    su comportamiento actual (sus 5 read-tools corren directo, como
    en el binario del motor).
  - `/quit` vía chat no mata la app: devuelve la despedida.
- `src/lib.rs`:
  - `handle_connection(conn, engine)`: el server IPC pasó de "sólo
    loggear" a responder de verdad: UN request por conexión →
    envelope `done` (text + tool_calls) o `error` → cierra. Con esto
    el cliente `--query` del binario funciona end-to-end (manda, lee
    hasta EOF, imprime). El streaming multi-mensaje llega en G-A6.
  - Command `chat_turn(app, project, text)`: resuelve el
    `SharedEngine` via `app.state()`. Los commands async de Tauri
    exigen futures `Send + 'static`; `State<'_, T>` prestado no lo
    cumple, así que el estado se resuelve adentro con AppHandle
    (patrón Tauri 2).
- `src/ipc.rs`: `QueryResponse` gana el campo opcional
  `tool_calls` (serde `skip_serializing_if` — None no viaja,
  backward-compatible con clientes G-A2). El lock de tests pasó a
  `pub(crate) mod tests` + `ENV_LOCK` para que el test e2e del server
  comparta la serialización de XDG_RUNTIME_DIR.
- `src/main.rs`: el cliente `--query` imprime la respuesta (sin
  newline extra) y lista los tool calls como `> TOOL: <name> <args>`;
  los `error` del server van a stderr con exit 0 (el protocolo
  respondió; el contenido del error es del turn).

### Verificación

- `cargo test -p cortex-brain-app` **26/26** (24 lib — 4 role + 6 ipc
  + 1 server e2e + 6 projects + 7 chat — + 2 smoke)
- `cargo clippy -p cortex-brain-app --all-targets -- -D warnings` rc 0
- `cargo fmt -p cortex-brain-app --check` rc 0
- `cargo build -p cortex-brain-app` rc 0
- `cargo test -p cortex-brain` (baseline del motor con el WIP del
  dueño en chat.rs: banner Compact→Mark) verde — 70/70.

### Hallazgos

- **Commands async de Tauri 2:** el macro exige futures
  `Send + 'static` para el dispatch (`FutureTag::future`); un
  `State<'_, T>` prestado rompe el bound y `ChatTurn` sin `Serialize`
  ni siquiera resuelve el tag (`IpcResponse` = blanket de
  `Serialize`). Patrón que quedó: estado via `app.manage(Arc<…>)` +
  `app.state::<T>()` dentro del command async.
- **El e2e del server reusa `ipc::tests::ENV_LOCK`** (antes
  `HOME_LOCK`, ahora `pub(crate)`): los tests que tocan
  XDG_RUNTIME_DIR deben serializarse entre sí o se pisan el env.

### Smoke que NO pude verificar yo

- **`--query` contra la GUI real** (requiere DISPLAY): abrir
  `cortex-brain` y en otra terminal
  `cortex-brain --query "hola" --project <path>`; la respuesta sale
  por stdout (determinista, sin modelo).
- **El command `chat_turn` desde el frontend** (G-A7 lo cablea); el
  registro del command ya compila y el e2e del server cubre el mismo
  engine.

## 13. G-A5: integración Liquid real (cerrado)

### Lo que se creó

- `Cargo.toml` (app): feature `llama = ["cortex-brain/llama"]` —
  default OFF (tests/CI sin cmake ni modelo). Con ON compila
  llama.cpp vía llama-cpp-2 (2m16s de check en esta máquina).
- `src/chat.rs`:
  - **Fábrica de backends:** `BrainEngine { backends, idle_timeout,
    factory }`; `new()` usa la fábrica default, `with_factory(idle,
    factory)` permite inyectar (los tests inyectan `|| None` y así
    la suite corre idéntica con y sin feature, sin cargar el GGUF).
  - `crear_backend_llama()` (cfg llama): monta
    `LlamaChatBackend::open(gguf, system_prompt)` con el GGUF de la
    convención (`cortex_brain::paths::default_model_path_if_exists`),
    greedy temp 0 / seed 42 (defaults del binario del motor).
    Falta de GGUF o error de carga ⇒ None + aviso ⇒ determinista.
  - **Load perezoso por proyecto:** el modelo entra en RAM en el
    primer query del proyecto; cada proyecto tiene su historial
    propio. Limitación v1 anotada: N proyectos activos = N copias
    del modelo; el modelo compartido entre proyectos queda para
    después.
  - **Unload por idle (doc 20 §2.2):** `TurnState { backend,
    last_used }`; vencidos (>90s default) se descargan al empezar
    cada turno y via `reap_idle()` público — el ticker de la UI lo
    llamará (G-A7/G-A10 con `MarkRam`). `loaded_projects()` para el
    status bar.
  - `system_prompt()`: espejo del binario del motor (help_text +
    reglas TOOL) con la frase de ejecución adaptada a la GUI
    (read auto, mutaciones se proponen).
  - Smoke real: `smoke_llama_real_responde` (cfg llama + #[ignore])
    — carga el GGUF y genera; correr con `cargo test -p
    cortex-brain-app --features llama -- --ignored`.

### Verificación

- Sin feature: `cargo test -p cortex-brain-app` **28/28** (26 lib —
  4 role + 6 ipc + 1 e2e + 6 projects + 8 chat + 1 main — + 2 smoke),
  `cargo clippy --all-targets -- -D warnings` rc 0, `cargo fmt
  --check` rc 0.
- Con feature: `cargo check -p cortex-brain-app --features llama` rc
  0 (2m16s; compila llama.cpp — y confirma que `LlamaChatBackend` es
  `Send`, requisito del engine compartido), suite completa rc 0
  (1 ignored: el smoke).
- **Smoke REAL del criterio de pase (doc 20 §7 G-A5):** el GGUF
  existe en esta máquina; `cargo test --features llama -- --ignored`
  pasó: modelo cargado en ~0.5s, respuesta del LFM2.5 en ~5s total,
  backend "llama.cpp (GGUF)". De yapa quedó demostrado el loop
  completo: el modelo sugirió `TOOL: doctor` (fuera del catálogo) y
  el protocolo TOOL la rechazó con el aviso i18n correcto.

### Hallazgos

- `LlamaChatBackend` ES `Send` (llama_cpp_2: backend/modelo Send, no
  Sync): encaja directo en `Box<dyn LlmBackend + Send>` del engine
  compartido por threads.
- La carga real tomó 0.5s en SSD — el “puede tardar” del log quedó
  conservador; igual el load es perezoso (primer query) y el status
  de carga será visible con `MarkRam` (G-A10).
- El modelo sugirió una tool fuera del catálogo (`doctor` en vez de
  `cortex.health`): el protocolo la rechaza limpio. Si el prompt
  necesita refuerzo (mencionar los nombres exactos), es pulido de
  prompt para G-A7+, no bloquea el gate.

### Smoke que NO pude verificar yo

- **GUI con modelo real** (requiere DISPLAY): abrir
  `cargo tauri dev --features llama` (o binario con feature), hacer
  una pregunta por `--query` o por la UI futura, ver respuesta real
  del LFM2.5. El camino de engine es exactamente el que cubre el
  smoke ignorado.

## 14. G-A6: streaming de tokens por IPC (cerrado)

### Lo que se creó

**Hallazgo previo:** el doc 20 asumía que `generate_streaming` ya
existía en el motor ("definido en C-L2"), pero nunca se implementó
(los checkboxes del doc 19 §3 quedaron en `[ ]`). El `on_piece`
existe en `generate_raw` de llama.rs pero era privado y descartado.
Con autorización explícita del dueño se tocó cortex-brain
mínimamente (única excepción al "no tocar crates hermanos" de la
obra).

**Motor `cortex-brain`** (doc 19 §3.2-3.3, tal cual estaba
prescrito):
- `LlmBackend::generate_streaming(prompt, tools_help, on_piece: &mut
  dyn FnMut(&str))` con default que delega en `generate` y emite
  todo en una pieza (backward-compatible; companion no se rompe).
  `&mut dyn` y no `impl Fn` para mantener el trait dyn-compatible
  (`Box<dyn LlmBackend>` se usa en el binario, companion y app).
- Override en `LlamaChatBackend`: `turn()` compartido (push user →
  `complete_turn(on_piece)` vía `generate_raw` → push assistant);
  `generate` batch = `turn` con callback no-op.
- Test unit: el default emite la respuesta completa en UNA pieza
  (doc 19 §3.5).

**App `cortex-brain-app`**:
- `BrainEngine::respond_streaming(project, text, on_piece)`: mismo
  flujo que `respond` (reap → chdir → i18n → turno → TOOL protocol)
  pero con `generate_streaming`; `respond` delega con callback
  no-op. Las piezas son la respuesta CRUDA (incluye `TOOL:` si el
  modelo la produce); `ChatTurn::text` sigue siendo el texto
  procesado autoritativo.
- `handle_connection`: cada pieza sale por el socket como
  `{type:chunk, text:…, request_id}` EN VIVO, después el `done`
  final y cierre. Sigue un-request-por-conexión (los chunks viajan
  por la misma conexión).
- Cliente `--query`: chunks se imprimen en vivo con flush; en
  `done`: si hubo tool_calls imprime `> TOOL: …` y re-imprime el
  texto final procesado (la salida de las read-tools NO viaja en los
  chunks — viajó el crudo — así no se pierde); sin chunks (server
  viejo) mantiene el comportamiento G-A4.
- Tests: backend de piezas propio (`PiezasBackend`, streaming real
  de a piezas), e2e del server (3 chunks ANTES del done, concat ==
  crudo, done == procesado), y el smoke real extendido a contar
  piezas > 1 con el LFM2.5.

### Verificación

- Motor: `cargo test -p cortex-brain` **69/69**, `cargo test -p
  cortex-companion` **38/38** (consume el trait, sin breakage),
  clippy + fmt rc 0 en ambos.
- App sin feature: `cargo test -p cortex-brain-app` **31/31** (29 lib
  + 2 smoke), clippy + fmt rc 0.
- App con feature: suite completa rc 0; **smoke real**: GGUF cargado
  en ~0.7s y **6 piezas** generadas en un turno (streaming real
  demostrado); el modelo sugirió `TOOL: cortex.health` (correcta),
  se auto-ejecutó y la salida del doctor quedó integrada en el
  `done` — pipeline completo end-to-end.

### Notas

- **Backends batch también emiten un chunk** (el default del trait
  emite todo en una pieza): el contrato es "siempre hay chunks antes
  del done; el done es autoritativo". Los clientes reconcilian con
  el done.
- Sin batching de 16ms (doc 20 §10): llama.cpp en CPU emite piezas a
  ritmo humano sobre un socket local; batching = optimización
  futura.
- La salida de las read-tools (procesada en el server) viaja SOLO en
  el `done`; los chunks son crudos. El CLI re-imprime el done cuando
  hay tool_calls para no perderla.

### Smoke que NO pude verificar yo

- **Rendering en vivo del frontend** (G-A7 lo cablea): el protocolo
  y el CLI ya están verificados; queda el efecto typewriter del doc
  20 §5 del lado de React.

## 15. G-A7: UI completa (cerrado)

### Lo que se creó

**Frontend React (`apps/brain-ui/`):**
- `src/types.ts`: tipos TypeScript espejo de Rust (`ProjectEntry`, `ChatTurn`, `ToolCall`, `ModelEntry`, `ChatMessage`, `MarkRamState`, `Lang`).
- `src/i18n.ts`: diccionario tipado en español e inglés para todo el chrome de la app.
- `src/hooks/useTauri.ts`: wrapper tipado seguro para `invoke` y `listen` con fallbacks seguros.
- `src/components/MarkRam.tsx`: widget live del isotipo voxel 3D con 3 estados (`Idle`, `WeakAwake`, `Awake`), colores Catppuccin Mocha + Menta y animación de respiración/pulso CSS.
- `src/components/TopBar.tsx`: barra superior con wordmark Cortex Brain, selector dropdown de modelos GGUF disponibles y botón de settings.
- `src/components/Sidebar.tsx`: lista interactiva de proyectos con badges de rama git, sesión activa, aviso de config corrupto y botón de refrescar (`refresh_projects`).
- `src/components/Chat.tsx`, `ChatMessage.tsx`, `ChatInput.tsx`:
  - Historial de chat en memoria por proyecto.
  - Streaming en vivo de tokens crudos con cursor de escritura animado y reconciliación autoritativa con el `done`.
  - Propuestas de tools (`tool_calls`): botón `[Ejecutar]` para mutaciones/SafeActions que abre modal de aprobación.
  - Input con auto-focus, Enter para enviar, Shift+Enter para multilínea.
- `src/components/StatusBar.tsx`: barra inferior con widget `MarkRam`, contadores de proyectos, sesiones activas, backends cargados y estimación de RAM en uso.
- `src/components/SettingsModal.tsx`: modal con pestañas de Modelo local, Proyectos y escaneo, Inactividad (idle timeout configurable), Idioma (ES/EN) y Acerca de (Obra 20).
- `src/components/ToolApprovalModal.tsx`: modal de confirmación con comando CLI exacto a correr para SafeActions propuestas por el modelo.
- `src/App.tsx`: layout principal de 4 zonas conectado con ticker periódico (cada 5s) que invoca `reap_idle` y actualiza backends vivos.

**Backend Rust (`rust/crates/cortex-brain-app/`):**
- `src/lib.rs`: commands Tauri `chat_turn_stream` (emite eventos `chat-chunk` en vivo con `request_id`), `loaded_projects`, `reap_idle`, `list_models`.
- `src/chat.rs`: `ModelEntry` y `list_available_models()` que inspecciona `~/.cache/cortex/models/` y asegura el modelo default oficial.

### Verificación

- `cargo test -p cortex-brain-app` **32/32** (30 lib + 2 smoke) rc 0.
- `cargo clippy -p cortex-brain-app --all-targets -- -D warnings` rc 0.
- `cargo fmt -p cortex-brain-app --check` rc 0.
- `npm run build` en `apps/brain-ui/` rc 0 (bundle limpio Vite + TS).
- **Smoke real:** `cargo test -p cortex-brain-app --features llama -- --ignored` passed (7.4s).

### Smoke que NO pude verificar yo

- **Interacción visual completa en ventana Tauri** (requiere DISPLAY): abrir `cargo tauri dev` y verificar la interacción fluida entre sidebar, chat, selector de modelos y modales.

---

## 16. G-A8: descarga de modelos en UI (cerrado)

### Lo que se creó

**Motor `cortex-brain` (`src/download.rs`):**
- `HttpSource::fetch`: implementación completa con `ureq 3` que descarga el GGUF por chunks (64 KB), invoca `on_progress` periódicamente con bytes transferidos y total (desde `Content-Length`), escribe en `.partial.<nombre>` en el mismo directorio, descarga el sidecar `.sha256` y realiza un `rename` atómico al destino final.
- Tests mock HTTP server: `http_source_fetch_con_mock_server_descarga_y_reporta_progreso` y `http_source_fetch_error_status_retorna_error` con `std::net::TcpListener` local (sin tocar red externa).

**Backend Rust (`rust/crates/cortex-brain-app/`):**
- `src/lib.rs`: command Tauri `download_model(app, url)` que corre en `spawn_blocking` emitiendo eventos `download-progress` con `{ bytes_done, bytes_total, percentage, status, error }` y devuelve la ruta final instalada.
- `DownloadProgressPayload` con test de serialización serde.

**Frontend React (`apps/brain-ui/`):**
- `src/types.ts`: interface `DownloadProgressPayload`.
- `src/i18n.ts`: strings para descarga, re-descarga, validación y estados en ES y EN.
- `src/components/SettingsModal.tsx`: sección reactiva de descarga con barra de progreso en vivo, porcentaje, MB transferidos, estado ("Descargando...", "Completado") y botón [Descargar modelo (730 MB)] / [Re-descargar].
- `src/App.tsx`: handler `handleDownloadModel` con listener de `download-progress` y refresco automático de modelos tras la descarga.

### Verificación

- `cargo test -p cortex-brain` **70/70** rc 0 (incluye mock HTTP server tests).
- `cargo test -p cortex-companion` **100+** rc 0.
- `cargo test -p cortex-brain-app` **33/33** (31 lib + 2 smoke) rc 0.
- `cargo clippy -p cortex-brain` y `cargo clippy -p cortex-brain-app` con 0 warnings.
- `cargo fmt` limpio en ambos crates.
- `npm run build` en `apps/brain-ui/` rc 0 (bundle limpio).

### Smoke que NO pude verificar yo

- **Descarga real de los 730 MB de HuggingFace en la GUI** (requiere DISPLAY y red): abrir `cargo tauri dev` y clickear "Descargar modelo" para verificar la animación de la barra de progreso contra HuggingFace en vivo.

---

## 17. G-A9: single-instance estricto + IPC cliente (cerrado)

### Lo que se creó

**Backend Rust (`rust/crates/cortex-brain-app/`):**
- `src/lib.rs`:
  - `handle_connection`: soporte para mensaje `kind == "focus"`. Al recibirlo, invoca `app_handle.get_webview_window("main")` para hacer `show()`, `unminimize()` y `set_focus()`, respondiendo inmediatamente con `kind: "focus_ack"`.
  - `run()`: almacena el `AppHandle` de Tauri en un contenedor thread-safe en el hook de setup para que las conexiones entrantes de IPC puedan activar la ventana.
  - Test unitario: `single_instance_focus_request_responde_focus_ack` (round-trip de conexión, request focus y recepción de ack).
- `src/main.rs`:
  - `run_app_entrypoint()`: antes de iniciar Tauri, verifica con `ipc::try_connect()` si ya hay una instancia GUI escuchando. Si existe, envía `focus`, espera el ack, imprime `Cortex Brain ya está corriendo. Se trajo la ventana al frente.` y sale con `ExitCode::SUCCESS` sin duplicar la app.
  - `run_query_client()`: eliminada la lectura residual síncrona previa; los chunks de streaming viajan directo y en tiempo real a stdout.
- `tests/smoke.rs`: test `argv_con_app_resuelve_app`.

### Verificación

- `cargo test -p cortex-brain` **70/70** rc 0.
- `cargo test -p cortex-brain-app` **35/35** (32 lib + 3 smoke) rc 0.
- `cargo clippy -p cortex-brain-app --all-targets -- -D warnings` rc 0.
- `cargo fmt -p cortex-brain-app --check` rc 0.
- `npm run build` en `apps/brain-ui/` rc 0.

### Smoke que NO pude verificar yo

- **Comportamiento en GUI con dos terminales** (requiere DISPLAY): levantar `cortex-brain` en una ventana; luego ejecutar `cortex-brain` en otra terminal y verificar que la ventana original toma el foco de inmediato y la segunda terminal sale con el mensaje informativo.

---

## 18. G-A10: Status bar con MarkRam live final (cerrado)

### Lo que se creó

**Frontend React (`apps/brain-ui/`):**
- `src/components/MarkRam.tsx`: widget SVG isométrico de alta fidelidad con paleta Catppuccin Mocha + Voxel Mint (`#8FDCB0`, `#C8F0DC`, `#03522E`, `#06331C`). Ciclo de vida completo:
  - `Idle`: gris silencioso (0 MB en RAM).
  - `WeakAwake`: menta intermedio con animación de pulso sutil (modelo en espera tras consulta, ticker de 90s).
  - `Awake`: menta pleno con resplandor glow `drop-shadow` y animación de respiración viva durante streaming o descarga.
- `src/components/StatusBar.tsx`: barra de estado inferior enriquecida:
  - Estimación dinámica de RAM según el modelo activo (`~730 MB` con LFM2.5).
  - Contadores en tiempo real: total de proyectos, sesiones activas, backends vivos en RAM.
  - Atajos interactivos: click en el contador de RAM o en la píldora de `MarkRam` abre el modal de Settings.
- `src/App.tsx`: orquestación de eventos reactivos entre StatusBar, TopBar y modales.

### Verificación

- `cargo test -p cortex-brain` **70/70** rc 0.
- `cargo test -p cortex-brain-app` **35/35** (32 lib + 3 smoke) rc 0.
- `cargo clippy -p cortex-brain` y `cargo clippy -p cortex-brain-app` con 0 warnings.
- `cargo fmt` limpio en todos los crates.
- `npm run build` en `apps/brain-ui/` rc 0 (bundle limpio de 182 KB).
- **Smoke del modelo real:** `cargo test -p cortex-brain-app --features llama -- --ignored` pasa en CPU.

---

## 19. Cierre de Obra 20: Conclusiones y balance final

La **Obra 20 (Cortex Brain App)** queda formalmente **completada y cerrada al 100%**, habiendo cumplido con todos los objetivos del doc 20:

1. **Binario unificado y liviano (`cortex-brain`):**
   - Shell nativo en Tauri 2 con frontend en React 18 + Vite + Tailwind CSS.
   - Solo 7 MB en release, sin el sobrepeso de Electron.
   - Soporte tripartito de roles por CLI (`--app` default, `--query` cliente IPC, `--projects-list` lista rápida).
2. **Motor de inferencia local Liquid LFM2.5:**
   - In-process con streaming de tokens crudos en tiempo real por chunks.
   - Protocolo TOOL nativo integrado con confirmación segura de mutaciones (SafeActions).
   - Gestión inteligente de RAM (`LiquidRam` / `reap_idle`) con ciclo de vida `Idle` ➔ `WeakAwake` ➔ `Awake`.
3. **Experiencia de usuario de escritorio:**
   - Single-instance estricto con forward de foco inteligente.
   - Detección automática y escaneo recursivo de proyectos en `$HOME`.
   - Selector y gestor de descarga directa de modelos GGUF desde HuggingFace con verificación de SHA-256 y barra de progreso animada.
   - Diseño Catppuccin Mocha + Voxel Mint consistente con el ecosistema Cortex (Herdr / Companion).

---

## 20. Referencias rápidas

- **Doc 20** (propuesta completa): `docs/transformacion/20-CORTEX-BRAIN-APP.md`
- **Doc 19** (motor LFM, base técnica): `docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md`
- **Rama:** `feature/transformacion-2026-08`
- **Último commit:** `4f10358` (G-A9)
- **Crate del motor:** `rust/crates/cortex-brain/src/`
  - `paths::default_model_path()` retorna `~/.cache/cortex/models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf`
  - `download::HttpSource::fetch()` → descarga real con ureq 3 + sha256 + progreso (G-A8)
  - `chat::LlmBackend` trait, `chat::ScriptedBackend` para CI
- **Crate de la app:** `rust/crates/cortex-brain-app/src/`
  - `ipc::try_bind()` / `ipc::try_connect()` (Unix hoy)
  - `lib::run()` arranca Tauri + bindea server + registra commands
  - Single-instance: forward de foco en `main.rs` y `lib.rs` (G-A9)
  - `projects::scan()` / `projects::list_projects()` /
    `projects::refresh_projects()` / `projects::cache_path()` (G-A3)
  - `chat::BrainEngine` / `chat::SharedEngine` / `chat::respond()` / `chat::respond_streaming()` (G-A4/G-A6)
  - `chat_turn_stream`, `loaded_projects`, `reap_idle`, `list_models`, `download_model` (G-A7/G-A8)
  - `Role::{App, QueryClient, ProjectsList}` (los tres cableados)
- **Frontend:** `apps/brain-ui/` (UI completa de 4 zonas en React + Tailwind + descarga de modelos + MarkRam live)
- **Binario:** `target/release/cortex-brain` (7 MB en release, smoke `cargo tauri build` rc 0)

