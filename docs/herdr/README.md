# TUI de Cortex para Herdr — Especificación, Preferencias y Estado

Este documento consolida el historial de diseño, decisiones arquitectónicas, dudas, indicaciones del usuario y el estado actual de la **TUI de Cortex** y su integración con **Herdr**.

---

## 1. Dudas y Consultas Planteadas por el Usuario

Durante el proceso de diseño e iteración surgieron las siguientes consultas técnicas y conceptuales:

### ¿Qué fue lo último que se hizo en el repositorio antes de esta etapa?
* Se consolidó la transformación nativa en Rust (Obras 17 y 18).
* Se completó el Doctor nativo, el formato binario `vectors.v3.bin`, el servidor MCP nativo y la base de `cortex-companion` para Herdr.

### ¿En cuanto a Herdr, la TUI y el engine con el modelo de Liquid, cómo quedó?
* **Herdr Companion:** Paneles de control interactivos (`cortex-herdr-float`, `cortex-herdr-sidecar`, `cortex-herdr-copilot`) integrados en el multiplexor de terminal Herdr.
* **Liquid RAM On-Demand:** Carga y descarga perezosa en memoria del modelo GGUF (en reposo consume 0 MB de VRAM/RAM; al consultarse se despierta y luego vuelve a reposo).
* **Herramientas de Agente (SDDwork):** Enrutamiento determinista hacia herramientas de solo lectura (`read_file`, `grep_search`, `tree`) y de mutación bajo confirmación del usuario.

### ¿Por qué al probar un comando se cerraba imprimiendo una sola pantalla?
* Los binarios de la TUI tienen un mecanismo de protección para entornos no interactivos / CI (`!is_terminal()`). Cuando se ejecutan sin una terminal TTY interactiva asignada, generan un snapshot estático y salen limpiamente sin colgar el proceso.

### ¿Por qué no encontraba resultados en otro proyecto?
* **Indexación:** Un proyecto nuevo sin base vectorial tiene 0 documentos indexados en el vault semántico.
* **Separación de modos:** La tecla `/` activa la búsqueda directa en el índice vectorial/memoria, mientras que `Tab` / `brain` abre la consulta conversacional con el modelo local de Liquid.

### ¿UI Web Integrada vs. Ratatui?
* Se analizó la alternativa de una interfaz Web/Electron/Tauri vs. Ratatui nativo en Rust.
* **Decisión:** Se descartó la opción Web debido a que consumiría entre 200 y 500 MB de memoria RAM y agregaría overhead de renderizado. Se priorizó Ratatui por su velocidad (<20 ms de inicio, <20 MB de memoria) y cero impacto en la máquina del desarrollador.

---

## 2. Indicaciones y Preferencias del Usuario

### 2.1. Rendimiento y Filosofía de Stack
* **Prioridad:** Máxima velocidad, consumo de recursos mínimo y ligereza extrema.
* **Stack tecnológico:** **Rust + Ratatui**.
* **Nivel de referencia:** Equivalente al estándar de **Gentle-AI** y **Engram** (Go / Bubbletea / Lipgloss) trasladado al ecosistema de Rust.

### 2.2. Estética y Diseño Visual
* **Paleta de Colores:** **Catppuccin Mocha** centralizada y tipada (`#1E1E2E` base, `#313244` superficie, `#CBA6F7` Mauve, `#89DCEB` Sky, `#B4BEFE` Lavender).
* **Eliminación de Marcos Verdes Estridentes:** Los bordes y focos deben usar tonos elegantes (Mauve / Surface2), eliminando cualquier marco verde chillón heredado.
* **Bordes Redondeados:** Uso estricto de `BorderType::Rounded` (`╭╮╰╯`) en todos los paneles, tarjetas y botones estándar. Reservar bordes dobles únicamente para diálogos modales críticos.
* **Tipografía y Wordmark 3D "CORTEX":**
  * Debe replicar exactamente el estilo de pixel art isométrico 3D con sombreado inferior de `herdr-texto-formato.jpeg` y `assets/nueva-estetica/nuevo-logo-cortex.png`.
  * **Caras frontales:** Azul cielo / Sky (`#89DCEB`).
  * **Iluminación / Bisel superior:** Blanco hielo / Highlight (`#C8F0DC`).
  * **Extrusión y sombra 3D inferior derecha:** Azul zafiro profundo (`#04A5E5` / `#1E3A5F`).
  * **Disposición horizontal fija:** Matriz de 35 columnas × 4 filas en semibloques Unicode (`▀` / `▄`). Nunca partirse verticalmente ni encimarse sobre las tarjetas inferiores.

### 2.3. Concepto e Interacción en Herdr
* **Interactividad con Mouse (Must-have):** Capacidad de hacer clic en botones (`[ Sesiones ]`, `[ Ver acciones ]`, `[ Abrir sesión ]`, `[ Menú ]`, `[ Copiar ]`, `[ Aprobar ]`, `[ Saltar ]`, `▸ brain`), cambiar de paneles y hacer scroll con la rueda del mouse.
* **Keymap Vim Completo:** Navegación por teclado complementaria (`j`/`k`, `g`/`G`, `/` buscar, `Enter` activar/copiar, `Esc` atrás/cerrar, `c` copiar vía OSC 52, `q` salir).
* **Integración en la Misma Terminal:** Diseñado para abrirse como panel flotante (~25% inferior) o sidecar (30/70) dentro del mismo espacio de trabajo de Herdr donde el desarrollador programa.

