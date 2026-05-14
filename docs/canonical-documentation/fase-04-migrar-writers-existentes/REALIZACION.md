# Fase 04 - Migrar Writers Existentes - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**Dependencias cumplidas:** Fase 00, 01, 02, 03

---

## 1. Resumen

Se migraron los 3 writers legacy (`write_session_note`, `write_spec_note`,
`write_tracked_item_note`) al schema canonico via dos pasos:

1. **3 nuevos writers canonicos** en `cortex/documentation/writers.py` con
   firma simetrica a los otros 9 (`SessionData`/`SpecData`/`HUData` + kwargs).

2. **3 wrappers de compatibilidad** en `cortex/documentation/_legacy_shims.py`
   que preservan la firma legacy (`vault_path: str | Path` + muchos kwargs)
   y delegan a los canonicos.

El shim de `importlib` introducido en Fase 00 se elimino: el archivo legacy
`cortex/documentation.py` queda huerfano en disco hasta Fase 12 cleanup.

Los 12 writers canonicos estan ahora vinculados al `DOC_TYPE_ROUTING`.
La tabla esta completa: cada DocType tiene su writer asignado.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/documentation/_legacy_shims.py    # 172 LOC: 3 wrappers backwards-compatible

Modificados:
    cortex/documentation/writers.py          # +3 funciones canonicas + branches en helpers
    cortex/documentation/__init__.py          # remove importlib shim, import _legacy_shims,
                                              # bind 3 nuevos writers al routing
    tests/unit/test_documentation.py         # 6 tests actualizados al schema canonico

Sin cambios:
    cortex/documentation.py                  # legacy original, ya no se importa
    cortex/services/session_service.py        # consume el shim wrapper
    cortex/services/spec_service.py           # idem
    cortex/services/pr_service.py             # idem
    cortex/workitems/service.py               # idem (lazy import)
    cortex/autopilot/session_writer.py        # no toca cortex.documentation directamente
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Tres canonicos + tres wrappers (en vez de migrar consumidores)

**Decision:** mantener la firma legacy de `write_session_note`,
`write_spec_note`, `write_tracked_item_note` via wrappers en
`_legacy_shims.py`. Los consumidores (services, workitems, tests) NO se
modifican.

**Alternativa rechazada:** migrar los consumidores a la firma canonica
(pasar `SessionData` en lugar de kwargs). Habria sido mas trabajo y mayor
riesgo: 4 archivos consumidores + tests asociados.

**Trade-off:** los wrappers viven hasta Fase 12 cleanup. Aceptable. La
disciplina de API canonica se mantiene en `writers.py`; los wrappers son
explicitamente "legacy".

### 3.2 `_PathOnlyVault` para wrappers legacy

Los wrappers reciben `vault_path: str | Path`, no un VaultReader. Para
delegar al canonico (que requiere `VaultLike`), envolvemos el path en una
clase minima `_PathOnlyVault` que NO indexa.

**Consecuencia:** los archivos creados via wrapper legacy NO se indexan
automaticamente. Los consumidores reales (SessionService, etc.) ya tienen
su propio paso de indexacion (`self._semantic.index_file(rel_path)` en
`session_service.py:125`), por lo que esto preserva el comportamiento
historico (donde tampoco indexaba la funcion legacy en `cortex/documentation.py`).

### 3.3 Mapeo `legacy_status -> canonical_status` en wrappers

- Session: `handoff=True` -> `status="handoff"` (valido en SESSION canonico).
- Session: `handoff=False` -> `status="completed"` (canonico) en lugar de
  legacy `"generated"`. Razon: `"generated"` no esta en `VALID_STATUSES[SESSION]`.
- HU: `"imported"` -> `"backlog"`, `"in_progress"` -> `"in-progress"`. Los
  valores legacy no son validos en HU canonico.

Tests legacy ajustados para verificar el nuevo status.

### 3.4 Eliminar el shim de `importlib` de Fase 00

Ya no es necesario porque los wrappers en `_legacy_shims.py` proveen las
3 funciones publicas con firma compatible. El archivo legacy
`cortex/documentation.py` queda huerfano: nadie lo importa.

**Riesgo:** si algun consumidor externo (fuera de Cortex) hace
`import cortex.documentation as m; m.write_session_note(...)`, sigue
funcionando porque las 3 funciones estan en el paquete via re-export desde
`_legacy_shims.py`.

### 3.5 Tests legacy: actualizar al schema canonico (no agregar warnings)

El plan original ofrecia 3 opciones para tests legacy:
1. Sin cambios (path/index).
2. Actualizar al nuevo formato.
3. Agregar `pytest.warns(DeprecationWarning)`.

