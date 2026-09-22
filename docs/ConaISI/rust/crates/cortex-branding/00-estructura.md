# rust/crates/cortex-branding — estructura interna

Identidad visual pura (sin dependencias de TUI). Half-block, paleta, pixel maps.

```
cortex-branding/
├── Cargo.toml
├── examples/preview.rs
├── src/
│   ├── lib.rs
│   ├── palette.rs     # Rgb, colores marca
│   ├── pixels.rs      # PixelMap, blit, PixelKind
│   ├── gradient.rs
│   ├── logo.rs        # LogoVariant::{Full, Compact, Mark}
│   ├── wordmark.rs
│   └── ansi.rs        # render_ansi / render_plain / env_color_mode / visible_width
└── tests/geometry.rs
```

## Relaciones

- **Recibe de:** nada de otros crates Cortex.
- **Envía a:** `cortex-brain` (banner ≤80 cols), `cortex-tui` (CortexLogo widget), `cortex-companion` (hud_brand consume paleta/mark).
