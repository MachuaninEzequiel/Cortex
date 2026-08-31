# 20 — Cortex Brain App: el experto local como aplicación

> Estado: PROPUESTA — pendiente de aceptación por el dueño.
> Origen: realineamiento del scope original (Obra 19 / G-L1) tras la
> decisión de imitar el patrón de Handy. **Esta propuesta reemplaza
> el modelo de "subcomando CLI `cortex brain *`" del doc 19**; el
> trabajo de C-L1.1 y C-L1.2 ya mergeado se reutiliza tal cual.
>
> Rama `feature/transformacion-2026-08`, commits locales, sin push.

---

## 0. Por qué este documento

El doc 19 proponía que el motor Liquid LFM2.5 se expusiera como
subcomandos del CLI nativo (`cortex brain install`, `cortex brain
status`, etc.). Esa idea queda **superada**: lo que tiene sentido hoy
es una **aplicación de escritorio** dedicada al motor, análoga a
[cjpais/Handy](https://github.com/cjpais/Handy) (speech-to-text local
con descarga de modelos, ventana propia, modelo solo en RAM cuando
se usa).

El motor (Liquid LFM2.5 + protocolo TOOL + streaming + logo vivo) no
cambia. Lo que cambia es la **superficie** que lo ofrece al usuario.

---

## 1. Qué es Handy (referencia) y qué patrón tomamos

Handy NO es un chat con LLM: es **speech-to-text offline** (Whisper /
Parakeet). El patrón que nos sirve, NO el producto:

| Patrón Handy | Aplicación a Cortex Brain |
|---|---|
| App de escritorio con ventana propia (Tauri: Rust + React + Tailwind) | Idéntico: Tauri, Rust backend, React frontend, Tailwind |
| Lista modelos disponibles + descargar más desde la UI | Lista de modelos GGUF elegibles (LFM2.5-Q4_K_M, LFM2.5-Q8_0, Qwen3-1.7B, Gemma-3-1B) + botón "Descargar" con progreso |
| Modelo solo en RAM durante la transcripción | Liquid solo en RAM durante la consulta al brain (igual que ya hace el Companion) |
| Historial de transcripciones | Historial de chats del brain por proyecto |
| Settings globales (shortcut, modelo activo, idioma) | Settings globales (modelo activo, path de proyectos, theme) |
| Single-instance + IPC por socket (un binario, varios "clientes" vía flags) | Idéntico: `cortex-brain` corre una vez; una segunda invocación manda consulta al primero |
| Cross-platform Windows/macOS/Linux | Idéntico (target oficial macOS+Linux, tier-2 Windows) |
| UI simple y limpia, sin onboarding ni tutoriales | Idéntico: cero tutorial, todo al alcance del click |

Lo que **NO** tomamos:
- El atajo de teclado global (no aplica: Brain no transcribe, no escribe en otro input).
- El motor de audio (VAD, cpal, rubato). Cero relevancia.

---

## 2. Producto: qué ve el usuario

### 2.1 Ventana principal (4 zonas, layout fijo)

```
┌──────────────────────────────────────────────────────────────────┐
│ [ CORTEX BRAIN ]              [ modelo: LFM2.5-Q4_K_M ▾ ] [⚙]  │  ← top bar
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                  │
│  PROYECTOS   │   [chat del proyecto seleccionado]               │
│              │                                                  │
│  ▸ acme-api  │   ──────────────────────────────────────────     │
│  ▸ webgraph  │   yo: cómo está la sesión?                       │
│  ▸ cortex    │                                                  │
│  ▸ docs      │   🧠: sesión SES-42 activa, modo: composed,      │
│  ──────      │        fase: implement, 3 checkpoints OK.        │
│  + agregar   │                                                  │
│              │   ──────────────────────────────────────────     │
│              │   [ escribí tu pregunta ................ ]   [↵] │
│              │                                                  │
├──────────────┼──────────────────────────────────────────────────┤
│ [en RAM: 0 MB] [proyectos: 4] [sesiones activas: 1] [● idle]  │  ← status bar
└──────────────────────────────────────────────────────────────────┘
```

