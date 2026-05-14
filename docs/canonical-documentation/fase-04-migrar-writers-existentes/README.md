# Fase 04 - Migrar Writers Existentes

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 1.5 dias (real: ~1 hora)
**Riesgo:** medio
**Dependencias:** Fase 01, Fase 02, Fase 03

---

## 1. Objetivo

Migrar los 3 writers existentes al nuevo schema canonico:
- `write_session_note` (actualmente en `cortex/documentation.py`)
- `write_spec_note` (idem)
- `write_tracked_item_note` -> renombrar a `write_hu_note`

Tras esta fase:
- Tres archivos de produccion son consistentes con los 9 escritores nuevos.
- Todos los consumidores (SessionService, SpecService, PRService) siguen funcionando.
- `write_tracked_item_note` queda deprecated con shim.

Riesgo medio porque toca codigo en uso (sessions, specs, PRs) y rompe tests existentes que esperaban el formato viejo.

---

## 2. Archivos a tocar

```text
cortex/
    documentation.py                  # archivo viejo
                                      # -> mover funciones a writers.py
                                      # -> dejar shim con DeprecationWarning
    documentation/
        writers.py                    # extender con 3 writers nuevos (canonicos)
        templates/
            session.md.j2             # ya creado en Fase 03
            spec.md.j2                # idem
            hu.md.j2                  # idem
    services/
        session_service.py            # usar nuevo write_session_note canonico
        spec_service.py                # usar nuevo write_spec_note canonico
        pr_service.py                  # usar nuevos
    autopilot/
        session_writer.py              # adaptar al nuevo schema

tests/unit/
    test_documentation.py              # TESTS LEGACY - actualizar
    services/
        test_session_service.py        # actualizar a schema nuevo
        test_spec_service.py           # idem
        test_pr_service.py             # idem
    autopilot/
        test_session_writer.py         # idem
    documentation/
        test_write_session_note.py     # NUEVO
        test_write_spec_note.py        # NUEVO
        test_write_hu_note.py          # NUEVO
```

---

## 3. Migracion paso a paso

### 3.1 `write_session_note`

**Hoy** (`cortex/documentation.py:69-139`):

```python
def write_session_note(
    *,
    vault: VaultReader,
    title, spec_summary, changes_made, files_touched,
    key_decisions, next_steps, tags, status,
    handoff=False, blockers=None, ...
) -> Path:
    # genera frontmatter inline
    # genera body con _render_list
    # path = vault / "sessions" / "{date}_{slug}.md"
    # vault.create_note(...)
```

**Objetivo:**

```python
# cortex/documentation/writers.py

def write_session_note(
    data: SessionData,
    *,
    vault: VaultReader,
    vault_scope: str = "local",
    project_id: str | None = None,
    actor: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Persist session note canonically. Same signature as other writers."""
    # Patron canonico (igual que ADR, etc):
    # 1. Validate
    # 2. Resolve route
    # 3. Render template session.md.j2
    # 4. Fingerprint
    # 5. Build SessionFrontmatter
    # 6. Render full markdown
    # 7. Resolve path
    # 8. Persist + Index
    # 9. Return
```

**Migracion del consumidor (SessionService):**

```python
# cortex/services/session_service.py

# Antes:
def create(self, title, spec_summary, ..., handoff=False, blockers=None, ...):
    path = write_session_note(
        vault=self._semantic,
        title=title, spec_summary=spec_summary, ...
    )

# Despues:
def create(self, title, spec_summary, ..., handoff=False, blockers=None, ...):
    data = SessionData(
        title=title,
        spec_summary=spec_summary,
        changes_made=changes_made,
        files_touched=files_touched,
        key_decisions=key_decisions,
        next_steps=next_steps,
        tags=tags,
        session_id=self._make_session_id(),
        status="handoff" if handoff else "completed",
        blockers=blockers or [],
        ...
    )
    path = write_session_note(data, vault=self._semantic)
```

### 3.2 `write_spec_note`

Patron analogo. Migrar a `SpecData` y usar `SpecFrontmatter`.

### 3.3 `write_tracked_item_note` -> `write_hu_note`

