# Fase 10 - Enterprise Extensions - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**Dependencias cumplidas:** Fases 01-08

---

## 1. Resumen

Se implementaron las extensiones enterprise del schema canonico:

1. **Multi-tenant governance** (`cortex/enterprise/governance.py`):
   resolucion de teams + permisos `can_promote`/`can_review` + visibilidad
   por classification + helpers `assert_can_promote`/`assert_can_review`.

2. **Retention policies** (`cortex/enterprise/maintenance.py`):
   `scan_retention_violations` + `archive_violations` con archive a
   `<vault>/_archived/<rel_path>`. Lectura del retention_days desde
   frontmatter o defaults del `RetentionPolicy` por DocType.

3. **Promotion DocType-aware** (`cortex/enterprise/promotion_doctype.py`):
   `promote_note_doctype_aware` honra `RouteSpec.promotion_mode`:
   - `as-is` -> copia integral.
   - `summarize` -> sintesis para SESSION (Key Decisions + Verified State).
   - `review-required` -> copia con `status=draft`.
   Incluye gate de severity para INCIDENT (rechaza `low`), audit_trail
   con evento `promoted` apendice, y respeto a `governance` (rechaza
   actors sin permiso).

4. **`EnterpriseOrgConfig` extendido** (`cortex/enterprise/models.py`):
   + `teams` (list[TeamConfig]).
   + `classifications` (Literal: public/internal/confidential).
   + `policies` (EnterprisePolicies con `confidential_visible_to`).
   + `retention_defaults` (RetentionPolicy con 12 entradas por DocType).
   Todos opcionales (default empty) para preservar backwards-compat.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/enterprise/governance.py             # 150 LOC
    cortex/enterprise/maintenance.py            # 160 LOC
    cortex/enterprise/promotion_doctype.py      # 300 LOC
    tests/unit/enterprise/test_governance.py    # 22 tests
    tests/unit/enterprise/test_promotion_doctype.py  # 16 tests
    tests/unit/enterprise/test_maintenance.py   # 13 tests

Modificados:
    cortex/enterprise/models.py    # +TeamConfig, +RetentionPolicy, +EnterprisePolicies
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Modulo nuevo `promotion_doctype.py` en lugar de modificar `knowledge_promotion.py`

El legacy `knowledge_promotion.py` es 338 LOC con su propio modelo de
estados (`PromotionRecord`, `PromotionDecision`). Modificarlo riesgo de
romper consumidores existentes (records.jsonl, CLI legacy). Decision:
crear un modulo separado que coexiste y pueda ser usado opt-in por el
pipeline canonico.

### 3.2 `ADMIN_TEAM` como sentinel string

Hardcoded `"admin"` como nombre del team con acceso total. Permite:
- Tests sin tener que configurar un team explicitamente.
- Caller pasa actor="admin" y obtiene visibilidad completa de
  classifications.

### 3.3 Incident severity gate dentro de `promote_note_doctype_aware`

Decision: severity=`low` bloquea promotion. severity={medium,high,critical}
permite. Esto evita ruido en el vault enterprise sin requerir politica
externa.

### 3.4 Audit trail append, no reemplazo

El frontmatter pasa con su `audit_trail` existente; la funcion AGREGA un
evento `"promoted"` al final. Idempotencia: promover el mismo doc dos
veces produce dos eventos distinct.

### 3.5 Retention defaults segun `RouteSpec.auto_expire_days`

Inicialmente queria leer `auto_expire_days` desde la routing table, pero
los plazos enterprise son distintos (regulatorios). Decision: dos
campos separados — `routing.auto_expire_days` para soft-warning local,
`RetentionPolicy.<doc_type>` para hard-archive enterprise.

---

## 4. Tests ejecutados

```text
tests/unit/enterprise/test_governance.py         22 passed
tests/unit/enterprise/test_promotion_doctype.py  16 passed
tests/unit/enterprise/test_maintenance.py        13 passed
---
Fase 10 nuevos:                                  51 passed
Suite global:                                  1281 passed, 6 skipped, 0 fallas
```

---

## 5. Coverage

```text
cortex/enterprise/governance.py          ~95%  (defensive paths)
cortex/enterprise/maintenance.py         ~95%
cortex/enterprise/promotion_doctype.py   ~93%
cortex/enterprise/models.py              extension cubierta por tests existentes
```

---

## 6. Checklist final

- [x] `EnterpriseOrgConfig` extendido con teams/classifications/policies/retention_defaults
- [x] `governance.py` con permissions + visibility
- [x] `maintenance.py` con retention scan + archive
- [x] `promotion_doctype.py` con 3 modos + governance + audit_trail
- [x] Tests >= 30 (51 implementados)
- [x] Coverage >= 90%
- [ ] CLI `cortex review-knowledge` - postergado a Fase 13 (bloque D)

---

## 7. Pendientes / Backlog

1. **CLI `cortex review-knowledge`** con subcomandos pending/approve/reject
   para revisar manualmente los runbooks promovidos con `status=draft`.
   Documentado en Fase 13 bloque D.

2. **Wire-up con el orchestrator de setup**: cuando un user hace
   `cortex setup enterprise --preset regulated-organization`, el setup
   deberia precargar la seccion teams con al menos un admin team. Se
   puede agregar despues sin breaking change.

---

## 8. Proximos pasos

Fase 11 (Migration y Backfill) ya esta lista para consumir
`EnterpriseOrgConfig` cuando un operador haga
`cortex docs migrate --vault-scope=enterprise --project-id=foo`
(actualmente no soportado en el CLI; queda como mejora futura).