- **Top bar:** logo, selector de modelo (dropdown con los disponibles), botón settings.
- **Sidebar (izquierda):** lista de proyectos Cortex detectados en la máquina. Click selecciona. Cada item muestra: nombre, rama actual, indicador de sesión activa.
- **Centro:** chat del proyecto seleccionado. Input abajo. Historial scrollable arriba.
- **Status bar (abajo):** uso de RAM del modelo, contadores, indicador de estado del modelo (idle/awake — el mismo `MarkRam` que ya existe).

### 2.2 Estados del modelo (logo + status bar)

Idénticos a los que ya implementamos en `cortex-companion` (D7 del doc 17):

- **Idle** — modelo NO en RAM. Logo silencioso, status bar gris.
- **Awake** — modelo cargado, respondiendo. Logo con tono pleno, status bar verde menta.
- **WeakAwake** — entre consultas, modelo todavía en RAM (todavía no se descargó por el timeout). Logo con tono intermedio.

Transición: la primera pregunta del proyecto activo → load → Awake. Idle > 90s (configurable) → unload → Idle. **Mismo `LiquidRam` + `MarkRam` del Companion.**

### 2.3 Settings screen (modal o panel)

- **Modelo activo:** dropdown con los GGUF disponibles (los de `~/.cache/cortex/models/`). Botón "Descargar más" abre la lista de modelos soportados.
- **Proyectos:** mostrar los paths detectados, permitir agregar/eliminar manualmente, ver cuándo fue el último scan.
- **Idle timeout:** segundos antes de descargar el modelo (default 90s).
- **Tema:** oscuro/claro, accent color (menta).
- **i18n:** ES/EN.
- **About:** versión, link al repo, doc 17.

### 2.4 Descarga de modelos (UX)

- Botón "Descargar modelo" en settings → modal con lista de modelos disponibles (los del catálogo de doc 19 §6.1, fuera de alcance para v1 pero presente para v1.1).
- Click en uno → barra de progreso (mismo `DownloadProgress` que ya existe).
- Una vez descargado, sha256 validado y sidecar escrito, aparece en el selector.
- Si ya está descargado, botón "Re-descargar" para forzar.

### 2.5 Acciones del motor (TOOL protocol, sin reinventar)

El brain ya tiene 7 tools (memory.search, docs.related, cortex.health, vault.stats, session.current, webgraph.serve, actions.propose). El chat las usa internas; las **mutaciones** se muestran como propuesta con botón [Ejecutar] (patrón ya del Companion, B8).

En esta app, el botón [Ejecutar] abre un **modal de aprobación** (mismo `run_guarded` que el Companion) con el comando CLI exacto a correr. Sin mutación silenciosa.

---

## 3. Arquitectura (3 procesos / 1 binario + IPC)

### 3.1 Binario único: `cortex-brain`

Tres roles en el mismo binario, decidido por flags:

| Flag | Rol | Comportamiento |
|---|---|---|
| (sin flag) o `--app` | **GUI principal** | Inicia Tauri, abre ventana. Si ya hay instancia, manda foco via IPC. |
| `--query "<texto>" --project <path>` | **Cliente CLI** | Conecta al socket, manda query, imprime respuesta, sale. Patrón de Handy con `--toggle-transcription`. |
| `--projects-list` | **Cliente inspección** | Lista proyectos detectados sin abrir GUI. |

Single-instance enforced con `socket Unix` o named pipe en `$XDG_RUNTIME_DIR/cortex-brain.sock` (Linux/macOS) y `\\.\pipe\cortex-brain` (Windows).

### 3.2 Layout del workspace (lo que se agrega al repo)

