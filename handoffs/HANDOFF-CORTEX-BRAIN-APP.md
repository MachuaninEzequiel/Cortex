# Handoff — Cortex Brain App (post G-A6)

> **De:** Agente de coding (Claude, sesión 2026-08-31/09-01).
> **Para:** Próximo agente que continúa la Obra 20.
> **Cuándo:** Al cierre de G-A6 (streaming de tokens por IPC) en
> `feature/transformacion-2026-08`. Último commit: `1c72443`.
> **Objetivo:** Que tengas TODO el contexto para arrancar G-A7 sin
> preguntar nada de lo que ya está decidido.

---

## 1. Quién es el dueño y cómo trabaja

- **Dueño:** Chucho. Trabaja con `feature/transformacion-2026-08`,
  commits locales, **sin push** (decisión del repo).
- **Estilo de commits:** Conventional Commits en español, un commit
  por gate, suite verde antes de commitear.
- **Aprobación de planes:** Antes de tocar código, presentale el plan
  del commit (alcance exacto, archivos a tocar, criterios de pase) y
  esperá su OK ("está perfecto, dale", "gogo"). Pregunta con opciones
  concretas (recomendado primero); él ajusta rápido cuando hace falta.
  Dos de tres gates aprobados **con ajustes**, así que la revisión de
  plan vale oro.
- **Tests:** quiere cobertura real pero **sin ceremonia TDD estricta**
  ni "pruebas tan grandes ni burocráticas" (cita textual). Tests
  enfocados (5-8 por gate), los 3 gates de verificación SÍ o SÍ.
- **No toca código que no entienda:** leé los docs y el código antes
  de proponer. Si una duda no está resuelta en el doc, **preguntale**.
- **Decisión de scope:** el handoff anterior prohibía tocar crates
  hermanos. Para G-A6 él autorizó explícitamente tocar
  `cortex-brain` (mínimamente). La regla vigente: **pedir autorización
  antes de salir de `cortex-brain-app`**, no asumir que está prohibido
  ni que está permitido.

## 2. Dónde está la verdad

### Documentos canónicos (leer en este orden)

1. **`docs/transformacion/21-CORTEX-BRAIN-APP-ESTADO.md`** — estado
   vivo de la obra, **actualizado al cierre de G-A6**. Cada gate
   cerrado tiene su sección con lo que se creó, verificación,
   hallazgos y smoke pendiente. **Es tu mapa principal.**
2. **`docs/transformacion/20-CORTEX-BRAIN-APP.md`** — propuesta
   completa (contrato): producto, arquitectura, gates, fuera de
   alcance.
3. **`docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md`** —
   motor LFM (paths, download, streaming del trait). Ojo: sus
   checkboxes de Trabajo 2 (streaming) decían `[ ]` — G-A6 lo
   implementó.
4. **`docs/herdr/README.md`** — design system (Catppuccin Mocha +
   voxel mint). **Crítico para G-A7** (es el gate de UI).
5. `docs/transformacion/README.md` — índice de obras.

### Código actual (los archivos que existen y qué son)

- `rust/crates/cortex-brain-app/` — el crate de la app:
  - `src/lib.rs` — `Role` enum, `run()` (Tauri + server IPC +
    registro de commands), `handle_connection()` (chunk/done/error).
  - `src/chat.rs` — **el corazón (G-A4/G-A5/G-A6)**: `BrainEngine`
    (backend por proyecto + fábrica inyectable + idle reap),
    `SharedEngine` (Arc compartido server/estado Tauri),
    `respond`/`respond_streaming`, `ChdirGuard`, `ToolCall`,
    `ChatTurn`, `catalogo_tools()`, `system_prompt()` (cfg llama).
  - `src/projects.rs` — **G-A3**: `scan()` recursivo (prof 8, skip de
    13 dirs), cache `~/.cache/cortex/brain-projects.json` (mtime +
    sha256), `list_projects()` (valida cache, NO recorre árbol),
    `refresh_projects()`, `scan_root()`, sesión activa por convención
    de archivos.
  - `src/ipc.rs` — **G-A2**: `try_bind`/`try_connect`, JSON-lines,
    `QueryRequest`/`QueryResponse` (con `tool_calls` opcional).
  - `src/main.rs` — entrypoint: `--query` (cliente, imprime chunks en
    vivo), `--projects-list` (lee cache, `path\tbranch\tstatus`),
    default GUI.
  - `Cargo.toml` — feature `llama = ["cortex-brain/llama"]` (default
    OFF), deps: tauri 2, serde, serde_json, serde_yaml, sha2,
    cortex-brain, libc (linux).
  - `tests/smoke.rs` — 2 tests de argv.
