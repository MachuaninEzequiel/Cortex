# rust/crates/cortex-setup/src/ide/adapters/vscode.rs

## Qué tiene adentro

`VSCodeAdapter`. Agents `.github/agents/*.agent.md` (cortex-sync, cortex-SDDwork). Subagents `.claude/agents/` (explorer, implementer, documenter). MCP `.vscode/mcp.json` clave `servers` con `${workspaceFolder}`.

## Para qué sirve

VS Code.

## Relaciones

### Recibe de

- Prompts strip frontmatter.

### Envía a

- GitHub agents + vscode mcp.

### Notas de implementación observadas en el código

SSoT install/uninstall en constantes VSCODE_TOP_AGENTS / CLAUDE_SUBAGENTS.
