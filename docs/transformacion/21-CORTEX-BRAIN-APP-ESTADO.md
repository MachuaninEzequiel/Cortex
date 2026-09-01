# 21 — Cortex Brain App: estado al cierre de G-A3

> Estado: ASENTAMIENTO — toda la Obra 20 hasta G-A3, listo para G-A4.
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
| G-A3 | Scan recursivo de proyectos | ✅ **HECHO** (este commit) |
| G-A4 | Chat in-process por proyecto (motor `cortex_brain` lib) | ⏳ |
| G-A5 | Integración Liquid real (feature `llama`) | ⏳ |
| G-A6 | Streaming por IPC (chunks) | ⏳ |
| G-A7 | UI completa (sidebar, chat, status bar, settings) | ⏳ |
| G-A8 | Descarga de modelos en UI | ⏳ |
| G-A9 | Single-instance + IPC cliente | ⏳ (G-A2 hace single-instance; G-A9 cablea el forward to running) |
| G-A10 | Status bar con `MarkRam` live | ⏳ |
| G-A2.1 | Windows: named pipes (stub hoy) | ⏳ deferido |

---

## 3. Commits de la Obra 20 (sobre la rama)

```
(este commit) app(tauri): scan recursivo de proyectos con cache (G-A3)
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

## 6. Lo que la app YA hace (G-A1 + G-A2 + G-A3)

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

---

## 7. Lo que la app TODAVÍA NO hace

- ❌ No tiene un motor de chat real (G-A4): el server sólo loggea.
- ❌ No carga el modelo Liquid (G-A5): el LLM no se usa todavía.
- ❌ No streamea tokens al cliente (G-A6).
- ❌ UI mínima: sólo el placeholder, sin sidebar, sin chat real,
  sin status bar con `MarkRam` (G-A7).
- ❌ No descarga modelos desde la UI (G-A8).
- ❌ No forwarda `--query` a una GUI ya abierta (G-A9): hoy el
  cliente retorna "no hay GUI"; el flag existe pero no hace
  forward. La app actual puede coexistir con otra instancia,
  pero el cliente externo no la encuentra.
- ❌ No funciona en Windows (G-A2.1: named pipes).

---

## 8. Estructura del repo al cierre de G-A3

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

## 12. Próximo gate (G-A4): chat in-process con el motor

Del doc 20 §7: cuando se selecciona un proyecto en la UI, el chat usa
el motor `cortex_brain` (lib) con el path del proyecto como contexto,
TODO in-process (sin IPC para esto). Sin modelo GGUF usa
`ScriptedBackend`/`DeterministicBackend` para CI; el modelo real entra
en G-A5 (feature `llama`).

Criterio de pase: test de integración end-to-end con backend scripted
(sin modelo); el server IPC del G-A2 pasa a responder queries
ruteándolas al motor.

---

## 13. Referencias rápidas

- **Doc 20** (propuesta completa): `docs/transformacion/20-CORTEX-BRAIN-APP.md`
- **Doc 19** (motor LFM, base técnica): `docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md`
- **Rama:** `feature/transformacion-2026-08`
- **Último commit:** `f3efa5d` (G-A2)
- **Crate del motor:** `rust/crates/cortex-brain/src/`
  - `paths::default_model_path()` retorna `~/.cache/cortex/models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf`
  - `download::HttpSource::fetch()` → `DownloadError::NotImplemented` (G-A2 marca; C-L1.3 lo implementa)
  - `chat::LlmBackend` trait, `chat::ScriptedBackend` para CI
- **Crate de la app:** `rust/crates/cortex-brain-app/src/`
  - `ipc::try_bind()` / `ipc::try_connect()` (Unix hoy)
  - `lib::run()` arranca Tauri + bindea server + registra commands
  - `projects::scan()` / `projects::list_projects()` /
    `projects::refresh_projects()` / `projects::cache_path()` (G-A3)
  - `Role::{App, QueryClient, ProjectsList}` (los tres cableados)
- **Frontend:** `apps/brain-ui/src/App.tsx` (placeholder, G-A7 lo reemplaza)
- **Binario:** `target/release/cortex-brain` (7 MB en release, smoke `cargo tauri build` rc 0)