- `rust/crates/cortex-brain/` — **el motor** (LLM backend):
  - `src/chat.rs` — trait `LlmBackend` (**con `generate_streaming`
    desde G-A6**), `ScriptedBackend`, `DeterministicBackend`,
    `procesar_respuesta_modelo` (protocolo TOOL), `extraer_tool`,
    banner.
  - `src/llama.rs` — `LlamaChatBackend` (cfg feature `llama`):
    `open(path, system)`, `with_temp/with_seed`, `turn()` con
    `generate_raw(on_piece)` — streaming real.
  - `src/paths.rs` — convención `~/.cache/cortex/models/`.
  - `src/router.rs`, `tools.rs` (7 tools, shell-out al CLI `cortex`
    respetando CWD), `i18n.rs` (ES/EN, global de proceso),
    `download.rs`, `window.rs`.
- `apps/brain-ui/` — frontend React/Vite/Tailwind (G-A1): **aún es el
  placeholder "Hello, Cortex Brain"**; G-A7 lo reemplaza. Vite en
  puerto 1420, `npm` (NO pnpm).
- `rust/Cargo.toml` — workspace.

## 3. Estado de los gates

| Gate | Estado | Commit | Notas |
|---|---|---|---|
| G-A1 | ✅ HECHO | `053cbe2` (+ lock `8b5133c`) | Scaffold Tauri. Ventana abre con placeholder. |
| G-A2 | ✅ HECHO | `f3efa5d` | IPC esqueleto (echo). |
| G-A3 | ✅ HECHO | `5c00691` | Scan recursivo de proyectos + cache. |
| G-A4 | ✅ HECHO | `4b23dd1` | Chat in-process con el motor + server responde. |
| G-A5 | ✅ HECHO | `c500ff5` | Liquid real con feature `llama`. Smoke real OK. |
| G-A6 | ✅ HECHO | `1c72443` | Streaming: trait + chunks IPC + cliente en vivo. |
| **G-A7** | ⏳ **PRÓXIMO** | — | **UI completa** (sidebar, chat, top bar, status bar, settings). |
| G-A8 | ⏳ | — | Descarga de modelos en UI. |
| G-A9 | ⏳ | — | Single-instance estricto + forward de foco. |
| G-A10 | ⏳ | — | Status bar con `MarkRam` live. |
| G-A2.1 | ⏳ deferido | — | Named pipes para Windows. |

## 4. Qué hace la app HOY (post G-A6)

1. GUI Tauri 1100×720 con placeholder React.
2. Al setup: bindea Unix socket (`$XDG_RUNTIME_DIR/cortex-brain.sock`),
   registra commands (`list_projects`, `refresh_projects`,
   `chat_turn`) y crea el `SharedEngine` (`app.manage`).
3. Detecta proyectos Cortex (`config.yaml` + `.cortex/`) escaneando
   `$HOME` (prof 8, skip agresivo), con cache persistente
   (`mtime` + `sha256_config` por entrada).
4. **Chat in-process por proyecto**: `chat_turn` (Tauri) y el server
   IPC comparten el MISMO `BrainEngine`. Primer query de un proyecto
   → fábrica: con feature `llama` + GGUF presente carga
   `LlamaChatBackend` real (greedy temp 0, seed 42); si no,
   `DeterministicBackend` (router 1:1).
5. **Streaming real**: las piezas que genera llama.cpp salen como
   `chunk` por el socket en vivo; al final un `done` con el texto
   procesado autoritativo + `tool_calls`. Verificado con el modelo
   real: 6 piezas en un turno.
6. **Protocolo TOOL**: las `TOOL:` de tier Read que propone el modelo
   se auto-ejecutan (salida integrada en el `done`); las SafeAction
   se deniegan y se reportan (modal de aprobación en G-A7+).
7. **Unload por idle** (>90s): `reap_idle()` público para el ticker de
   la UI; `loaded_projects()` para el status bar.
8. `--query "texto" --project <path>` funciona end-to-end contra la
   GUI abierta (chunks en vivo en stdout).
9. `--projects-list` imprime `path\tbranch\tstatus` (`ok`/`session`/
   `invalid`) desde el cache (si no hay cache, hace un scan).
10. `/quit` vía chat NO mata la app (devuelve la despedida).
11. Sin feature `llama` o sin GGUF: todo funciona en modo determinista
    (router + read-tools), con aviso por stderr.

## 5. G-A7 en detalle (tu trabajo)

Del doc 20 §2.1/§3.2/§7: reemplazar el placeholder por la UI completa
de 4 zonas.

