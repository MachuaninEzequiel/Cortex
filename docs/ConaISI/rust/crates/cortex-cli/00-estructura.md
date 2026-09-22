# Estructura interna — `rust/crates/cortex-cli`

Binario **`cortex-cli`** (P12B-8): CLI 100% nativo. Dispatch por primer token; comando desconocido → `No such command '<first>'.` rc 2. **Sin passthrough a Python.** `CORTEX_PY=1` solo imprime aviso histórico y continúa nativo.

Dependencias: clap 4, unicode-width, cortex-{doctor,enterprise,tutor,autopilot,webgraph-server,workspace,core,app,embed,actions,services,setup,mcp,config,tui}, sha2, ratatui, serde_yaml, chrono, serde_json (float_roundtrip).

```
cortex-cli/
├── Cargo.toml
├── examples/cli_check.rs
├── src/
│   ├── main.rs          # dispatch
│   ├── lib.rs
│   ├── paths.rs
│   ├── memory.rs        # NativeMemory
│   ├── memory_cmds.rs   # search/context/stats/reindex
│   ├── pyjson.rs
│   ├── rich_panel.rs
│   └── commands/
│       ├── mod.rs
│       ├── doctor.rs
│       ├── misc.rs              # agent-guidelines, install-skills
│       ├── tutor.rs             # tutor + hint
│       ├── org_config.rs
│       ├── promote.rs
│       ├── review.rs
│       ├── memory_report.rs
│       ├── webgraph.rs
│       ├── autopilot.rs
│       ├── session_cmd.rs
│       ├── next_cmd.rs
│       ├── hu_cmd.rs
│       ├── ide_cmd.rs
│       ├── remember_cmd.rs
│       ├── docs_cmd.rs
│       ├── ci_cmd.rs
│       ├── setup_cmd.rs
│       ├── pr_context_cmd.rs
│       ├── mcp_cmd.rs
│       └── finish_cmd.rs
└── tests/  (20 archivos de contrato/dispatch/paridad)
```

## Árbol de comandos cableados (`dispatch_native`)

| Token | Destino |
|---|---|
| (sin args) | TUI Home (`cortex_tui`), o snapshot 100×40 si stdout no es TTY |
| `--cli-version` / `--version` / `-V` | `cortex-cli 0.1.0` |
| `doctor` | `commands::doctor` |
| `agent-guidelines` | `misc::agent_guidelines` |
| `install-skills` | `misc::install_skills` |
| `tutor` / `hint` | `commands::tutor` |
| `org-config` | enterprise config |
| `promote-knowledge` | promotion |
| `review-knowledge` | cola review |
| `memory-report` | reporting |
| `webgraph` | export/serve/doctor |
| `autopilot` | start/preflight/checkpoint/finish/status/doctor |
| `search` `context` `stats` `reindex` | `memory_cmds` |
| `session` | current/checkpoint/switch/diff/abandon/list/show/watch\|tui/task/hooks |
| `next` | motor de acciones |
| `hu` | import/list/show |
| `ide` | list/setup/remove/status |
| `remember` / `forget` | episódico |
| `docs` | search/migrate/validate/restore/list-backups/routing-table |
| `ci` | validate-pr/open-review-session/report-checkpoint/close-review-session |
| `setup` | agent/pipeline/full/composed/webgraph/enterprise |
| `init` | alias de `setup agent` |
| `pr-context` | capture/store/search/generate/full |
| `mcp-server` / `mcp-serve` | rmcp stdio |
| `finish` / `finish-session` | NativeFinishBackend |

## Relación

Glue: abre `NativeMemory` / `WorkspaceLayout` y llama crates B. Es el único binario CLI del workspace.
