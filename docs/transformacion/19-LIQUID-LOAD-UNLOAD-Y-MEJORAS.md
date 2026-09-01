# 19 — Liquid LFM2.5: descarga, streaming y vida visual del motor

> Estado: ESPECIFICACIÓN DE TRABAJO — pendiente de implementar.
> Origen: deep-review del motor local de Liquid (Obra 06 / 08) + decisión
> de foco del dueño (2026-08-31). Rama `feature/transformacion-2026-08`,
> commits locales, sin push.
>
> Reglas de administración documental (mismas que el resto de la serie):
> - Toda tarea ejecutable lleva checkbox `[ ]`; se marca `[x]` cuando se
>   verifica con evidencia.
> - Criterio de entrada: Obra 07 completa + Obra 08 stream B cerrada +
>   modelo Liquid on-demand funcionando en `cortex-companion` (G-B1…G-B6 PASS).
> - Criterio de salida: ver §6.
> - Si una decisión se revisa, se actualiza este archivo; no se decide en
>   chat y se pierde.

---

## 0. Por qué este documento

El motor local de Liquid (LFM2.5-1.2B-Instruct GGUF) está implementado en
`rust/crates/cortex-brain/` y conectado en `rust/crates/cortex-companion/`
como pieza "on-demand" del producto (doc 17 §7.2). El deep-review del
estado del árbol detecta tres brechas concretas que bloquean el uso real
del motor en una máquina nueva:

1. **No existe un comando para bajar el modelo.** El usuario tiene que
   hacerlo a mano (HuggingFace → curl → ruta hardcoded), conocer la
   convención de `~/.cache/cortex/models/` y compilar con `--features
   llama`. Barrera de entrada real.
2. **El streaming de tokens al usuario no está cableado.** El callback
   `on_piece` ya existe en `LlamaChatBackend::generate_raw` pero el
   `main.rs` del binario lo descarta con `| _ | {}`. Resultado: silencio
   durante segundos mientras el modelo piensa.
3. **El logo del HUD no "respira".** Hoy cambia entre 3 tonos discretos
   (`MarkRam::{Idle, WeakAwake, Awake}`); el doc 17 §10 describe una
   respiración continua, no escalonada.

Estas tres cosas son lo único que se ataca en este tramo. Lo demás del
deep-review (override por env var, multi-modelo, telemetría, poda de
historial, etc.) queda descartado por ahora — el dueño lo confirmó.

---

## 1. Lo que YA está hecho (no se toca)

Inventario concreto del estado hoy, como base de lo que se modifica:

| Pieza | Ubicación | Estado |
|---|---|---|
| Trait `LlmBackend` | `cortex-brain/src/chat.rs` | ✅ |
| `DeterministicBackend` (router 1:1, sin modelo) | `cortex-brain/src/chat.rs` | ✅ |
| `ScriptedBackend` (cola, para CI) | `cortex-brain/src/chat.rs` | ✅ |
| `LlamaChatBackend` (real, llama.cpp) | `cortex-brain/src/llama.rs` | ✅ (feature `llama`) |
| Catálogo de 7 tools (read + safe-action) | `cortex-brain/src/tools.rs` | ✅ |
| Router determinista 1:1 del Python | `cortex-brain/src/router.rs` | ✅ |
| Protocolo TOOL con confirmación | `cortex-brain/src/chat.rs` | ✅ |
| i18n ES/EN | `cortex-brain/src/i18n.rs` | ✅ |
| Banner ≤80 cols (Mark + wordmark) | `cortex-brain/src/chat.rs` + `cortex-branding` | ✅ |
| 13 tests spec conductual | `cortex-brain/tests/spec_behavior.rs` | ✅ verde |
| Tests protocolo TOOL con Scripted | `cortex-brain/tests/tool_protocol.rs` | ✅ verde |
| Mapa 1:1 brain → engine en Companion | `cortex-companion/src/brain_panel.rs` | ✅ |
| Liquid on-demand (load/unload) en Companion | `cortex-companion/src/runner.rs` + `app::LiquidRam` | ✅ |
| Logo del HUD con tono por estado RAM | `cortex-companion/src/hud_brand.rs` (`MarkRam`) | ✅ |
| Convención de ruta `~/.cache/cortex/models/LFM2.5-1.2B-Instruct-Q4_K_M.gguf` | `cortex-brain/src/llama.rs::model_path_default` | ✅ |

