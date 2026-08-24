# 10 — P10: Branding Cortex + TUI ratatui (implementación)

> Estado: **COMPLETO** (2026-08-24, sesión P10). Gate P10 del plan 08:
> "snapshot render + latencia" → **VERDE** (snapshots TestBackend + Home
> render promedio <50ms, presupuesto `RENDER_BUDGET_MS = 50`).
>
> Contrato estético: `docs/logo/prompt-logo.md` (aprobado por el dueño).
> Referencia visual: `docs/logo/cortex-logo.png` (isotipo canónico).
> Este doc sigue el formato de entregable §51 del prompt.

## 1. Archivos creados

```
rust/crates/cortex-branding/          # identidad PURA, cero dependencias
├── Cargo.toml
├── src/
│   ├── lib.rs            # wiring + re-exports
│   ├── palette.rs        # paleta oficial + gradiente + fallback 16 colores
│   ├── pixels.rs         # PixelKind + PixelMap (parse/blit/glow exterior)
│   ├── logo.rs           # máscaras Full/Compact/Mark (FUENTE DE VERDAD)
│   ├── gradient.rs       # color = f(kind, y): geometría separada del color
│   ├── wordmark.rs       # "Cortex" pixel-font 5×7 propia (35×7)
│   └── ansi.rs           # half-blocks → ANSI (truecolor/16/plain) + utilidades
├── examples/preview.rs   # preview de las 3 variantes + wordmark
└── tests/geometry.rs     # dimensiones, glow solo-exterior, silueta

rust/crates/cortex-tui/               # integración ratatui
├── Cargo.toml            # deps: ratatui 0.30 + cortex-branding
├── src/
│   ├── lib.rs            # CortexLogo re-export, BrandingMode, breakpoints, lang()
│   ├── renderer.rs       # PixelMap → celdas ratatui (Widget CortexLogo)
│   ├── splash.rs         # splash responsive (logo + wordmark + tagline)
│   └── home.rs           # Home espejo de HomeState (cortex/tui/core.py)
├── examples/splash.rs    # demo interactiva responsive en vivo
├── examples/home_preview.rs  # dump headless del Home a texto
└── tests/snapshots.rs    # snapshots TestBackend + gate latencia <50ms
```

## 2. Archivos modificados

| Archivo | Cambio |
|---|---|
| `rust/Cargo.toml` | +2 members de workspace (`cortex-branding`, `cortex-tui`) |
| `rust/crates/cortex-brain/Cargo.toml` | +dep `cortex-branding` (path) |
| `rust/crates/cortex-brain/src/chat.rs` | `BANNER` ASCII → `banner()/banner_ansi()/banner_plain()` (isotipo Compact + wordmark lado a lado, 65×10 px → 5 filas) |
| `rust/crates/cortex-brain/src/main.rs` | print del banner nuevo con assert de ≤80 columnas **visibles** |
| `rust/crates/cortex-brain/tests/spec_behavior.rs` | spec `banner_renderiza_en_80` → `banner_visible_en_80` (mismo contrato, mide columnas visibles strip-ANSI en ambas variantes) |

**NO se tocó** (zona del otro agente / cierre conjunto): `cortex-app/*`,
`cortex-config/*`, `cortex-core/*`, `cortex-embed/*`, `cortex-py/*`,
`cortex/` (Python), `HANDOFF.md`, `ESTADO-ACTUAL.md`, `08-*.md`,
`rust/Cargo.lock` (quedó sucio en el árbol por la sesión P2-P9; mis 2
entradas mecánicas se consolidan al cierre de sesión — CI no usa `--locked`).

## 3. Arquitectura elegida

```text
GEOMETRÍA (logo.rs: máscaras const)      ← fuente de verdad, curada a mano
      ↓ PixelKind {Transparent, Mark, Cross, Layer, Highlight, Shadow}
COLOR    (gradient.rs: color = f(kind, y, h))   ← gradiente desacoplado
      ↓ PixelMap
RENDER   ├── ansi.rs (half-blocks → ANSI plano: banner brain, previews)
         └── cortex-tui/renderer.rs (PixelMap → celdas ratatui: Widget)
```

- **Dos crates** en vez de uno: `cortex-branding` no tiene dependencias, así
  el brain (y cualquier binario futuro) usa la identidad sin arrastrar
  ratatui. Mismo criterio que cortex-core (puro) vs cortex-py (fachada).
- **Máscaras como datos, no strings gigantes**: `PixelMap` parsea filas de
  chars (`'#'`/`'X'`/`'L'`/`'H'`) con padding automático; el glow periférico
  se calcula UNA vez (`OnceLock`) y solo emana del cuerpo principal
  (Mark/Cross/Highlight) para no llenar los huecos entre capas.
- **Fondo jamás pintado**: celdas transparentes → `Color::Reset` /
  `\x1b[49m`. El usuario mantiene su tema (prompt §26).
- **Breakpoints centralizados**: `branding_mode(area)` — ≥90×28 Full,
  ≥55×18 Compact, resto Minimal (prompt §18). Nadie más decide variantes.
