# rust/crates/cortex-setup/src/session_hooks/claude_code.rs

## Qué tiene adentro

`ClaudeCodeHookAdapter`. Escribe `_cortex_managed` en `.claude/settings.json` PostToolUse matcher `Edit|Write|MultiEdit`, comando `cortex session checkpoint --source ide-hook --note 'edit via Claude Code' ... || true`. `json_dump_utf8`.

## Para qué sirve

Checkpoint automático al editar en Claude Code.

## Relaciones

### Recibe de

- settings.json existente.

### Envía a

- `.claude/settings.json`.

### Notas de implementación observadas en el código

Load: {} si falta/vacío; error si JSON inválido o raíz no-objeto.