- **Top bar:** logo/wormark Cortex, selector de modelo (los GGUF de
  `~/.cache/cortex/models/` — `cortex_brain::paths`), botón settings.
- **Sidebar (izquierda):** proyectos de `list_projects` (nombre,
  rama, indicador de sesión activa), click selecciona, botón
  refrescar (`refresh_projects`). El `config.yaml` corrupto se
  muestra con `valid_config: false` (decisión del dueño: no esconder).
- **Centro:** chat del proyecto seleccionado. Invoca `chat_turn`
  (command Tauri) — **ojo**: hoy `chat_turn` es batch (devuelve el
  `ChatTurn` completo); para streaming en vivo el frontend necesita
  escuchar por eventos de Tauri o por el socket — **decisión a cerrar
  con el dueño** (ver §7). Reconciliar: chunks crudos en vivo, el
  `done` manda (texto procesado con outputs de tools).
- **Status bar (abajo):** `MarkRam` (Idle/WeakAwake/Awake, portar de
  `cortex-companion::hud_brand`), proyectos cargados
  (`loaded_projects()`), ticker que llame `reap_idle()` (el unload
  por idle necesita ese tick — G-A5 lo dejó preparado).
- **Settings modal:** modelo activo, paths detectados + último scan,
  idle timeout, tema, i18n ES/EN, About (doc 20 §2.3).
- **Criterios de pase (doc 20):** snapshot test de la UI; click flows
  cubiertos. Verificación extra: `npm run build` en `apps/brain-ui`.

### Decisiones a cerrar con el dueño ANTES de implementar G-A7

1. **Streaming hacia el frontend:** ¿el frontend consume el socket
   directamente (WebSocket o fetch por chunks), o se agregan eventos
   de Tauri (`app.emit` desde el engine → `listen` en React)? El
   `chat_turn` actual es batch. Sugerencia: eventos Tauri
   (`emit`/`listen`) con `request_id` como clave — evita exponer el
   socket al WebView.
2. **`MarkRam` en la UI:** ¿se porta `LiquidRam`/`MarkAnimation` del
   companion o se hace un port liviano solo con los 3 estados y la
   respiración del doc 17 §10?
3. **Idioma de la UI:** ¿reusar `cortex_brain::i18n` desde Rust y
   pasarle strings al frontend, o i18n del lado TS con los mismos
   textos? Sugerencia: TS con espejo de los textos (el engine ya
   fija el idioma del chrome por proyecto).

## 6. Arquitectura técnica que necesitás saber

- **`BrainEngine`** (chat.rs): `Mutex<HashMap<String, TurnState>>` +
  `idle_timeout` + `factory: fn() -> Option<BoxBackend>`.
  `TurnState { backend: Box<dyn LlmBackend + Send>, last_used }`.
  Los turnos están serializados por el lock: dentro se hace chdir al
  proyecto (las tools del motor shell-out al CLI `cortex` heredando
  CWD) y se fija el i18n global — por eso el lock es obligatorio.
  `ChdirGuard` restaura al salir.
- **Fábrica:** `new()` usa `factory_backend_default` (con feature
  `llama` intenta el GGUF; sin feature devuelve None ⇒ determinista).
  `with_factory(idle, factory)` existe para que los tests inyecten
  `|| None` y **nunca carguen el GGUF real**.
- **`SharedEngine = Arc<BrainEngine>`**: un único engine registrado
  con `app.manage()` y clonado para el thread del server IPC. Estado
  conversacional compartido entre ambos caminos.
- **IPC (G-A2/G-A4/G-A6):** JSON-lines por Unix socket. Un request
  por conexión: cliente manda `{"type":"query","project","text",
  "request_id"}`; server responde 1+ `chunk` (crudo) y un `done`
  (texto procesado + tool_calls) o `error`, y cierra. Windows: stub
  (`NotSupported`) hasta G-A2.1.
- **Tool protocol:** `procesar_respuesta_modelo` (motor) con
  `aprobar` = tier Read ⇒ true (auto-ejecuta), SafeAction ⇒ false
  (denegada, reportada en `tool_calls`). La salida de las read-tools
  viaja SOLO en `done.text` — los chunks son crudos.
- **Feature llama del app:** `llama = ["cortex-brain/llama"]`.
  Compila llama.cpp vía cmake (check: ~2m). `LlamaChatBackend` ES
  `Send` (backend/modelo Send, no Sync): encaja en
  `Box<dyn LlmBackend + Send>` del engine compartido.
- **El trait `LlmBackend` del motor ahora es dyn-compatible con
  streaming:** `generate_streaming(..., on_piece: &mut dyn FnMut(&str))`
  — el `&mut dyn` es deliberado (un `impl Fn` lo rompía).

