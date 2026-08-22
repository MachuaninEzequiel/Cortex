# ESTADO ACTUAL DEL PROGRAMA

> Actualizar SIEMPRE al terminar una sesión de trabajo. Máximo ~40 líneas.

## Sesión 2026-08-22 — OBRA 02 COMPLETA (Fases 0-1, 2 y 3)

- Sello: v0.5.0-baseline-seal @ a64e350. Rama: feature/transformacion-2026-08. Suite unit VERDE (exit 0).
- TRAMO 0 + TRAMO 1 ola 1: commits 788c5c4..bf5bd3b.
- OBRA 02 (estándar único de CLIs/IDEs) CERRADA:
  - Fase 0-1 (640ca20): helpers marcadores en base.py + caracterización 11 adapters.
  - Fase 2 (42adfe1..13c7ff1): uninstall(project_root) real en los 11; restore-de-backup;
    merge inverso JSON/TOML; fix skills huérfanas cursor; fix _unique_backup.
  - Fase 3 (f8a6ec0): CLI unificada `cortex ide list|setup|remove|status` (--project-root,
    --dry-run real, --json) + deprecation funcional de install-ide/uninstall-ide/inject/sync-ide
    con paridad legacy testeada. 22 tests nuevos.
- Backlog Obra 02 (no bloqueante):
  - Byte-equality de re-run requiere timestamp congelado en _generate_autogen_header.
  - Docs/skills que mencionan comandos viejos ("Regenerate: cortex sync-ide").
  - Hooks dentro de `ide setup` (--no-hooks/--keep-hooks).

## Próximo paso (elegir)

1. P3: golden tests MCP -> split server.py 2977l en schemas/dispatcher/handlers (ALTO riesgo).
2. Tramo 2 = Obra 04: fixes vectoriales A1-A6 -> suite eval ES/EN -> modelo nuevo + config por idioma.
3. P4: adelgazar cli/main.py (los 4 comandos IDE viejos ya delegan; quedan ~15 comandos top-level por migrar a subapps).