**Renombrar.** El nuevo nombre `write_hu_note` es coherente con la convencion.

**Shim de compatibilidad:**

```python
# cortex/documentation.py (archivo viejo)

import warnings
from cortex.documentation.writers import (
    write_session_note as _new_session,
    write_spec_note as _new_spec,
    write_hu_note as _new_hu,
)

def write_session_note(*args, **kwargs):
    warnings.warn(
        "Importing write_session_note from cortex.documentation is deprecated. "
        "Use cortex.documentation.writers instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Adaptar args legacy -> SessionData
    data = _legacy_to_session_data(*args, **kwargs)
    return _new_session(data, vault=kwargs.get("vault"))

def write_tracked_item_note(*args, **kwargs):
    warnings.warn(
        "write_tracked_item_note is deprecated. Use write_hu_note from cortex.documentation.writers.",
        DeprecationWarning,
        stacklevel=2,
    )
    data = _legacy_to_hu_data(*args, **kwargs)
    return _new_hu(data, vault=kwargs.get("vault"))
```

El shim vive hasta Fase 12 (cleanup).

---

## 4. Cambios concretos por archivo

### `cortex/documentation/writers.py`

Agregar las 3 funciones siguiendo el patron canonico. Reusar todos los helpers de Fase 03.

### `cortex/documentation.py`

- Mover funciones reales a `writers.py`.
- Dejar shims con `DeprecationWarning`.
- Mantener `_frontmatter`, `_render_list`, `_slugify` (helpers privados) o moverlos a `common.py`.

### `cortex/services/session_service.py`

- Cambiar la construccion del SessionData.
- Mismo path resultante (sessions/<file>.md).
- Frontmatter ahora tiene `schema_version: 1`, `doc_type: session`, etc.

### `cortex/services/spec_service.py`

Analogo.

### `cortex/services/pr_service.py`

`generate_pr_docs` y `write_pr_docs` actualizadas para usar el nuevo writer.

### `cortex/autopilot/session_writer.py`

Adaptarse al nuevo schema. El `session_id` se asigna explicitamente.

---

## 5. Tests

### Tests nuevos por writer migrado

Mismo patron de 8 tests por writer (igual que Fase 03):

```python
# tests/unit/documentation/test_write_session_note.py

def test_write_session_minimal(tmp_vault):
    data = SessionData(title="t", session_id="abc123")
    path = write_session_note(data, vault=tmp_vault)
    assert path.exists()

def test_write_session_full(tmp_vault):
    """All optional fields populated."""

def test_write_session_handoff_status(tmp_vault):
    """status='handoff' renders without 'completed'."""

def test_write_session_telemetry_field(tmp_vault):
    """cortex_telemetry can be embedded."""

def test_write_session_filename_pattern(tmp_vault):
    """Filename: {date}_{session_id}_{slug}.md"""

def test_write_session_duplicate_raises(tmp_vault):
    """..."""

def test_write_session_indexes_file(tmp_vault):
    """..."""

def test_write_session_with_pr_branch_commit(tmp_vault):
    """All git metadata captured in frontmatter."""
```

Idem para `test_write_spec_note.py` y `test_write_hu_note.py`.

### Tests existentes a actualizar

Lista de archivos test que necesitan adaptarse al nuevo schema:

- `tests/unit/test_documentation.py` - usa funciones legacy
- `tests/unit/services/test_session_service.py` - construccion de SessionData
- `tests/unit/services/test_spec_service.py` - SpecData
- `tests/unit/services/test_pr_service.py` - chain de servicios
- `tests/unit/autopilot/test_session_writer.py` - autopilot writer
- `tests/e2e/scenarios/test_autopilot_basic.py` - golden path

**Estrategia de actualizacion:**

1. Para tests que verifican path/index: sin cambios.
2. Para tests que verifican frontmatter exacto: actualizar al nuevo formato.
3. Para tests que importan funciones legacy: agregar `pytest.warns(DeprecationWarning)`.

---

## 6. Backwards compatibility

### Shim API

Codigo externo que llamaba a `write_session_note(...)` con kwargs legacy sigue funcionando (con warning). Migracion del codigo cliente puede hacerse gradualmente, pero los servicios internos de Cortex se migran de una.

