# rust/crates/cortex-companion — estructura interna

TUI mouse-first (ratatui) + integración Herdr. `#![forbid(unsafe_code)]`.

```
cortex-companion/
├── Cargo.toml
├── examples/preview_ansi.rs
├── src/
│   ├── lib.rs              # CompanionMode, Screen, UiRequest
│   ├── engine.rs           # trait Backend + InProcessBackend
│   ├── approval.rs         # run_guarded + ActionLog
│   ├── app.rs              # estado ELM-lite, hit-test, LiquidRam 90s
│   ├── effects.rs          # aplica Effect al estado
│   ├── runner.rs           # loop ratatui
│   ├── menu.rs             # catálogo anti-olvido de comandos CLI
│   ├── brain_panel.rs      # chat híbrido (reads in-process, mutaciones [Ejecutar])
│   ├── herdr.rs            # herdr api snapshot / plugin pane
│   ├── feedback.rs         # feedback.jsonl rotado
│   ├── hud_brand.rs        # mark/word pixel RAM
│   ├── clipboard.rs
│   ├── theme.rs / widgets.rs
│   ├── screens/            # home, menu, sessions, actions, search, brain, hud, copilot
│   └── bin/
│       ├── companion.rs    # modo Normal
│       ├── sidecar.rs      # CompanionMode::Sidecar
│       ├── float.rs        # Float HUD
│       └── copilot.rs      # Copilot
└── tests/                  # approval, parity_cli, hud, screens_snapshot, …
```

Binarios en Cargo.toml: `cortex-companion`, `cortex-herdr-sidecar`, `cortex-herdr-float`, `cortex-herdr-copilot`. Feature `llama` → `cortex-brain/llama`.

## Relaciones

- **Recibe de:** `cortex-cli::memory` (NativeMemory, pyjson), `cortex-actions`, `cortex-app::session`, `cortex-workspace`, `cortex-branding`, `cortex-brain` (brain_panel), CLI `herdr`.
- **Envía a:** terminal ratatui; `.cortex/action_log.jsonl`; `.cortex/feedback.jsonl`; panes Herdr (`plugin pane open`, `report-agent`).