- **Half-blocks**: `▀` fg/bg, `▄` fg, `█` merge mismo-color, espacio en
  transparente (prompt §10). Sin `░▒▓` como base (§23), sin animación (§48).
- **Fallback**: `NO_COLOR` → silueta plana; `COLORTERM`/`TERM` sin truecolor
  → paleta 16 (Ice→Cyan, Light→LightCyan, Cyan→Cyan, Blue→Blue,
  Deep/Shadow/Muted→DarkGray, prompt §25).

## 4. Dimensiones finales

| Variante | Píxeles lógicos | Terminal (half-block) | Rango prompt | Uso |
|---|---|---|---|---|
| **Full** | 44×34 | 44 cols × 17 filas | 44-54 × 16-22 ✓ | splash, onboarding, empty states |
| **Compact** | 28×20 | 28 cols × 10 filas | 26-34 × 10-14 ✓ | pantallas medianas, banner brain |
| **Mark** | 13×10 | 13 cols × 5 filas | 8-14 × 4-7 ✓ | headers (Home) |
| Wordmark | 35×7 | 35 cols × 4 filas | — | bajo el isotipo Full |

## 5. Paleta final

| Nombre | Hex | Rol |
|---|---|---|
| `ICE` | `#D9F4FF` | highlights, tope del gradiente |
| `LIGHT` | `#A9E3FF` | gradiente alto, X (con CYAN), wordmark |
| `CYAN` | `#55CAF7` | centro del gradiente |
| `BLUE` | `#209CEB` | gradiente bajo |
| `DEEP` | `#1167C4` | base del gradiente |
| `SHADOW` | `#0B3158` | glow periférico (solo Full) |
| `TEXT` | `#D9F4FF` | texto principal |
| `MUTED` | `#6E899B` | texto secundario, tagline, hints |
| `BG` | `#050A10` | SOLO referencia — no se pinta nunca por default |

Gradiente del isotipo: ICE → LIGHT → CYAN → BLUE → DEEP (vertical). La X va
en banda LIGHT→CYAN; las capas muestrean el gradiente corrido `h/6` hacia
abajo (tono levemente más profundo, sin exagerar).

## 6. Cómo probar

```bash
cd rust
# Splash interactivo (resize en vivo: Full → Compact → Minimal)
cargo run -p cortex-tui --example splash          # q/Esc sale

# Preview de las 3 variantes + wordmark (respeta NO_COLOR/COLORTERM)
cargo run -p cortex-branding --example preview

# Home headless (dump a texto)
cargo run -p cortex-tui --example home_preview

# Banner nuevo del brain
printf '/salir\n' | cargo run -q -p cortex-brain --bin cortex-brain

# Gates
cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test
```

## 7. Diferencias respecto de la imagen original

1. **Glow**: la imagen tiene bloom difuso; la terminal no soporta blur. Se
   implementa como anillo periférico de 1px en `SHADOW` (#0B3158), solo en
   Full, solo alrededor del cuerpo principal (las capas quedan nítidas y los
   huecos entre slabs conservan el espacio negativo). En modo plain el glow
   no se dibuja.
2. **X "aplastada"**: los brazos de la X conservan la diagonal a 45° REAL
   (pendiente 1.8 en la grilla) porque la celda de terminal es ~1:2; en
   píxeles lógicos se ve más ancha que alta, igual que en el PNG.
3. **Regularización**: la pared izquierda es vertical perfecta y las 4 capas
   son paralelogramos con slant/spacing uniformes (el PNG tiene drift de
   perspectiva y glow que ensucia los bordes). Reinterpretación deliberada,
   no captura pixelada (prompt §37).
4. **Mark**: la X usa trazo 2 con contacto central (a 13×10 px no entra una
   X de brazos separados); conserva C + abertura + 2 insinuaciones de capa.
5. **Wordmark**: pixel-font 5×7 propia (no la fuente del PNG), mayúscula C +
   minúsculas, como pide el prompt §20 Opción A.

## 8. Estado P10 y qué falta para el cierre total de la fase

Gate P10 del plan 08: **snapshot render + latencia → VERDE**.

- 8 tests de snapshot (TestBackend): Full/Compact/Minimal, área mínima sin
  panic, no-escritura fuera del área, determinismo, contenido del Home.
- Gate de latencia: 200 renders del Home 80×24, promedio < 50ms.
- Suite: `cortex-branding` 25 tests + `cortex-tui` 10 tests + brain 55
  tests, todos verdes; `cargo check --workspace` verde; suite Python
  completa verde (exit 0, oráculo intacto).

**Diferido por diseño (no es deuda de P10):**
- Cableado del Home a servicios reales (sessions/acciones/vault): cuando
  cortex-app los exponga (P4-P6 del otro agente). `HomeState` ya espeja los
  campos de `cortex/tui/core.py` para que sea mecánico.
- `cortex brain` in-process y default Rust: P12.
- Animaciones: explícitamente fuera de alcance v1 (prompt §48).
- Comandos `cortex splash` / integración del Home en el CLI: cuando el CLI
  nativo migre a subcomandos propios (Obra E / P11-P12).
