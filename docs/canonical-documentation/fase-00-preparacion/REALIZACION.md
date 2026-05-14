# Fase 00 - Preparacion - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**PRs:** (este commit)

---

## 1. Resumen

Se construyo el scaffolding del paquete `cortex/documentation/` con helpers
compartidos, jerarquia de errores e inventario del vault. Todos los gates
del plan se cumplieron.

---

## 2. Archivos creados

```text
cortex/documentation/
    __init__.py             # API publica del paquete + shim legacy
    errors.py                # 5 clases de error + base
    common.py                # 7 helpers (slugify, fingerprint, YAML, frontmatter parsing)
    inventory.py             # VaultInventory + inventory_vault + classify_path

tests/unit/documentation/
    __init__.py
    conftest.py              # 3 fixtures: tmp_vault_with_notes, tmp_vault_with_random, tmp_empty_vault
    test_errors.py           # 2 tests (jerarquia + raise/catch)
    test_common.py           # 25 tests (slugify, fingerprint, YAML, frontmatter)
    test_inventory.py        # 14 tests (inventario + classify_path)
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Shim legacy via `importlib` (en lugar de rename)

**Contexto:** al crear el paquete `cortex/documentation/`, Python lo
prefiere sobre el archivo legacy `cortex/documentation.py` (que aun
contiene `write_session_note`, `write_spec_note`, `write_tracked_item_note`).
Esto rompe 4 consumidores existentes: `cortex/services/session_service.py`,
`cortex/services/spec_service.py`, `cortex/workitems/service.py`,
`tests/unit/test_documentation.py`.

**Opcion descartada:** renombrar `cortex/documentation.py` a
`cortex/_legacy_documentation.py`. El clasificador del entorno denego la
accion por ser destructiva no autorizada.

**Decision:** cargar el archivo legacy via `importlib.util.spec_from_file_location`
desde `cortex/documentation/__init__.py` y re-exportar las tres funciones
legacy. El archivo legacy no se modifica.

**Codigo:**
```python
_legacy_path = _Path(__file__).resolve().parent.parent / "documentation.py"
if _legacy_path.exists():
    _spec = _importlib_util.spec_from_file_location(
        "cortex._documentation_legacy", str(_legacy_path)
    )
    _legacy_module = _importlib_util.module_from_spec(_spec)
    _spec.loader.exec_module(_legacy_module)
    write_session_note = _legacy_module.write_session_note
    ...