```
rust/crates/
├── cortex-brain/             ← EXISTENTE, se REUTILIZA (paths, download, chat, llama, tools, i18n, router, window)
├── cortex-brain-app/         ← NUEVO crate: backend Tauri de la GUI
│   ├── src/
│   │   ├── lib.rs
│   │   ├── ipc.rs            ← servidor de socket + cliente
│   │   ├── projects.rs       ← scan recursivo + caché
│   │   ├── tauri_commands.rs ← commands que el frontend React invoca
│   │   └── state.rs          ← estado del proceso (modelo activo, proyectos, etc.)
│   ├── tauri.conf.json
│   └── tests/
└── apps/
    └── brain-ui/             ← NUEVO: frontend React + Vite + Tailwind
        ├── package.json
        ├── vite.config.ts
        ├── tailwind.config.js
        ├── src/
        │   ├── main.tsx
        │   ├── App.tsx
        │   ├── components/
        │   │   ├── ProjectList.tsx
        │   │   ├── Chat.tsx
        │   │   ├── TopBar.tsx
        │   │   ├── StatusBar.tsx
        │   │   ├── SettingsModal.tsx
        │   │   └── ModelDownload.tsx
        │   ├── hooks/
        │   │   ├── useTauri.ts        ← wrapper de los commands
        │   │   └── useChat.ts
        │   ├── state/                  ← zustand o context
        │   └── types.ts                ← espejo de los tipos Rust
        └── tests/
```

### 3.3 Por qué Tauri y no egui/iced (decisión del dueño, ya tomada)

- Handy lo usa → proof of concept validado por miles de usuarios.
- Tauri compila el binario Rust → produce un binario nativo con WebView embebido según OS (WebKit en macOS, WebView2 en Windows, webkit2gtk en Linux).
- El frontend React es separado y testeable por su cuenta.
- Bundle: ~5-10 MB, vs 50-150 MB de Electron. **Cumple "lo más liviana posible"** en el sentido de impacto en RAM/disco.
- Reutiliza crates de Cortex sin reescribir nada (la lógica del motor sigue en `cortex-brain`).
- Dependencias nuevas al lock: `tauri`, `tauri-build`, `serde_json` (ya está), `tokio` (ya está).

### 3.4 IPC: contrato mínimo

**Servidor (instancia GUI) escucha en:**
- Linux: `$XDG_RUNTIME_DIR/cortex-brain.sock` (fallback `/tmp/cortex-brain-<uid>.sock`)
- macOS: `~/Library/Application Support/cortex/brain.sock` (o temporal)
- Windows: `\\.\pipe\cortex-brain`

**Protocolo:** JSON lines (NDJSON). Un mensaje por línea, ack inmediato.

Request del cliente:
```json
{"type":"query","project":"/path/to/proj","text":"¿cómo está la sesión?","request_id":"r1"}
```

Response del servidor:
```json
{"type":"chunk","text":"sesión ","request_id":"r1"}
{"type":"chunk","text":"SES-42 activa...","request_id":"r1"}
{"type":"done","full_text":"...","tool_calls":[{"tool":"memory.search","args":"..."}],"request_id":"r1"}
{"type":"error","message":"...","request_id":"r1"}
```

**Lo que se reutiliza del motor ya hecho:**
- `cortex_brain::chat::LlmBackend` (trait)
- `cortex_brain::chat::procesar_respuesta_modelo` (protocolo TOOL)
- `cortex_brain::download::{ModelSource, HttpSource, LocalSource}` (descarga de modelos)
- `cortex_brain::paths` (rutas del GGUF)
- `cortex_brain::i18n` (textos ES/EN)

---

## 4. Detección de proyectos (scan recursivo)

### 4.1 Algoritmo

- **Trigger:** al abrir la app, en background, con debounce. También `--scan-now` o click "Refrescar" en settings.
- **Raíces de scan:** `$HOME` por default + roots extra configurables en settings (`~/.config/cortex/brain.toml`).
- **Heurística de "es un proyecto Cortex":** el directorio contiene `config.yaml` válido de cortex (parsea) + tiene `.cortex/` (sesiones, specs, etc.).
- **Skip agresivo:** `.git`, `node_modules`, `target`, `.venv`, `__pycache__`, `.cargo`, `dist`, `build`, `.next`, `.gradle`, `vendor`, `Library`, `.cache` (la lista es la misma que un `.gitignore` estándar de dev).
- **Límite de profundidad:** 8 niveles (cubre cualquier repo razonable sin meterse en cosas raras).
- **Cache del resultado:** `~/.cache/cortex/brain-projects.json` con mtime por entrada. Invalidar si el path ya no existe o el `config.yaml` cambió.
- **Detección de "abierto en este instante":** lock en `$HOME/.config/cortex/locks/<hash-proyecto>` con PID adentro. Otra instancia del brain (otro dev, otra terminal) podría chusmear. Para v1 basta con: tiene `.git/HEAD` legible y branch != null.
- **Sesión activa:** `cortex_app::session::SessionService::get_active()` del proyecto. Si hay una, se marca en la UI.