## 7. Decisiones ya cerradas con el dueño (son leyes, no las reabra)

1. **Binario unificado** `cortex-brain` con roles por flags (doc 20
   §12.1 opción C) — implementado.
2. **G-A3:** raíces del scan = solo `$HOME` v1 (fallback
   `USERPROFILE`); `config.yaml` corrupto se lista con
   `valid_config: false` (no se esconde); sesión activa leyendo la
   convención de archivos (`.cortex/sessions/active.txt` + `<id>.yaml`
   existe) en vez de depender de `cortex-app` (arrastra ONNX); el doc
   21 viaja en los commits de la obra.
3. **G-A4:** read-tools auto-ejecutadas sin confirmación; SafeAction
   denegada + reportada (modal en G-A7+); chdir al proyecto bajo el
   lock del engine; `/quit` no mata la app.
4. **G-A5:** idle unload en el gate (90s, `reap_idle()` público; el
   ticker llega con la UI); smoke real del modelo corrido con éxito.
5. **G-A6:** autorización a tocar `cortex-brain` mínimamente
   (generate_streaming + override llama); streaming crudo en chunks +
   `done` autoritativo; CLI imprime chunks en vivo.
6. **Estilo:** sin ceremonia TDD estricta; tests enfocados; 3 gates de
   verificación siempre.

## 8. Convenciones que respetamos

- **Commits atómicos por gate**, suite verde antes de commitear.
- **Conventional Commits en español.** Ejemplos reales: `app(tauri):
  scan recursivo de proyectos con cache (G-A3)`, `brain(chat):
  streaming de tokens + IPC chunks (G-A6)`.
- **Gates de verificación:** `cargo test -p cortex-brain-app`,
  `cargo clippy -p cortex-brain-app --all-targets -- -D warnings`,
  `cargo fmt -p cortex-brain-app --check`. Si tocás el motor: ídem
  `-p cortex-brain` (+ companion si el trait cambia).
- **`#![allow(unsafe_code)]`** en `cortex-brain-app` (solo para
  `set_var` en tests); el motor mantiene `forbid`.
- **Tests con lock de filesystem/env** que se serializan
  (`ipc::tests::ENV_LOCK` pub(crate) — compartilo si tu test toca
  `XDG_RUNTIME_DIR` o `CORTEX_BIN`; `PROJECTS_LOCK` en projects.rs
  para `$HOME`; `chat::tests::ENV_LOCK` para `CORTEX_BIN`).
- **i18n ES/EN** (motor: `cortex_brain::i18n`; UI: decidir en G-A7).
- **Catppuccin Mocha** en la UI (`apps/brain-ui/tailwind.config.js`
  ya configurado). **npm, no pnpm.**
- **Paridad por construcción:** delegar en servicios existentes del
  motor; no reimplementar.
- **Snake_case** archivos, **PascalCase** structs/enums.
- **Cero deps nuevas al lock** sin necesidad (todas las actuales
  fueron edges de workspace: serde_yaml, sha2, cortex-brain, libc).
- **Doc 21 se actualiza y commitea con cada gate** (§ por gate con
  evidencia + próximo gate anotado).

## 9. Lecciones aprendidas (errores que ya cometimos — no los repitas)

Del handoff anterior (siguen vigentes):

1. **Tauri corre `beforeBuildCommand` desde `rust/crates/`**, no desde
   el crate. Rutas en `tauri.conf.json`: `frontendDist:
   ../../../apps/brain-ui/dist`, `npm --prefix ../../apps/brain-ui`.
   No las cambies sin entender esto.
2. **Tauri requiere íconos RGBA** (no RGB).
3. **pnpm rompe** por supply-chain estricto; usar `npm`.
4. **Tests con `set_var`** requieren `unsafe` (Rust 1.80+) y Mutex para
   serializarse (patrón `lock().unwrap_or_else(|e| e.into_inner())`).
5. Tests de socket: wrappear `BufReader::new` **antes** del barrier.
6. **`cargo fmt -p <crate> && cargo fmt -p <crate> --check`** (no fmt
   global del workspace).

Nuevas de esta sesión:

7. **Commands async de Tauri 2 exigen futures `Send + 'static`**: un
   `tauri::State<'_, T>` prestado NO compila el tag y el return
   necesita `Serialize` (IpcResponse = blanket de Serialize). Patrón
   que funciona: `app.manage(Arc<T>)` en setup + resolver con
   `app.state::<T>()` DENTRO del command async, tomando `AppHandle`
   como parámetro.