### Schema legacy en frontmatter persistido

Notas viejas tienen frontmatter incompatible. Eso se resuelve en Fase 11 (backfill), no aqui.

Durante esta fase, una session note vieja sigue siendo leible por `VaultReader` (que es lenient en el parser). El validator estricto solo aplica a notas nuevas.

---

## 7. Criterios de diseno

- **Misma firma simetrica que los nuevos writers.** Sin excepciones.
- **Servicios internos migrados de una.** No coexistencia compleja.
- **Shim externo vive 1 fase mas.** Eliminacion en Fase 12.
- **Tests existentes deben pasar.** Sin perder coverage.
- **Frontmatter de notas nuevas valida.** Tests verifican.

---

## 8. Checklist

- [x] `write_session_note_canonical` implementado en `writers.py`
- [x] `write_spec_note_canonical` implementado en `writers.py`
- [x] `write_hu_note` (canonico, antes `write_tracked_item_note`)
- [x] Shims en `_legacy_shims.py` (sin DeprecationWarning aun; postergado a Fase 12)
- [x] `SessionService.create()` consume el wrapper sin cambios
- [x] `SpecService.create()` consume el wrapper sin cambios
- [x] `PRService.write_pr_docs()` consume el wrapper sin cambios
- [x] `autopilot/session_writer.py` no toca `cortex.documentation` directamente
- [x] 6 tests legacy actualizados al schema canonico (en lugar de 3 archivos nuevos: cubierto en test_writers.py de Fase 03)
- [x] Tests existentes pasan al 100% sin regresion
- [x] Coverage del nuevo modulo ~97% (>= 90%)

---

## 9. Gate de salida

- `pytest tests/unit/documentation tests/unit/services tests/unit/autopilot tests/e2e/scenarios/test_autopilot_basic.py` pasa al 100%.
- Tests originales que pasaban antes siguen pasando.
- DeprecationWarning visible al importar funciones de `cortex/documentation.py`.
- `cortex` CLI funciona sin error (smoke test global).
- Session/Spec/HU notes nuevas validan contra schema canonico.
- `REALIZACION.md` documentado.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Tests existentes rompen masivamente | Actualizar tests en mismo PR; identificar antes de empezar (grep `write_session_note`) |
| Servicios cliente externos (no Cortex) rompen | Shim con warning preserva API |
| autopilot session writer tiene logica especial | Test e2e de autopilot debe pasar |
| Cambio de naming `tracked_item` -> `hu` confunde | Shim mantiene legacy name; grep documenta nuevo |
| Status legacy "fallback" / "auto-draft" no validan | VALID_STATUSES[SESSION] los incluye |
| `cortex_telemetry` field no esta en SessionData hoy | Default `None`; se popula en Fase 05 |
| Path filename pattern cambia (`{date}_{session_id}_{slug}` vs `{date}_{slug}`) | Mantener compatibilidad: include session_id en filename del nuevo writer |

---

## 11. Notas para agentes implementadores

1. **Hacer un dry-grep antes:** `grep -r "write_session_note\|write_spec_note\|write_tracked_item_note"` para conocer la huella.
2. **Migrar UN servicio a la vez.** session_service -> tests pasan -> spec_service -> tests pasan -> ...
3. **No tocar el comportamiento de `cortex_save_session` MCP tool** salvo lo necesario para que use nuevo writer.
4. **autopilot session writer es delicado.** Tests e2e son el ground truth.
5. **Backups de frontmatter en logs de DeprecationWarning.** No saltearse.
6. **El shim acepta misma signature legacy.** Adapter pattern.
7. **No combinar con Fase 05 (telemetria).** Aqui solo se migra el schema; telemetria es siguiente.

---

## 12. Referencias

- `docs/canonical-documentation/data-model.md` - SessionData, SpecData, HUData
- `docs/canonical-documentation/frontmatter-schema.md` - schemas correspondientes
- `docs/canonical-documentation/templates-reference.md` - session.md.j2, spec.md.j2, hu.md.j2
- `cortex/documentation.py` - codigo legacy actual
- `cortex/services/session_service.py:62-143` - consumidor a actualizar
