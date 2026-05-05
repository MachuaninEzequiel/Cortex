# EPIC-04 - Hardening de paths y seguridad operativa

> Importante: marcar cada tarea completada en este archivo.
> Al cerrar la epica, completar [EPIC-04-hardening-de-paths-y-seguridad-operativa-REALIZACION.md](./EPIC-04-hardening-de-paths-y-seguridad-operativa-REALIZACION.md).

## Objetivo

Centralizar la validacion segura de paths y aplicarla a las superficies que leen o escriben sobre vault, workspace y archivos derivados de input operativo.

## Historia de usuario 1

**Como** maintainer del runtime  
**Quiero** un modulo central de seguridad de paths  
**Para** evitar que cada componente resuelva rutas con reglas distintas.

### Tarea 4.1 - Crear modulo comun de path safety

**Archivos principales a cambiar**

- `cortex/security/__init__.py`
- `cortex/security/paths.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/mcp/server.py`
- `cortex/semantic/vault_reader.py`
- `cortex/documentation.py`
- `cortex/workitems/service.py`
- `tests/unit/security/test_paths.py` o `tests/unit/test_security_paths.py`

**Checklist**

- [x] Crear una excepcion especifica para escape de ruta o violacion de root permitido.
- [x] Implementar un helper unico para unir paths bajo un root permitido.
- [x] Implementar un helper unico para validar que un path absoluto siga bajo ese root.
- [x] Dejar documentado en el modulo cuando usar `workspace_root` y cuando usar `vault_path`.

## Historia de usuario 2

**Como** maintainer de las operaciones de vault  
**Quiero** que escritura, indexado y acceso a notas usen el helper comun  
**Para** cerrar traversal y normalizar la resolucion de paths.

### Tarea 4.2 - Aplicar seguridad de paths a superficies de vault y MCP

**Archivos principales a cambiar**

- `cortex/documentation.py`
- `cortex/semantic/vault_reader.py`
- `cortex/workitems/service.py`
- `cortex/mcp/server.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/services/session_service.py` - usa `write_session_note`
- `cortex/services/spec_service.py` - usa `write_spec_note`
- `tests/unit/test_documentation.py`
- `tests/unit/semantic/test_vault_reader.py`
- `tests/integration/mcp/test_server.py`
- `tests/unit/cli/test_main.py`

**Checklist**

- [x] Hacer que `write_session_note`, `write_spec_note` y `write_tracked_item_note` escriban bajo rutas validadas.
- [x] Hacer que `VaultReader.index_file()`, `create_note()` y `update_note()` rechacen rutas fuera del vault.
- [x] Hacer que `WorkItemService.get_item_note()` y cualquier path derivado del item use validacion segura.
- [x] Revisar `_extract_candidate_files()` y cualquier otra resolucion de archivos en el MCP para impedir escapes del proyecto.
- [x] Mantener el comportamiento actual para paths validos dentro del workspace.

## Historia de usuario 3

**Como** maintainer del proyecto  
**Quiero** un documento minimo de politica y threat model  
**Para** dejar explicito el alcance de seguridad que el codigo intenta garantizar.

### Tarea 4.3 - Publicar documentacion minima de seguridad

**Archivos principales a cambiar**

- `SECURITY.md`
- `docs/security/threat-model.md`

**Dependencias que deben revisarse o corregirse por arrastre**

- `README.md` - futura referencia si se decide enlazar seguridad
- `docs/guides/getting-started.md` - futura mension si se agrega nota operativa
- `docs/vision/PLAN_CORTEX_MAXIMO_IMPACTO.md` - consistencia con el plan

**Checklist**

- [x] Crear `SECURITY.md` con alcance, politica de reporte y versiones soportadas.
- [x] Crear `docs/security/threat-model.md` con superficies, amenazas y mitigaciones implementadas.
- [x] Describir explicitamente las restricciones de paths, vault y workspace.
- [x] Registrar cualquier limitacion deliberadamente no cubierta todavia.

## Validacion de la epica

- [x] Ejecutar los tests nuevos de seguridad de paths.
- [x] Ejecutar `pytest -q tests/unit/semantic/test_vault_reader.py`.
- [x] Ejecutar `pytest -q tests/unit/test_documentation.py`.
- [x] Completar el archivo de realizacion de la epica.