Elegi **opcion 2** para los 6 tests porque:
- No emitimos DeprecationWarning aun (Fase 12 lo decide).
- El formato del schema canonico es estructuralmente equivalente al
  legacy; los tests siguen verificando comportamiento real.

Los 6 tests actualizados verifican:
- `path.parent.name == "sessions"` / `"specs"` / `"hu"` (subfolder canonico)
- `parse_frontmatter_lenient(path)` (frontmatter cliente-agnostico)
- `fm["doc_type"]`, `fm["status"]`, `fm["external_id"]`, etc.
- Body markers como `"Replace cortex-work with..."` (contenido tematico)

---

## 4. Inconvenientes encontrados

### 4.1 `_build_filename_context` faltaba branches para SESSION/SPEC/HU

**Sintoma:** primer corrida de tests legacy fallaba con
`RoutingError: Missing placeholders for hu filename: ['external_id']`.

**Causa:** en Fase 03 implementamos las branches para los 9 tipos nuevos,
pero olvidamos SESSION/SPEC/HU porque sus writers iban a llegar en Fase 04.

**Resolucion:** agregar 3 branches:
```python
elif doc_type == DocType.SESSION:
    ctx["session_id"] = data.session_id
elif doc_type == DocType.SPEC:
    pass
elif doc_type == DocType.HU:
    ctx = {"external_id": data.external_id}
```

### 4.2 `_type_specific_fields` faltaba branches para SESSION/SPEC

**Sintoma:** segundo round fallaba con
`SchemaValidationError: session_id field required`.

**Causa:** misma omision; `_type_specific_fields` no sabia que para SESSION
hay que copiar `session_id`, `pr`, `branch`, `commit`, `cortex_telemetry`.

**Resolucion:** agregar branches SESSION y SPEC al final del helper.

### 4.3 Tests legacy verificaban formato YAML exacto

**Sintoma:** tests esperaban strings literales como
`'external_id: "PROJ-123"'` (con comillas), `"status: generated"`,
`"tags: [session, release, handoff]"` (flow style).

**Causa:** el schema canonico produce YAML en block style sin comillas
auto (PyYAML decide), y los status legacy ("generated") no son canonicos.

**Resolucion:** actualizar los 6 tests para usar `parse_frontmatter_lenient`
y verificar campos estructuralmente, no por string match exacto.

---

## 5. Tests ejecutados

```text
tests/unit/test_documentation.py (legacy)      6 passed (actualizados)
tests/unit/documentation/                    210 passed (sin cambios)
---
Modulo + legacy:                              216 passed
Suite unit completa:                          958 passed, 6 skipped
Suite integration:                             83 passed
Suite e2e:                                     80 passed
---
TOTAL:                                       1121 passed, 6 skipped, 0 fallas
```

**Cero regresion** en ningun test pre-existente. Los servicios
(SessionService, SpecService, PRService, workitems.service, autopilot
session writer) consumen los wrappers sin cambios.

---

## 6. Coverage

```text
cortex/documentation/__init__.py            22/22  100%
cortex/documentation/_legacy_shims.py        40/41  98%   (linea 156: synced_at tz fallback)
cortex/documentation/writers.py             204/213 96%   (9 lineas defensive)
cortex/documentation/audit.py                10/10  100%
cortex/documentation/templates_engine.py     15/15  100%
cortex/documentation/data.py                130/130 100%
cortex/documentation/doc_type.py             47/47  100%
cortex/documentation/errors.py                7/7   100%
cortex/documentation/inventory.py            60/63  95%
cortex/documentation/routing.py              61/61  100%
cortex/documentation/validation.py            ~     100%
cortex/documentation/schemas/*               ~97%
---
Modulo cortex/documentation/ total:         ~97%

cortex/documentation.py (legacy huerfano):    0%   (no se importa)
```

El archivo `cortex/documentation.py` (legacy) tiene 0% coverage porque ya no
se carga. Esta huerfano hasta Fase 12 cleanup.

Coverage del modulo nuevo: **~97%**, supera el objetivo del gate.

---

## 7. Checklist final (del README de la fase)

- [x] `write_session_note_canonical` implementado en `writers.py`
- [x] `write_spec_note_canonical` implementado en `writers.py`
- [x] `write_hu_note` implementado en `writers.py` (renombrado de tracked_item)
- [x] Shims en `_legacy_shims.py` con firma legacy para compat
- [x] `__init__.py` re-exporta los 3 wrappers legacy bajo nombres originales
  (`write_session_note`, `write_spec_note`, `write_tracked_item_note`)