### 2.4. Higiene y Mantenimiento de Código
* No borrar código previo en uso o de referencia histórica; moverlo a la carpeta `deprecated/` y comentarlo debidamente para mantener el historial intacto.

---

## 3. Trabajo Realizado

1. **Instalación y Configuración del Ecosistema Ratatui:**
   * Agregadas las dependencias: `catppuccin` (feature `ratatui`), `ratatui-macros`, `tui-widgets`, `tui-input`, `tachyonfx`, `crossterm` (feature `event-stream`), `tokio`, `futures`, `color-eyre`, `insta`.
2. **Arquitectura MUV (Model-Update-View) Desacoplada:**
   * Separación estricta entre estado puro (`AppState`), reducer puro determinista (`update.rs`), mapeador de eventos (`event.rs`), portapapeles (`clipboard.rs` con secuencias ANSI OSC 52) y vistas de renderizado puras (`view.rs`).
3. **Tema Catppuccin Mocha Centralizado:**
   * Creación de `theme.rs` con tokens semánticos completos (`bg`, `surface`, `text`, `accent`, `focus`, `border_idle`, `border_focus`, `wordmark_highlight`, `wordmark_face`, `wordmark_shadow`).
4. **Implementación del Wordmark 3D Voxel:**
   * Creación de la función `draw_3d_wordmark` que dibuja el logo en 35×4 celdas con semibloques `▀`/`▄`, sombras 3D y gradiente vertical, solucionando el bug visual de `BigText`.
5. **Migración a `src/deprecated/`:**
   * Se movieron y comentaron los renderizadores ANSI antiguos (`renderer_legacy.rs`, `splash_legacy.rs`, `header_legacy.rs`).
6. **Modernización de Widgets de `cortex-companion`:**
   * Se actualizaron los botones, listas y paneles de Herdr Companion con `BorderType::Rounded`, colores Catppuccin y efectos hover activos al interactuar con el mouse.

---

## 4. Estructura de Carpetas

### 4.1. Crates Principales de Interfaz de Usuario
```text
rust/crates/
├── cortex-tui/                     # TUI completa de Cortex (Patrón MUV / Elm)
│   ├── Cargo.toml                  # Dependencias del stack moderno Ratatui
│   └── src/
│       ├── lib.rs                  # Exportaciones públicas de la TUI
│       ├── theme.rs                # Paleta Catppuccin Mocha centralizada
│       ├── event.rs                # Mapeo crossterm Event -> Action
│       ├── clipboard.rs            # Copia a portapapeles nativo OSC 52
│       ├── view.rs                 # Renderizado puro (draw, draw_3d_wordmark, draw_home...)
│       ├── app/                    # Estado, reducer y runtime
│       │   ├── state.rs            # AppState, Screen, Overlay, LoadState
│       │   ├── action.rs           # Acciones del usuario y del sistema
│       │   ├── update.rs           # Reducer puro (state, action) -> Option<Effect>
│       │   └── runtime.rs          # Loop asíncrono y recarga de snapshots
│       └── deprecated/             # Código legacy archivado y comentado
│           ├── mod.rs              # Módulo contenedor
│           ├── header_legacy.rs    # Header anterior de bloques
│           ├── renderer_legacy.rs  # Renderizador ANSI de píxeles anterior
│           └── splash_legacy.rs    # Splash screen anterior
│
├── cortex-companion/               # HUD, Paneles Flotantes y Sidecar de Herdr
│   ├── Cargo.toml
│   └── src/
│       ├── app.rs                  # Manejo de eventos y mouse hit-testing
│       ├── runner.rs               # Event loop interactivo y TTY protection
│       ├── widgets.rs              # Button, Panel y List con bordes redondeados y hover
│       ├── hud_brand.rs            # Marca compacta de HUD
│       └── screens/                # Pantallas específicas de Herdr
│           ├── home.rs             # Home con wordmark 3D y botones clickeables
│           ├── hud_screen.rs       # HUD ~25% inferior para aprobación y copia de prompts
│           ├── copilot_screen.rs   # Modo co-pilot interactivo
│           ├── brain_screen.rs     # Panel conversacional con Liquid RAM
│           ├── sessions_screen.rs  # Lista y detalle de sesiones
│           ├── actions_screen.rs   # Propuestas y aprobación del Action Engine
│           └── search_screen.rs    # Buscador semántico e híbrido
```

---

## 5. Lo Último que se Hizo

1. **Reemplazo total del banner anterior:** Se sustituyó `BigText` por `draw_3d_wordmark`, logrando la tipografía 3D idéntica a `herdr-texto-formato.jpeg` (35 cols × 4 filas fijas con sombras 3D y luces superiores).
2. **Consolidación de `cortex-companion`:** Se aplicaron bordes redondeados (`BorderType::Rounded`) y efectos hover a los botones de `widgets.rs`, preservando al 100% la interactividad por mouse y las coordenadas de clic.
3. **Suite de pruebas completa:**
   * `cargo test -p cortex-tui`: **98 tests pasados / 0 fallados**.
   * `cargo test -p cortex-companion`: **100+ tests pasados / 0 fallados**.
