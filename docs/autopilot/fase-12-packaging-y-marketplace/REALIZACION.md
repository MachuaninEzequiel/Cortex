# Fase 12 — Packaging y Marketplace: Realización

**Fecha:** 2026-05-09  
**Estado:** Completado

---

## 1. Archivos creados

| Archivo | Descripción |
|---|---|
| `.codex-plugin/plugin.json` | Manifesto Superpowers-compatible para Codex |
| `.claude-plugin/plugin.json` | Manifesto Superpowers-compatible para Claude Code |
| `.cursor-plugin/plugin.json` | Manifesto Superpowers-compatible para Cursor |
| `cortex/autopilot/packaging.py` | Módulo de packaging: `PluginManifest`, `install_plugin()`, `uninstall_plugin()`, `list_compatible_plugins()`, `validate_manifest()` |
| `tests/unit/autopilot/test_packaging.py` | 14 tests: manifest load/validate, install/uninstall cursor, idempotencia, list compatible plugins |
| `docs/autopilot/marketplace.md` | Documentación de marketplace: formatos, instalación, desinstalación, requisitos, compatibilidad |

## 2. Archivos modificados

| Archivo | Cambio | Motivo |
|---|---|---|
| `cortex/autopilot/cli.py` | Agregados comandos `install` y `uninstall` | Gate de salida exige instalación/desinstalación limpia |
| `tests/unit/autopilot/test_cli.py` | Agregadas clases `TestInstall` y `TestUninstall` (4 tests) | Cobertura de comandos CLI nuevos |

## 3. Decisiones tomadas

### 3.1 Reutilización de adapters existentes en lugar de reimplementar install/uninstall

Los adapters `CursorAutopilotAdapter`, `ClaudeCodeAutopilotAdapter`, etc. ya implementan `install()` y `uninstall()` con backup y remoción de bloques.  `packaging.py` es una capa fina que:
- Valida manifestos JSON (`PluginManifest` con Pydantic).
- Resuelve el adapter vía `registry.get_adapter()`.
- Delega la operación al adapter.

Esto mantiene la regla de la fase: *no reescribir fases anteriores*.

### 3.2 Manifestos estáticos en raíz del repo

Los directorios `.codex-plugin/`, `.claude-plugin/`, `.cursor-plugin/` viven en la raíz del repositorio, siguiendo exactamente la estructura pedida en el plan de fase 12.  Cada manifesto apunta a:
- `skills.directory`: `cortex/autopilot/skills`
- `hooks.directory`: `cortex/autopilot/hooks`

Las rutas son relativas a la raíz del repo y se resuelven por el installer según el contexto.

### 3.3 CLI install/uninstall implementados ahora

El plan global de fase 7 mencionaba `cortex autopilot install --ide <name>` como comando deseado, pero no estaba implementado.  Se implementó en esta fase porque el gate de salida de fase 12 exige explícitamente:
> "Instalacion limpia en workspace nuevo. Desinstalacion limpia."

Sin comandos CLI, no se podría verificar ese gate de forma automatizada.

### 3.4 Sin dependencia externa obligatoria

El packaging no agrega nuevas dependencias a `pyproject.toml`.  Usa `pydantic` (ya requerido por Cortex) y el adapter registry existente.

## 4. Discrepancias detectadas

| Discrepancia | Resolución |
|---|---|
| Fase 7 mencionaba `install --ide` pero no existía en CLI | Implementado en esta fase como requisito del gate de salida |
| El plan pedía solo 3 manifestos (codex, claude, cursor) pero hay 5 adapters | Se crearon exactamente los 3 manifestos solicitados. Los adapters opencode/pi están disponibles vía CLI install igualmente. |

## 5. Comandos ejecutados y resultados

```bash
# Tests unitarios de packaging + CLI
pytest tests/unit/autopilot/test_packaging.py tests/unit/autopilot/test_cli.py --tb=short --no-cov
# => 34 passed in 2.20s

# Suite unitaria completa de Autopilot
pytest tests/unit/autopilot --tb=short --no-cov
# => 291 passed in 3.13s

# Suite E2E de escenarios Autopilot (regresión Fase 11)
pytest tests/e2e/scenarios/test_autopilot_basic.py tests/e2e/scenarios/test_autopilot_finish.py tests/e2e/scenarios/test_autopilot_budget.py --tb=short --no-cov
# => 22 passed in 3.22s
```

Salida exacta de la suite unitaria completa:
```
........................................................................
........................................................................
........................................................................
........................................................................
...
291 passed in 3.13s
```

## 6. Checklist de fase

- [x] Manifest incluye metadata clara.
- [x] Skills apuntan a carpeta Autopilot.
- [x] Hooks usan wrapper Python cross-platform (documentado en marketplace.md).
- [x] Documentar install/uninstall (marketplace.md + REALIZACION.md).
- [x] Versionar compatibilidad por harness (tabla en marketplace.md).
- [x] Formato compatible con ecosistema Superpowers (estructura plugin.json).
- [x] Instalación limpia en workspace nuevo (validado en tests).
- [x] Desinstalación limpia (validado en tests).
- [x] Sin dependencia externa obligatoria.

## 7. Riesgos residuales y próximos pasos

1. **Marketplace centralizado:** Actualmente los manifestos son archivos estáticos en el repo. Un marketplace real requeriría un endpoint de descarga o un registry de plugins.
2. **Compatibilidad futura con Superpowers:** Si Superpowers cambia su formato `plugin.json`, los manifestos de Cortex necesitarán una migración. Se recomienda versionar el campo `version` del manifesto de forma independiente del formato externo.
3. **Hooks solo para IDE conocidos:** Si un nuevo IDE aparece, hay que crear un nuevo adapter y un nuevo manifesto. La arquitectura actual lo permite con solo agregar un archivo.
4. **Próximo paso recomendado:** Publicar una release tag (`v0.1.0`) que incluya los manifestos, de forma que los gestores de plugins puedan apuntar a un URL estable.