El callback `on_piece` ya existe en `LlamaChatBackend::generate_raw`
(`llama.rs:108`) — no se reescribe el motor, se cablea lo que ya está.

---

## 2. Trabajo 1 — Comando de descarga/instalación del GGUF

### 2.1 Fuente

- HuggingFace: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`
- Archivo: `LFM2.5-1.2B-Instruct-Q4_K_M.gguf` (~770 MB)
- URL de descarga: `https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF/resolve/main/LFM2.5-1.2B-Instruct-Q4_K_M.gguf`
- Sha256: vive en `LFM2.5-1.2B-Instruct-Q4_K_M.gguf.sha256` al lado del
  binario en el repo de HF. Se valida contra el archivo descargado.

### 2.2 Decisión de crate HTTP

- **`ureq 3.x`**, **opción recomendada y por defecto**.
- Justificación: ya está resuelto en el lock transitivamente (lo trae
  `ort-sys` para descargar binarios de onnxruntime en el primer build
  con `--features onnx`). **Cero paquetes nuevos al workspace**.
- Sync, simple, soporta `Content-Length` para progreso.
- `ureq::Agent` + lectura chunked de 64 KB.
- Alternativas descartadas: `reqwest` (suma cadena pesada), `Command::new("curl")`
  (depende del binario del sistema), `huggingface-hub` (overkill, dep nueva).

### 2.3 Comandos a exponer (familia `cortex brain`)

```
cortex brain install              # baja si no está; idempotente
cortex brain install --force      # re-baja aunque exista; verifica sha
cortex brain install --path <ruta>  # importa un .gguf local a la ubicación default
cortex brain status               # ¿está? ¿versión? ¿tamaño? ¿sha?
cortex brain path                 # imprime la ruta default
```

Convención: viven en `cortex-cli/src/commands/brain_cmd.rs` (módulo
nuevo) y se registran en `dispatch_native` (tabla real de ~27 familias
hoy). Forma consistente con `cortex setup`, `cortex ide`, etc.

### 2.4 Dónde vive el código

Recomendación: **subcomando nuevo en `cortex-cli` + función pública en
`cortex-brain`**.

- `cortex_brain::paths::default_model_dir() -> PathBuf` (movido desde
  `llama.rs::model_path_default` para no requerir el feature `llama` al
  usarla).
- `cortex_brain::paths::default_model_filename() -> &str` (constante).
- `cortex_brain::download::{install, status, import_from}` (módulo
  nuevo, **no requiere el feature `llama`**; ureq no necesita cmake).
- `cortex-cli/src/commands/brain_cmd.rs` arma los clap subcommands y
  delega a `cortex_brain::download::*`.
- `cortex-cli/src/main.rs::dispatch_native` registra `brain` como
  familia nueva (suma 1 entrada a la tabla).

Razón: el CLI es la fachada pública del repo, el brain es la lógica
pura. `cortex_brain::download` no depende de clap ni del runtime del
CLI, así que es testeable en librería.

### 2.5 Validación de integridad (sha256)

- Bajar el `.gguf` y el `.sha256` sidecar en paralelo (con `ureq`).
- Parsear el sha del sidecar (formato HF: `<hash>  <filename>\n` o solo
  el hash; tolerar ambos).
- Verificar con `sha2` (ya está en el workspace: `[workspace.dependencies]
  sha2 = "0.10"`).
- Si falla: borrar el `.partial`, mensaje accionable en i18n, exit 1.
- Persistir el sha en `~/.cache/cortex/models/.sha256` después de una
  instalación exitosa; `install --force` lo usa para detectar
  "ya-tenía-este-archivo" sin re-hashear.

### 2.6 Descarga robusta

- Descargar en `~/.cache/cortex/models/.partial/<nombre>.gguf` (tmp).
- Al terminar OK: `rename` atómico a la ruta final.
- Si el destino ya existe con sha válido: salir con éxito silencioso
  (idempotente).
- Si no hay espacio en disco: `statvfs` (Unix) / `GetDiskFreeSpaceExW`
  (Windows) para chequeo previo; mensaje con cuánto falta.
- Si no hay red: error claro, exit 1, **nunca** simular descarga.
- Reanudación con `Range`: **fuera de alcance** para v1 (siempre
  descarga completa). Queda anotado en §6.

### 2.7 Lock de concurrencia

- Dos procesos pidiendo `install` a la vez: el segundo espera.
- `flock(2)` sobre `~/.cache/cortex/models/.lock` (Unix). En Windows:
  `LockFileEx` (no prioridad para v1; si no se puede, documentar).
- Fallback portable: `OpenOptions::new().create_new(true).open(...).lock()`
  con retry + backoff (1s × 30).

### 2.8 Progreso visible

- TTY: barra `▓▓▓▓░░░░ 50% · 380MB/770MB · 12 MB/s` con `\r` y
  `flush` cada chunk.
- No TTY: log por stderr en `installed=0.50 ratio=0.50 bytes=380MB`.
- Sin progreso falso: si no hay `Content-Length`, no mostrar porcentaje,
  solo bytes transferidos.

### 2.9 i18n

Usar `cortex_brain::i18n` con las funciones nuevas (no romper las
existentes):

- `instalando_gguf(lang, nombre, total_mb)` → "🧠 bajando GGUF: LFM2.5-… (770 MB)".
- `instalacion_ok(lang, ruta, elapsed)` → "✓ GGUF listo en {ruta} ({elapsed})".
- `instalacion_ya_ok(lang, ruta)` → "✓ GGUF ya estaba en {ruta}".
- `error_red(lang, msg)` → "✗ error de red: {msg}".
- `error_sha(lang, esperado, real)` → "✗ sha256 no coincide (esperado {esperado}, real {real})".
- `error_espacio(lang, falta_mb)` → "✗ no hay {falta_mb} MB libres en el disco".
- `error_lock(lang)` → "✗ otra instalación en curso (lock activo)".

### 2.10 Tests

- Unit: `model_dir_crea_si_no_existe`, `parse_sha_sidecar_acepta_dos_formatos`,
  `progress_format_no_tty_no_contiene_escape_ansi`.
- Integración con `ureq` mockeado: trait `ModelSource` con dos impls
  (`HttpSource`, `FileSource` para tests). Tests:
  - instala_ok,
  - ya_existe_idempotente,
  - sha_incorrecto_borra_parcial,
  - red_caida_mensaje_accionable,
  - lock_ocupado_espera_y_termina,
  - import_from_path_local_no_red.

### 2.11 Tareas

- [ ] Mover `model_path_default` a `cortex_brain::paths` (sin feature
      `llama`).
- [ ] Agregar `cortex_brain::download` con `ModelSource` trait +
      `HttpSource` (ureq) + `FileSource` (para tests/import).
- [ ] `install(status)` con sha256, lock, progreso, i18n.
- [ ] `cortex-cli/src/commands/brain_cmd.rs` con los 3 subcomandos.
- [ ] Registrar `brain` en `dispatch_native`.
- [ ] Mensajes i18n nuevos.
- [ ] Suite de tests del módulo `download`.
- [ ] Smoke: `cortex brain install` baja el GGUF real (manual, anotado).

---

## 3. Trabajo 2 — Streaming de tokens al usuario

### 3.1 Estado actual

`LlamaChatBackend::generate_raw` ya tiene `on_piece: impl FnMut(&str)`
(`llama.rs:108`). El binario `cortex-brain/src/main.rs:185` lo invoca
con `| _ | {}` — descarta. Resultado: el usuario espera en silencio
durante segundos.

### 3.2 Diseño de la API (mínimamente invasivo)

**Recomendación:** agregar un método NUEVO al trait `LlmBackend`, no
modificar el existente.

```rust
pub trait LlmBackend {
    fn name(&self) -> &str;