### 4.2 Por qué scan y no registro

- El usuario tiene 5-50 proyectos Cortex en la máquina, posiblemente sin acordarse dónde están.
- Scan una vez + cache = costo despreciable, UX mágica.
- El skip agresivo evita falsos positivos en home con muchos proyectos.
- La cache hace que el segundo arranque sea instantáneo.

---

## 5. Streaming (cambio de scope: era de C-L2, ahora parte de v1)

Como la app es GUI y el chat es interactivo, el streaming es **indispensable**, no nice-to-have. Re-cableamos `LlamaChatBackend::generate_streaming` (que ya definimos en C-L2) para emitir chunks por el IPC al frontend React, que los va rendereando con un pequeño efecto typewriter (un caracter cada ~20ms para que no flashee).

---

## 6. Cambios de scope vs doc 19

| Doc 19 decía | Doc 20 (este) dice |
|---|---|
| `cortex brain install/status/path` como subcomandos del CLI `cortex` | Funcionalidad equivalente pero expuesta como botón/modal en la GUI |
| `cortex brain` binario CLI standalone para chatear con Liquid sobre un proyecto puntual | Reemplazado por la GUI; el CLI queda como `--query` para power users (punto 3.1) |
| `cortex-companion` (Herdr) sigue siendo la superficie principal en terminal | `cortex-companion` **no se toca** (queda para el flujo de Herdr). Esta es una app **separada y complementaria** |
| Doc 19 §3 (streaming) era "Trabajo 2" | Pasa a v1, no se puede postergar |
| Doc 19 §4 (respiración del logo) era "Trabajo 3" | Sigue igual, ahora visible en la top bar de la GUI |
| Descarga de un modelo: flujo CLI | Descarga: botón en GUI, mismo `download::HttpSource` por debajo |

**Lo que se REUTILIZA del trabajo C-L1 ya mergeado (commits `0d882ab`, `ccc2c39`, `8e1f2b9`):**
- `cortex_brain::paths` (rutas del GGUF) — **se usa tal cual**.
- `cortex_brain::download::{ModelSource, HttpSource, LocalSource}` — **se usa tal cual en el IPC server**.
- `DownloadError` se mapea a mensajes de UI via i18n.

**Lo que se DESCARTABA del doc 19 (al reemplazarlo con esta app):**
- §2.10 (CLI `cortex brain install` con subcomandos) → reemplazado por la GUI. El flag `--projects-list` y `--query` del binario único son el subrogado mínimo.
- §6.1 fuera de alcance sigue vigente (no multi-modelo en v1, no override env var, etc.) — se mantiene como simplificación inicial.

---

## 7. Plan de implementación (gates)

Estilo Obra 07: un commit por gate, cada uno con su suite verde.

