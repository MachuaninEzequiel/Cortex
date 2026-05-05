# Realizacion - EPIC-04

> Completar este archivo al terminar todos los checklists de [EPIC-04-hardening-de-paths-y-seguridad-operativa.md](./EPIC-04-hardening-de-paths-y-seguridad-operativa.md).

## Estado

- Fecha de inicio: 2026-05-05
- Fecha de cierre: 2026-05-05
- Responsable: agente autonomo de desarrollo

## Resumen ejecutivo

Se implemento un modulo central de seguridad de paths (`cortex.security.paths`) con dos helpers (`resolve_safe`, `validate_under_root`) y una excepcion especifica (`PathSecurityError`). Se aplico a todas las superficies que construyen rutas a partir de input operativo: vault reader, documentacion, workitems y MCP server. Se publico `SECURITY.md` y `docs/security/threat-model.md` con alcance, politica de reporte y mitigaciones implementadas.

## Archivos modificados

- `cortex/security/__init__.py` — export publico del modulo de seguridad
- `cortex/security/paths.py` — `resolve_safe`, `validate_under_root`, `PathSecurityError`
- `cortex/documentation.py` — validacion de rutas en `write_session_note`, `write_spec_note`, `write_tracked_item_note`
- `cortex/semantic/vault_reader.py` — validacion en `index_file`, `create_note`, `update_note`
- `cortex/workitems/service.py` — validacion en `get_item_note`
- `cortex/mcp/server.py` — `_extract_candidate_files` reescrito con `resolve_safe`
- `tests/unit/security/test_paths.py` — tests parametrizados de traversal y paths absolutos
- `SECURITY.md` — politica de seguridad y versiones soportadas
- `docs/security/threat-model.md` — superficies, amenazas (T1-T4) y mitigaciones

## Validaciones ejecutadas

- `pytest -q tests/unit/security/test_paths.py` — 10 passed
- `pytest -q tests/unit/test_documentation.py` — 3 passed
- `pytest -q tests/unit/semantic/test_vault_reader.py` — 8 passed
- `pytest -q tests/integration/mcp/test_server.py` — 6 passed
- `pytest -q` (suite completa) — 395 passed, 6 skipped, 0 failed

## Decisiones tomadas

- **Excepcion especifica `PathSecurityError`** hereda de `ValueError` para que los callers puedan capturarla explicitamente o como ValueError generico.
- **`resolve_safe` rechaza paths absolutos en el componente rel**: esto evita que un input como `/etc/passwd` sea tratado como relativo.
- **No se modificaron `SessionService` ni `SpecService` directamente**: ellos delegan a `write_session_note` y `write_spec_note`, que ahora validan internamente. Esto evita duplicar logica.
- **`VaultReader.create_note` valida `subfolder`**: aunque el `title` ya se limpia via regex, `subfolder` es input directo del usuario y puede contener `../`.
- **Symlinks**: se documento en el threat model que `resolve_safe` usa `Path.resolve()`, que sigue symlinks. Un symlink dentro del vault que apunte fuera sera detectado como escape, pero esto es una defensa de mejor esfuerzo.

## Pendientes o riesgos abiertos

- Ninguno para esta epica. La superficie de paths queda centralizada y validada.
