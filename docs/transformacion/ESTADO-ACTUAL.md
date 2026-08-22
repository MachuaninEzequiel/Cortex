# ESTADO ACTUAL DEL PROGRAMA

> Actualizar SIEMPRE al terminar una sesión de trabajo. Máximo ~40 líneas.

## Sesión 2026-08-21/22 — TRAMO 0 + TRAMO 1 ola 1 + OBRA 02 FASE 0-1 completos

- Sello: tag v0.5.0-baseline-seal @ a64e350 (pusheado). master intacto.
- Rama: feature/transformacion-2026-08. Suite unit+integration: VERDE.
- TRAMO 0 (788c5c4): pin mcp<2 + tar-slip fix. 86 -> 0 fallos.
- TRAMO 1 ola 1 (e9b3e4e..bf5bd3b): ide uninstall seguro, session mutate() anti
  lost-update, webgraph cache/404/mode, cli --dry-run real, poda P1 (6 ítems).
- OBRA 02 FASE 0-1 (640ca20):
  - base.py: helpers compartidos de marcadores (extract/strip/upsert/is_cortex_owned) + 22 tests
  - Caracterización completa de los 11 adapters: test_contract_git_dirs.py (62 tests)
    + test_contract_native_config.py (17 tests)
  - KNOWN-BUGS documentados con xfail strict: uninstall no-op heredado en
    claude_code/opencode/vscode/windsurf/zed/antigravity/hermes; cursor deja skills huérfanos

## Próximo paso

- OBRA 02 FASE 2: migrar adapters al contrato IDEAdapterV2 uno por uno usando los
  helpers de base.py (orden sugerido: codex→opencode→claude_code→pi→cursor→resto),
  haciendo pasar los xfail. Cada adapter = 1 commit con su suite verde.
- FASE 3: superficie CLI unificada `cortex ide setup|status|remove|list` + deprecation.
- Después de Obra 02: P3 golden tests MCP + split server.py; luego Tramo 2 (Obra 04 embeddings).
- Nota flake: test_setup_dry_run_creates_nothing mostró 1 fallo no reproducible (orden/pollution); vigilar.