| Gate | Alcance | Criterio de pase |
|---|---|---|
| G-A1 | **Scaffolding Tauri**: crate `cortex-brain-app` con `tauri.conf.json` mínimo; hello-world React con Vite; binario arranca, ventana se abre, vacío. | `cargo tauri dev` abre ventana; `cargo build -p cortex-brain-app` rc 0. |
| G-A2 | **IPC esqueleto**: socket + JSON-lines server; `--query` flag del binario manda y recibe; el server hace echo por ahora. | Test: lanzar binario en background, mandar query, recibir respuesta. Sin modelo aún. |
| G-A3 | **Scan de proyectos**: módulo `cortex-brain-app::projects` con scan recursivo + cache; command Tauri `list_projects` retorna JSON. | Test: fixture con 3 proyectos, scan los encuentra; cache en segundo run es instantáneo. |
| G-A4 | **Chat in-process por proyecto**: cuando seleccionás un proyecto en la UI, el chat usa `cortex-brain` con el path del proyecto como `--project-root`. Sin IPC aún: todo in-process. | Test: integración end-to-end con backend `ScriptedBackend` (sin modelo). |
| G-A5 | **Integración Liquid real**: con `--features llama` + GGUF instalado, el chat usa `LlamaChatBackend` con load/unload. | Smoke: arrancar, elegir proyecto, hacer pregunta, recibir respuesta. |
| G-A6 | **Streaming por IPC**: el `LlamaChatBackend::generate_streaming` emite chunks, el IPC server los manda, el frontend los renderea. | Test: la respuesta del modelo aparece incrementalmente, no de golpe. |
| G-A7 | **UI completa**: top bar, sidebar, chat, status bar, settings modal. Todo conectado. | Snapshot test de la UI; click flows cubiertos. |
| G-A8 | **Descarga de modelos en UI**: botón "Descargar modelo" usa `HttpSource` por debajo, muestra progreso, persiste sha256. | Test: mock HTTP server, verifica flujo end-to-end. |
| G-A9 | **Single-instance + IPC cliente**: `cortex-brain --query` (cuando hay GUI abierta) manda al server y sale. | Test: dos invocaciones, una sola carga de modelo. |
| G-A10 | **Status bar con MarkRam**: indicador live del estado del modelo (Idle/WeakAwake/Awake). | Test: cambio de estado visible en UI. |

---

## 8. Criterio de salida de v1

1. La app abre con `cortex-brain` (sin args). Ventana se muestra.
2. La sidebar lista al menos 1 proyecto detectado (con fixture, en CI: 1 proyecto hardcoded).
3. Click en un proyecto → chat con el engine en modo determinista (sin GGUF) o real (con `--features llama` + GGUF).
4. La respuesta aparece **token a token** (streaming), no de golpe.
5. El modelo se descarga de RAM al pasar 90s sin consultas.
6. Botón "Descargar modelo" en settings baja `LFM2.5-1.2B-Instruct-Q4_K_M.gguf` con sha256 validado.
7. `cortex-brain --query "¿cómo está la sesión?" --project /path/proj` (con GUI abierta) recibe respuesta en stdout.
8. App cross-platform: compila y abre ventana en **Windows, macOS y Linux**. CI corre tests de build en los tres OS.
9. Bundle final: binario < 15 MB, RSS en idle < 30 MB (sin modelo), < 200 MB con modelo cargado.
10. `cargo test --workspace` verde, clippy limpio, fmt OK.

---

## 9. Fuera de alcance de v1 (anotado, no se hace)

Por decisión del dueño (2026-08-31):

- ❌ Multi-modelo real (sigue siendo LFM2.5-Q4_K_M por default; los otros quedan como "futuro" en el dropdown).
- ❌ Override de ruta del modelo por env var (solo settings GUI).
- ❌ Reanudación de descarga con `Range` (siempre full download).
- ❌ Telemetría / métricas de uso de RAM.
- ❌ Historial de chat persistido entre sesiones (se guarda en RAM, se pierde al cerrar).
- ❌ Tema custom (solo el tema por default).
- ❌ Atajo de teclado global.
- ❌ Auto-update de la app.
- ❌ Sincronización de settings entre máquinas.
- ❌ Login / cuenta / nube (sigue 100% local).
- ❌ Multi-ventana.
- ❌ Notificaciones del sistema cuando el modelo termina de generar.
- ~~❌ Soporte de Windows como target oficial (tier-2; el código se compila pero no se testea en CI).~~ **Decisión revertida: Windows es target oficial de v1.**

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Tauri agrega un bundle grande al repo (frontend compilado) | Frontend compilado en `apps/brain-ui/dist/`, ignorado por git (igual que cualquier build artifact). Solo fuentes TypeScript en repo. |
| El scan recursivo tarda en HOME grande con muchos archivos | Skip agresivo + cache + opción de cancelar; scan corre en background, no bloquea la UI. |
| El modelo GGUF no carga en máquinas con poca RAM | Verificación previa con `sysinfo` o crate equivalente; mensaje claro "necesitas al menos 2 GB libres". |
| El IPC socket tiene path collisions en multi-user | Usar `$XDG_RUNTIME_DIR` con UID; tests con path custom. |
| Tauri requiere WebView2 (Windows) que no viene preinstalado | Documentar en INSTALL.md; ofrecer bundle de WebView2 fallback. |
| `cargo tauri dev` no anda en máquinas del dev sin toolchain web | Documentar prerrequisitos (Node 20+, npm/pnpm). |
| El streaming por IPC genera muchos mensajes chicos | Batching: acumular chunks durante 16ms (~60fps) y mandar como un solo mensaje. |
| `cortex-brain` binario se vuelve muy grande por LLM incluido | Es un binario: el modelo NO se linkea, se carga desde archivo en runtime. El binario solo carga `llama-cpp-2` (la lib) que es ~5 MB. |
| Reusar `cortex-companion` produce conflicto de scope | NO se reusa. `cortex-brain-app` es un crate separado, solo importa `cortex-brain` (la lib de motor). |
| El dueño cambia de idea sobre Tauri | egui/iced es un swap factible: la lógica de motor está en `cortex-brain` (no Tauri), solo cambia el shell. El IPC + scan + chat se mantienen. |