```

**Por que es legitimo:** el legacy es autocontenido (solo importa
`cortex.security.paths` y `cortex.workitems.models`); el shim no introduce
ciclos. Se elimina en Fase 04 cuando los writers canonicos toman el lugar.

**Trade-off:** un pequeno overhead al import time del paquete (~1ms).
Aceptable. Tras Fase 04 desaparece.

### 3.2 Inventario depende de strings, no de DocType enum

`cortex/documentation/inventory.py` clasifica paths via un dict
`_SUBFOLDER_TO_DOC_TYPE` que devuelve strings (no enum `DocType`).

**Razon:** mantener Fase 00 sin dependencias hacia Fase 01. El enum
`DocType` se introduce en Fase 01; el inventario solo necesita el slug
para reporte.

**Migracion futura:** Fase 11 (migration y backfill) hara `DocType(slug)`
al consumir el output del inventario.

### 3.3 `slugify` normaliza unicode (strip accents)

Decision tomada porque los slugs son filesystem-safe en multiples sistemas
y los acentos pueden generar problemas en Windows / git en algunos
escenarios. Tests verifican `Café` -> `cafe`, `Sueño` -> `sueno`.

### 3.4 `parse_frontmatter_lenient` jamas lanza excepcion

YAML malformado, archivo no existente, archivo sin frontmatter, contenido
non-mapping: todos devuelven `{}`. Razon: el inventario y la migracion
deben funcionar contra cualquier vault, incluyendo legacy con frontmatter
roto.

---

## 4. Inconvenientes encontrados

### 4.1 Conflicto paquete vs modulo del mismo nombre

**Sintoma:** al ejecutar la primera pasada de tests, `from cortex.documentation
import` fallaba con `ImportError: cannot import name 'write_session_note'`
porque Python selecciono el paquete (carpeta) sobre el modulo (archivo)
del mismo nombre.

**Resolucion:** ver decision 3.1 (shim via `importlib`).

### 4.2 Permisos del clasificador

`git mv` fue denegado. Solucion alternativa (shim) resulto mas elegante
porque preserva el archivo legacy intacto para auditoria. La eliminacion
final ocurre en Fase 12 (cleanup), donde el shim ya no es necesario.

### 4.3 Sin otros inconvenientes

Tests pasaron al primer intento despues del fix del shim. Coverage del
modulo nuevo cumple objetivo sin ajustes.

---

## 5. Tests ejecutados

```text
tests/unit/documentation/test_errors.py       2 passed
tests/unit/documentation/test_common.py      25 passed
tests/unit/documentation/test_inventory.py   14 passed
tests/unit/test_documentation.py (legacy)     6 passed
---
Total nuevos:        41 passed
Total regresion:      6 passed
Suite completa:     798 passed, 6 skipped, 0 failed (21.33s)
```

---

## 6. Coverage

```text
cortex/documentation/__init__.py        16/16    100%
cortex/documentation/common.py          57/60     95%
cortex/documentation/errors.py           7/7     100%
cortex/documentation/inventory.py       60/63     95%
---
Modulo total:                          140/146   ~96%
```

Lineas no cubiertas (`common.py:86`, `common.py:130-131`, `inventory.py:109-110`,
`inventory.py:121`) corresponden a paths de error defensivos que requieren
inyectar fallas a nivel filesystem (OSError en read_text). Coverage por
encima del objetivo de >= 95%.

---

## 7. Checklist final (del README.md de la fase)

- [x] `cortex/documentation/__init__.py` exporta API publica
- [x] `cortex/documentation/errors.py` define jerarquia de errores
- [x] `cortex/documentation/common.py` con 7 helpers
- [x] `cortex/documentation/inventory.py` con `inventory_vault` y `classify_path`
- [x] `tests/unit/documentation/test_common.py` >= 15 tests (25 implementados)
- [x] `tests/unit/documentation/test_inventory.py` >= 8 tests (14 implementados)
- [x] `tests/unit/documentation/test_errors.py` >= 2 tests (2 implementados)
- [x] Coverage del modulo `cortex/documentation/` >= 95% (96%)
- [x] `from cortex.documentation import *` no rompe
- [x] `pytest tests/unit/documentation` pasa al 100%

---

## 8. Gate de salida

- [x] `pytest tests/unit/documentation` pasa al 100%
- [x] Coverage >= 95% en `cortex/documentation/`
- [x] Modulo se importa sin side effects (excepto la carga lazy del legacy)
- [x] Suite completa sin regresion (798 passed)
- [x] `REALIZACION.md` con resumen

---

## 9. Pendientes / Backlog identificados

1. **Tests defensivos para `OSError` en `parse_frontmatter_lenient`** (3
   lineas no cubiertas). Pueden agregarse usando `monkeypatch` para forzar
   `read_text` a raise. No bloquean Fase 01.

2. **Edge case en `inventory_vault`** (linea 121): archivos `.md` directamente
   en la raiz del vault. Test podria agregarse con un fixture especifico.

Ambos son mejoras incrementales, no requeridos para el gate.

---

## 10. Proximos pasos (Fase 01)

Implementar la Capa 1 (DocType enum) y Capa 2 (schemas pydantic) segun
`fase-01-doctype-y-schema/README.md`:
- `cortex/documentation/doc_type.py` con `DocType` enum + helpers + `VALID_STATUSES`
- `cortex/documentation/data.py` con 12 dataclasses
- `cortex/documentation/schemas/` (base + 12 archivos por tipo)
- `cortex/documentation/validation.py`

El inventario de Fase 00 ya esta listo para consumir el enum cuando exista
(via `DocType(slug)` en Fase 11).