    /// Modo batch: completa la respuesta entera. Se mantiene para
    /// backends que no streamen (Deterministic, Scripted).
    fn generate(&mut self, prompt: &str, tools_help: &str) -> Result<String, String>;

    /// Modo streaming: callback recibe cada fragmento a medida que se
    /// genera. Default = llamar a `generate` y emitir TODO en un solo
    /// callback (compatibilidad hacia atrás).
    fn generate_streaming(
        &mut self,
        prompt: &str,
        tools_help: &str,
        mut on_piece: impl FnMut(&str),
    ) -> Result<String, String> {
        let full = self.generate(prompt, tools_help)?;
        on_piece(&full);
        Ok(full)
    }
}
```

Solo `LlamaChatBackend` override `generate_streaming` para usar el
`on_piece` que ya existe en su `generate_raw`. El resto usa el default.

### 3.3 Binario `cortex-brain` (stdin/stdout)

- Cuando el backend es `LlamaChatBackend`: usar `generate_streaming`,
  `print!` cada piece (sin `\n`), `flush` después.
- Al terminar, newline.
- Cuando hay un protocolo TOOL mid-stream: el modelo emite texto +
  `TOOL: …` + (opcional) más texto. Estrategia:
  - `on_piece` **siempre** va a stdout.
  - Después de EOF, la respuesta completa se parsea con `extraer_tool`
    (ya existe).
  - Si hay TOOL: línea aparte `> TOOL: <name> <args>` visible, prompt
    de confirmación, etc. — todo lo que ya hace `procesar_respuesta_modelo`.
- Para `DeterministicBackend` y `ScriptedBackend`: se sigue usando
  `generate` (modo batch); el streaming no aporta nada ahí.

### 3.4 Companion (panel Brain)

El panel Brain tiene hoy `BrainMsg::Brain(String)` (respuesta entera).
Para streaming, hay dos opciones:

| Opción | Pros | Contras |
|---|---|---|
| **A. `BrainMsg::BrainChunk(String)`** que se concatena al último `BrainMsg::Brain` en un reducer. | Mantiene el modelo de mensajes puros. | Más cambios en el reducer y en `brain_rows`. |
| **B. Append in-place al último `BrainMsg::Brain`** mutable. | Más simple. | Rompe inmutabilidad conceptual del estado (pero el estado ya es mutable por diseño). |

**Recomendación: opción A** (puro, testeable). Cambios concretos:

- `BrainMsg::BrainChunk(String)` nuevo variant.
- En el reducer (donde se aplica `Effect::BrainTurn`): el runtime va
  acumulando chunks hasta que `generate_streaming` retorna; al final
  colapsa los chunks en un solo `BrainMsg::Brain(String)`.
- Alternativa simple: pasar el closure al `run_turn` que escribe
  directamente al estado (igual que `app.liquid.mark_active`).

### 3.5 Tests

- `llama_streaming_invoca_callback_por_parte`: con `LlamaChatBackend`
  mockeado (o un fake que cuente), verificar que el callback se llama
  ≥1 vez.
- `scripted_backend_streaming_default_emite_todo_en_una`: el default
  del trait emite la respuesta completa en un solo callback.
- `brain_panel_chunk_se_concatena_en_mensaje_final`: test del Companion
  verifica que la lista final de mensajes tiene un solo `Brain` con
  el texto entero.
- Spec ya cubierta por `tool_protocol.rs::flujo_completo_*` no se
  rompe (sigue usando `generate` batch).

### 3.6 Tareas

- [ ] Agregar `LlmBackend::generate_streaming` con default que delega a
      `generate`.
- [ ] Override en `LlamaChatBackend` que use `generate_raw` con un
      `on_piece` real.
- [ ] `cortex-brain/src/main.rs`: cuando backend es `Llama`, usar
      `generate_streaming` + `print!` + `flush`.
- [ ] En el Companion: pasar al reducer un canal/closure para chunks,
      o agregar `BrainMsg::BrainChunk` y colapsar al final.
- [ ] Tests de los tres niveles (trait, backend, panel).

---

## 4. Trabajo 3 — Respiración del logo del HUD

### 4.1 Estado actual

`cortex-companion/src/hud_brand.rs` define `MarkRam` con tres estados y
`tone()` aplica un factor discreto:

| Estado | Factor |
|---|---|
| `Idle` | 0.72 |
| `WeakAwake` | 0.88 |
| `Awake` | 1.0 |

El doc 17 §10 pide "respiración/glow" continuo, no escalonado.

### 4.2 Diseño de la animación

Una struct nueva al lado de `MarkRam`:

```rust
pub struct MarkAnimation {
    pub phase: f32,        // [0, 2π)
    pub state: MarkRam,
    pub enabled: bool,     // reduced-motion / NO_COLOR
}