---

## 11. Relación con el resto de las obras

| Obra | Cómo se relaciona |
|---|---|
| Doc 19 (Liquid: descarga, streaming, vida visual) | **Reemplazado** en scope de producto por este doc 20. La parte técnica (C-L1.x, descarga, sha256) se mantiene y se reutiliza. |
| Doc 17 (Producto: experto al lado) | El producto activo sigue siendo el Companion en Herdr. La app de este doc 20 es **complementaria**: corre standalone, no requiere Herdr ni terminal. |
| Obra 08 (Companion Herdr) | **No se toca.** El Companion queda como está. La app de este doc 20 es una superficie nueva. |
| `cortex-brain` (lib) | Es la base. Se REUTILIZA entera. C-L1.1 y C-L1.2 ya mergeados entran al stack tal cual. |
| `cortex-cli` (CLI) | No se toca. El subcomando `cortex brain *` del doc 19 queda descartado; el equivalente vive en la GUI. |
| `cortex-companion` (Herdr HUD) | No se toca. Convive con esta app. |

---

## 12. Preguntas abiertas (a cerrar antes de C-L1.3)

Antes de implementar, el dueño debe pronunciarse sobre:

1. **Nombre del binario y de la app:** `cortex-brain-app`? `cortex-brain` (mismo nombre que el binario CLI actual → conflicto)? `Cortex Brain`? Sugiero `cortex-brain` para el binario (mismo que ya existe) y el GUI es la "GUI" del mismo binario. La lib es `cortex_brain`. El crate Tauri es `cortex-brain-app`. **Decisión del dueño.**

2. **Nombre del frontend:** `apps/brain-ui/` o `apps/cortex-brain-ui/`? Sugiero `apps/brain-ui/` (paralelo al crate `cortex-brain`).

3. **Target oficial Windows:** v1 no testea Windows. ¿OK?

4. **Distribución:** ¿querés que v1 se distribuya como binario precompilado (release workflow en GH Actions), o alcanza con `cargo install --path rust/crates/cortex-brain-app`? Sugiero empezar con `cargo install` y dejar el packaging para v1.1.

5. **Re-nombrar el binario CLI actual `cortex-brain`:** choca con el GUI. Opciones:
   - (a) Renombrar el CLI actual a `cortex-brain-cli`, el GUI es `cortex-brain` (default).
   - (b) Mantener `cortex-brain` como CLI y crear `cortex-brain-gui` para el GUI.
   - (c) Fusionar: un solo binario `cortex-brain`, decide según flags (`--app` default, `--query` cliente).
   - **Mi recomendación: (c).** Es lo más limpio, y los flags determinan el rol. El CLI standalone queda accesible con `--query` (ya plan arriba).

---

## 13. Próximo paso (si se aprueba)

1. Crear crate `rust/crates/cortex-brain-app/` con scaffolding Tauri.
2. Crear `apps/brain-ui/` con Vite + React + Tailwind.
3. **G-A1** como primer commit: "app opens, shows empty window".
4. Iterar gate por gate (G-A2, G-A3, ..., G-A10).

Si esta propuesta te cierra, paso a implementarla gate por gate como hicimos con C-L1. Si algo no te cierra, lo iteramos acá antes de tocar código.