- [x] `SessionService.create()` usa el wrapper (sin cambios al codigo del servicio)
- [x] `SpecService.create()` usa el wrapper (sin cambios)
- [x] `PRService.write_pr_docs()` usa el wrapper (sin cambios)
- [x] `cortex/workitems/service.py` usa el wrapper (sin cambios)
- [x] `cortex/autopilot/session_writer.py` no toca `cortex.documentation` directamente
- [x] Tests existentes (`tests/unit/test_documentation.py`) actualizados al schema canonico (6/6)
- [x] Tests legacy + suite unit completa pasan al 100%
- [x] Tests integration + e2e pasan al 100%
- [x] Coverage del nuevo modulo >= 90% (~97%)

---

## 8. Gate de salida

- [x] `pytest tests/unit/documentation tests/unit/test_documentation.py` pasa al 100% (216/216)
- [x] `pytest tests/unit tests/integration tests/e2e` pasa al 100% (1121/1121)
- [x] DeprecationWarning NO se emite aun (decision: queda para Fase 12)
- [x] `cortex` CLI funciona sin error (smoke test global)
- [x] Session/Spec/HU notes nuevas validan contra schema canonico
- [x] 12 writers asignados al routing table (todos los DocType)
- [x] `REALIZACION.md` documentado

---

## 9. Pendientes / Backlog identificados

1. **`cortex/documentation.py` huerfano en disco.** No se carga, pero el
   archivo existe. Eliminacion programada para Fase 12 cleanup. El
   clasificador denego el rename inicial; el plan es eliminarlo con `git rm`
   en Fase 12 una vez confirmado que ningun consumidor lo referencia.

2. **DeprecationWarning en wrappers legacy.** El plan original mencionaba
   emitir warnings. Decision: postergar hasta Fase 12 para no contaminar
   la build con warnings antes de eliminar el archivo legacy.

3. **`_legacy_shims.py:156`** (1 linea sin cubrir): rama defensive para
   `synced_at` sin timezone. No bloqueante; defensive coverage.

4. **`writers.py:120, 125-126, 297, 346-347, 595, 631, 633`** (9 lineas):
   mayoria defensive paths. Coverage 96% suficiente.

5. **Test flaky `tests/unit/autopilot/test_service.py::TestStatus::test_latest_session`**
   sigue presente. NO es regresion de esta fase. Documentado en Fase 01.

---

## 10. Proximos pasos (Fase 05)

Implementar telemetria in-vault segun
`fase-05-telemetria-in-vault/README.md`:

- `cortex/context_enricher/telemetry.py` con `PersistentObserver`.
- Integracion del observer con `ContextEnricher.enrich()` via callback.
- Captura del bloque `cortex_telemetry` en `SessionFrontmatter` (ya
  definido en Fase 01 - `CortexTelemetry` pydantic model).
- Extension de `SessionService.create()` para aceptar `cortex_telemetry`.
- Citation detection (parsing del body por wiki-links).
- Comando `cortex memory-report` extendido.
- Tests >= 20.

---

## 11. Estado final del modulo `cortex.documentation` tras Fase 04

```text
DocType (Enum)              -> 12 valores cerrados
Dataclasses (data.py)       -> 12 dataclasses (Session/Handoff/Spec/ADR/Decision/
                                Incident/Postmortem/Runbook/Architecture/Changelog/
                                HU/GlossaryEntry)
Pydantic schemas            -> 12 local + 12 enterprise + AuditEvent + CortexTelemetry
DOC_TYPE_ROUTING            -> 12 entries, TODAS con writer asignado
Canonical writers           -> 12 funciones simetricas en writers.py
Legacy shims                -> 3 wrappers en _legacy_shims.py (backwards-compat)
Templates Jinja2            -> 12 archivos .md.j2
CLI                          -> cortex docs routing-table (con --json y --doc-type)
Errors                       -> 5 clases + base
Common helpers               -> 7 funciones (slugify, fingerprint, YAML, frontmatter)
Inventory                    -> VaultInventory + inventory_vault + classify_path
Validation                   -> validate_frontmatter + validate_path_frontmatter
Templates engine             -> render_template (Jinja2)
Audit                        -> append_audit_event para enterprise

Total LOC nuevo:             ~1700
Total tests Fase 00-04:       216 module + 6 legacy + 0 regresion
Coverage modulo:              ~97%
```

Fase 04 cierra la primera etapa de la iniciativa canonical-documentation
(Fases 00 a 04). El motor de escritura canonica esta operativo y todos
los consumidores existentes siguen funcionando sin cambios. Las proximas
fases (05-12) construyen sobre este cimiento: telemetria, vectorizacion
inteligente, retrieval con filtros, enterprise extensions y migracion del
vault actual.
