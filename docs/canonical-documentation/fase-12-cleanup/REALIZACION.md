# Fase 12 - Cleanup - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~30 minutos
**Estado:** Completado parcialmente (eliminaciones destructivas a Fase 13)
**Dependencias cumplidas:** Fase 11

---

## 1. Resumen

Fase 12 cierra la deuda estructural de la iniciativa canonical-documentation
en lo que se puede tocar sin autorizacion destructiva:

1. **Setup orchestrator actualizado** (`cortex/setup/orchestrator.py`):
   las 12 carpetas canonicas se crean automaticamente en `cortex setup`
   en vez de las 6 + ghosts del layout legacy.

2. **Documenter canonico** (`.cortex/subagents/cortex-documenter.md`):
   se agrego al inicio una **tabla de routing canonica** que mapea
   "que quiero documentar" a `doc_type` + `write_*_note` MCP function.

3. **Tests del setup canonico** verifican que las 12 carpetas estan
   declaradas y que `DOC_TYPE_ROUTING` cubre la misma lista (sin huerfanos
   en ninguna direccion).

Lo que NO se hizo en Fase 12 (y se difirio a Fase 13 bloque A) es la
eliminacion de archivos legacy:
- `cortex/documentation.py` (huerfano desde Fase 04).
- `cortex-pi/.pi/agents/cortex-documenter.md` (legacy duplicado).
- Migracion de los 4 consumidores de `_legacy_shims.py`.

Estos items requieren `git rm` o equivalente y se ejecutan bajo
autorizacion explicita del operador.

---

## 2. Archivos modificados / nuevos

```text
Modificados:
    cortex/setup/orchestrator.py            # dirs[] -> 12 carpetas canonicas
    .cortex/subagents/cortex-documenter.md  # +tabla de routing al inicio

Nuevos:
    tests/unit/setup/test_canonical_folders.py    # 3 tests
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Setup orchestrator declarativo

La lista `dirs[]` en `_create_directories` paso de 6 entradas a 12,
matching exacto con `DOC_TYPE_ROUTING.subfolder` de cada DocType (con
`decisions` deduplicado entre ADR y DECISION).

Se garantiza con un test (``test_no_dead_subfolders_in_routing``) que
ambas listas (`dirs[]` en orchestrator + subfolders de
`DOC_TYPE_ROUTING`) coinciden exactamente. Cualquier divergencia futura
falla el test.

### 3.2 Documenter canonico se EXTIENDE, no se reemplaza

El prompt existente del documenter (HIGH-SIGNAL MODE + Reference >
Duplicate) sigue vigente. Solo se agrega al INICIO una tabla de routing
canonica para que el subagente sepa que `write_*_note` invocar segun el
caso de uso.

Decision: NO eliminar la version legacy de cortex-pi
(`cortex-pi/.pi/agents/cortex-documenter.md`). Esa eliminacion es
destructiva y queda en Fase 13 bloque A.

### 3.3 Test del orchestrator inspecciona el source

`test_orchestrator_directories_list_matches_canonical` lee
`cortex/setup/orchestrator.py` como string y busca cada literal de
`vault_path / "<subfolder>"`. Esto es fragil (cambios de formato lo
rompen) pero garantiza que la lista no se modifica accidentalmente.

Mejor opcion futura: refactorizar el orchestrator para que llame a
`cortex.documentation.routing.list_canonical_subfolders()`. Queda como
mejora.

---

## 4. Tests ejecutados

```text
tests/unit/setup/test_canonical_folders.py    3 passed
---
Fase 12 nuevos:                                3 passed
Suite global:                              1310 passed, 6 skipped, 0 fallas
```

---

## 5. Checklist final

- [x] Setup orchestrator declara 12 carpetas canonicas
- [x] Test garantiza paridad con `DOC_TYPE_ROUTING`
- [x] Documenter canonico tiene tabla de routing
- [ ] `cortex/documentation.py` eliminado - Fase 13 bloque A
- [ ] `cortex-pi/.pi/agents/cortex-documenter.md` eliminado - Fase 13 bloque A
- [ ] Consumidores migrados fuera de `_legacy_shims.py` - Fase 13 bloque A
- [ ] Gate global ejecutado y aprobado - Fase 13 al cierre total
- [ ] Sembrar seed inicial por carpeta canonica - mejora futura

---

## 6. Pendientes / Backlog

Toda la deuda no resuelta de Fase 12 se consolido en Fase 13 (bloque A).
Ver `../fase-13-backlog-consolidado/README.md` para el detalle.

---

## 7. Proximos pasos

Fase 13 (Backlog Consolidado) cierra todos los pendientes acumulados de
las 12 fases en un solo plan + desarrollo del subset no-destructivo.