impl MarkAnimation {
    pub fn tick(&mut self, dt: Duration) {
        if !self.enabled { return; }
        let speed = match self.state {
            MarkRam::Idle => 0.13,        // rad/s, ciclo ~48s
            MarkRam::WeakAwake => 0.42,   // ciclo ~15s
            MarkRam::Awake => 0.84,       // ciclo ~7.5s
        };
        self.phase = (self.phase + speed * dt.as_secs_f32())
            .rem_euclid(2.0 * std::f32::consts::PI);
    }

    pub fn breath_factor(&self) -> f32 {
        if !self.enabled {
            return match self.state {
                MarkRam::Idle => 0.72,
                MarkRam::WeakAwake => 0.88,
                MarkRam::Awake => 1.0,
            };
        }
        let pulse = 0.5 + 0.5 * self.phase.sin();          // 0..1
        let base = 0.85 + 0.15 * pulse;                   // 0.85..1.0
        let state_factor = match self.state {
            MarkRam::Idle => 0.75,
            MarkRam::WeakAwake => 0.90,
            MarkRam::Awake => 1.0,
        };
        base * state_factor
    }
}
```

### 4.3 Loop con tick de animación

El runner hoy es bloqueante en `event::read()`. Hay que cambiar a
`event::poll(timeout)` con timeout corto:

```rust
loop {
    // render
    terminal.draw(|f| render(...))?;

    if event::poll(Duration::from_millis(80))? {
        // procesar input
    } else {
        // tick de animación
        state.mark_anim.tick(Duration::from_millis(80));
        // no redraw acá, el `terminal.draw` del próximo loop se encarga
    }
}
```

Cuidado: el presupuesto de render es <50ms hoy. Un tick de 80ms no debe
romper eso. Verificar con `tests/rss_measure.rs` (existente) y un nuevo
test que mida el frame promedio con tick activo.

### 4.4 Reduced motion / accesibilidad

- `NO_COLOR=1` → animación desactivada, tonos discretos.
- `CORTEX_NO_ANIMATION=1` → idem.
- No TTY (modo snapshot) → animación desactivada, primer frame
  capturado en estado `Idle`.
- `prefers-reduced-motion` no aplica (no es GUI); pero la convención de
  respetar `NO_COLOR` ya está en el repo.

```rust
pub fn should_animate() -> bool {
    if std::env::var("NO_COLOR").is_ok() { return false; }
    if std::env::var("CORTEX_NO_ANIMATION").is_ok() { return false; }
    std::io::stdout().is_terminal()
}
```

### 4.5 Integración con el pipeline

- Reemplazar `tone()` en `hud_brand.rs` por uno que use
  `MarkAnimation::breath_factor()` en vez del factor discreto de `MarkRam`.
- Agregar `MarkAnimation` a `AppState` (al lado de `LiquidRam`).
- En `runner.rs::run_app`: inicializar `mark_anim.enabled = should_animate()`,
  y el loop hace `tick(80ms)` en el branch de timeout.
- Cuando `LiquidRam::mark_active()` se llama: sincronizar
  `mark_anim.state = liquid.ram()`. Cuando `mark_idle()`: idem.

### 4.6 Tests

- `breath_factor_idle_nunca_supera_0_78`: en cualquier fase, el
  factor en Idle es ≤ 0.78.
- `breath_factor_awake_llega_a_1`: en algún punto del ciclo, Awake
  llega a 1.0.
- `tick_avanza_fase`: tras 10 ticks de 100ms, la fase creció
  aproximadamente 0.84 * 1.0 (Awake).
- `should_animate_false_con_NO_COLOR`: env `NO_COLOR=1` desactiva.
- `reduced_motion_da_factores_discretos`: con animación off, los
  factores coinciden con los del `MarkRam` actual.

### 4.7 Tareas

- [ ] Agregar `MarkAnimation` a `hud_brand.rs`.
- [ ] `MarkAnimation::tick(dt)` y `breath_factor()`.
- [ ] `should_animate()` helper.
- [ ] `MarkAnimation` en `AppState`, sincronizado con `LiquidRam`.
- [ ] Loop del runner con `event::poll(80ms)` + tick.
- [ ] Reemplazar uso del `tone()` actual en `blit_mark`.
- [ ] Tests del módulo (factor, tick, reduced motion).
- [ ] Verificar presupuesto de render sigue <50ms con animación activa.

---

## 5. Orden de implementación (recomendado)

1. **Trabajo 1 (descarga)** primero. Sin modelo no se puede probar
   streaming ni la respiración en un estado real de carga.
2. **Trabajo 3 (respiración)** segundo. Es visible de inmediato, no
   depende de tener GGUF, y valida el patrón de `event::poll` con
   timeout que después usa el streaming.
3. **Trabajo 2 (streaming)** tercero. Depende de tener el modelo
   cargado y del loop de tick ya en su lugar.

Cada trabajo se cierra con su propio gate (estilo Obra 07):

| Gate | Criterio de pase |
|---|---|
| G-L1 (descarga) | `cortex brain install` baja el GGUF real, sha256 OK, exit 0, tests verdes; con red caída, error claro. |
| G-L2 (respiración) | Frame animado visible (snapshot de 2 frames consecutivos muestra cambio de tono en Awake); reduced-motion off ⇒ estático. |
| G-L3 (streaming) | Binario `cortex-brain --model` emite tokens a stdout uno a uno; tests del trait verdes. |

---

## 6. Criterio de salida (definición de hecho)

Este tramo se considera cerrado cuando se cumple TODO lo siguiente, con
evidencia (comando + salida) en commits separados por gate:

1. `cortex brain install` baja el GGUF desde HuggingFace, valida sha256,
   reporta progreso, es idempotente y maneja errores de red / disco /
   sha mismatch con mensajes accionables.
2. El binario `cortex-brain` con `--model` emite la respuesta token a
   token por stdout; sin `--model` sigue funcionando como hoy
   (determinista).
3. En el Companion, el logo del HUD tiene respiración continua en
   `Awake` y `WeakAwake`, casi imperceptible en `Idle`. Con
   `NO_COLOR=1` o sin TTY, queda en tonos discretos.
4. Suite completa verde: `cargo test -p cortex-brain -p cortex-companion`
   sin warnings nuevos, `cargo clippy --workspace -- -D warnings`
   limpio, `cargo fmt --check` OK.
5. RSS del Companion con animación activa sigue en el rango actual
   (~18 MB) — sin leaks por el tick.
6. Documentación actualizada: `docs/herdr/README.md` menciona el
   comando de instalación, y este doc 19 tiene todas las casillas
   `[x]` con sus respectivos links a commits.

### 6.1 Fuera de alcance (anotado, no se hace)

Por explícita decisión del dueño (2026-08-31):

- Override de ruta por env var (sólo flag `--model`).
- Soporte de múltiples modelos (Q5, Q8, otros).
- Reanudación de descarga con `Range`.
- Validación de la licencia LFM1.0.
- Telemetría de carga / RAM real.
- Historial de chat con poda por tokens.
- Verificación de RAM disponible antes de cargar.
- Prompt copiable REESCRITO por Liquid (doc 17 §6.2 v1.1).
- Soporte macOS cache path (`~/Library/Caches`).
- Fallback a otros modelos (Qwen3-1.7B, Gemma-3-1B).
- Lock en Windows (sólo Unix; documentar la limitación).

---

## 7. Archivos que se tocan (resumen)

| Ámbito | Archivos |
|---|---|
| `cortex-brain` | `src/llama.rs` (mover `model_path_default` a `paths`), `src/paths.rs` (nuevo), `src/download.rs` (nuevo), `src/chat.rs` (`generate_streaming`), `src/i18n.rs` (mensajes nuevos), `src/main.rs` (usar streaming), `Cargo.toml` (ureq), `tests/*.rs` (nuevos tests) |
| `cortex-companion` | `src/hud_brand.rs` (`MarkAnimation`), `src/app.rs` (campo nuevo + sync con LiquidRam), `src/runner.rs` (`event::poll` + tick), `src/brain_panel.rs` (streaming), `tests/*.rs` |
| `cortex-cli` | `src/commands/brain_cmd.rs` (nuevo), `src/main.rs` (registrar `brain` en dispatch_native) |
| Docs | `docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md` (este), `docs/herdr/README.md` (mención) |

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| HF cambia la URL del archivo | URL configurable via `cortex brain install --repo <owner/repo> --file <nombre>` (defensa en profundidad, default al actual). |
| `ureq` no soporta proxy HTTPS | `ureq::Agent::builder().proxy(...)` documentado; v1 sin proxy. |
| Modelo > 1 GB y SSD chico | `install --status` informa tamaño antes de bajar; `install --dry-run` (futuro) muestra costo. |
| Tick del loop introduce lag perceptible | Medir con `tests/rss_measure.rs`; presupuesto de render sigue <50ms. |
| Animación distrae con `Idle` largo | Frecuencia muy baja (~48s/ciclo en Idle); `NO_COLOR=1` lo desactiva. |
| Streaming rompe protocolo TOOL | El parsing de TOOL se hace DESPUÉS del EOF; los chunks van siempre a stdout. El TOOL se imprime como línea `> TOOL: …` aparte. |
| `cortex brain` como subfamilia choca con el binario `cortex-brain` | El binario se llama `cortex-brain` (guion); el subcomando es `cortex brain` (espacio). Sin colisión en clap. |
| Lock deja huérfanos si un proceso muere | Lock con `O_EXCL` + un PID adentro; al reintentar, chequear si el PID está vivo (Linux) o timeout duro (Windows). |
