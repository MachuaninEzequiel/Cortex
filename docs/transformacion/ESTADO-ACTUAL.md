# ESTADO ACTUAL DEL PROGRAMA

> Actualizar SIEMPRE al terminar una sesión de trabajo. Máximo ~40 líneas.

## Sesión 2026-08-22 — OBRA 02 FASE 2 completa (uninstall real en los 11 adapters)

- Sello: v0.5.0-baseline-seal @ a64e350. Rama: feature/transformacion-2026-08. Suite VERDE.
- TRAMO 0 + TRAMO 1 ola 1: commits 788c5c4..bf5bd3b (ver docs/transformacion/ESTADO-ACTUAL.md histórico en git).
- OBRA 02:
  - Fase 0-1 (640ca20): helpers de marcadores en base.py + caracterización de los 11 adapters.
  - Fase 2 (42adfe1, 9913da1, 13c7ff1): contrato uninstall(project_root) en base +
    uninstall REAL en los 9 adapters que lo tenían roto/no-op:
    restore-de-backup (claude_code, windsurf, antigravity), merge inverso JSON/TOML
    (opencode, claude_desktop, zed, hermes, vscode, cursor), fix skills huérfanas cursor,
    fix local _unique_backup (granularidad de segundos pisaba backups).
  - KNOWN-BUGS restantes en adapters: 0 conocidos. Todos los xfail flippeados.
  - Falta Fase 3: superficie CLI unificada `cortex ide setup|status|remove|list`
    (+deprecation de install-ide/uninstall-ide/inject/sync-ide/session hooks *).

## Próximo paso

1. Obra 02 Fase 3 (CLI unificada) — requiere tocar cli/main.py (libre desde P4 pendiente;
   coordinar con poda). Tests de paridad viejo-vs-nuevo.
2. P3 golden tests MCP + split server.py (ALTO riesgo).
3. Tramo 2 = Obra 04 (embeddings + idioma): fixes A1-A6 primero.
