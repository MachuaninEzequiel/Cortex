# rust/crates/cortex-tui — estructura interna

TUI nativa sobre ratatui (Obra 07 P10). Arquitectura ELM-lite: `Action` → `update` → `Effect` → runtime.

```
cortex-tui/
├── Cargo.toml
├── examples/{splash,home_preview,capture}.rs
├── src/
│   ├── lib.rs                 # BrandingMode, lang(), reexports
│   ├── app/{mod,action,effect,state,update,runtime,search}.rs
│   ├── components/            # header, list, panel, status_bar, help, empty_state, feedback
│   ├── deprecated/            # renderer/header/splash legacy
│   ├── actions.rs / sessions.rs / session_detail.rs / search.rs / home.rs
│   ├── keymap.rs / hit.rs / layout.rs / view.rs / renderer.rs
│   ├── splash.rs / terminal.rs / theme.rs / event.rs / clipboard.rs
└── tests/{sessions_screen,snapshots,theme_hygiene}.rs
```

Breakpoints branding (`lib.rs`): ≥90×28 Full, ≥55×18 Compact, resto Minimal.

## Relaciones

- **Recibe de:** `cortex-branding`, `cortex-actions`, `cortex-app`.
- **Envía a:** `cortex-cli` (comando TUI); framebuffer ratatui.