8. **Callbacks de trait: `&mut dyn FnMut(&str)`, nunca `impl FnMut`
   si el trait se usa como `dyn`** (object safety). Y en los
   call-sites de closures HRTB anotá el tipo: `&mut |p: &str| ...`.
9. **Los tests del app inyectan fábrica `|| None`** para que la suite
   con `--features llama` NUNCA cargue el GGUF real (rápida y
   determinista). El camino llama real se cubre con el smoke
   `#[ignore]`: `cargo test -p cortex-brain-app --features llama --
   --ignored` (el GGUF ya está en `~/.cache/cortex/models/`).
10. **El contrato IPC post G-A6: SIEMPRE hay ≥1 chunk antes del
    done** (backends batch emiten todo en una pieza — default del
    trait). Los clientes reconcilian con el done; no asumas que el
    primer mensaje es el done.
11. **`git add <archivo>` arrastra TODO el working tree del archivo**,
    incluido WIP ajeno. Si el archivo tiene hunks de otros, stageá
    selectivo: filtrá los hunks del diff y `git apply --cached` el
    parche filtrado (y verificá con `git show HEAD -- <archivo>`)
    — en G-A6 hubo que amendar por esto.
12. **El árbol tiene WIP del dueño sin commitear** (banner
    Compact→Mark en `cortex-brain/src/chat.rs`, cambios en
    companion/tui/branding, varios untracked). NO lo incluyas en tus
    commits y NO lo reviertas.
13. **`git show`/`git log` arrancan con metadata del commit**: si
    extraés hunks para parches, usá `git diff HEAD~1 HEAD -- archivo`
    (sin metadata) o fallará el `git apply`.
14. **El smoke del modelo real es viable sin DISPLAY** (test ignorado
    en proceso): GGUF carga en ~0.5-0.7s en SSD, turno completo ~5s.

## 10. WIP y estado del árbol (a la fecha de este handoff)

- **`rust/crates/cortex-brain/src/chat.rs`:** WIP del dueño sin
  commitear — banner `Compact` → `Mark` (quedó FUERA del commit
  G-A6 deliberadamente, vía staging selectivo). No lo commitees ni lo
  reviertas sin preguntar.
- Cambios sin commitear del dueño en `cortex-companion`,
  `cortex-tui`, `cortex-branding` y varios untracked (`docs/herdr/`,
  assets, etc.). **Nunca los agregues a tus commits** — stageá
  siempre por archivo exacto.
- `docs/transformacion/19-...` sigue untracked (21 ya está commiteado
  desde G-A3). `handoffs/` es untracked.
- Tests al cierre de G-A6: motor **69/69**, app **31/31** (29 lib + 2
  smoke), companion **137**. Clippy/fmt rc 0 en todos.

## 11. Workflow recomendado para vos

1. Leé el doc 21 completo (§11-§16 son los últimos 4 gates, con las
   decisiones y hallazgos), después doc 20 (§2 producto y §7 gates) y
   `docs/herdr/README.md` (G-A7 es UI).
2. Leé `apps/brain-ui/src/App.tsx`, `tailwind.config.js` y el
   `tauri.conf.json`; y en el backend, `chat.rs` + `lib.rs` (son los
   que vas a consumir).
3. Cerrá con el dueño las 3 decisiones de G-A7 (§5 de este handoff).
4. Presentale el plan del commit (alcance, archivos, criterios). Él
   aprueba o ajusta.
5. Implementá. Corré los 3 gates de verificación + `npm run build`
   (desde `apps/brain-ui/`).
6. Commit con mensaje siguiendo la convención.
7. Avisá al cierre y armamos G-A8.

## 12. Resumen ejecutivo (si solo leés esto)

- Cortex Brain = app de escritorio Tauri (Obra 20) para el experto
  local LFM2.5. Binario único `cortex-brain` con roles por flags.
- **G-A1 a G-A6 mergeados** (último: `1c72443`): scaffold, IPC,
  scan+cache de proyectos, chat in-process con el motor, modelo real
  con feature `llama`, streaming por IPC. Todo con suite verde y
  smoke real del modelo verificado.
- **Tu trabajo es G-A7: la UI completa** (sidebar/top bar/chat/status
  bar/settings). El backend ya expone todo lo que la UI necesita
  (commands + chunks + reap) — te falta decidir el transporte del
  streaming hacia React (§5).
- **3 decisiones de G-A7** para cerrar con el dueño antes de tocar
  código (§5). Presentale el plan antes de implementar.
- Si te trabás: doc 21 (más concreto), después el código de
  `chat.rs`/`lib.rs` (lo más reciente).
