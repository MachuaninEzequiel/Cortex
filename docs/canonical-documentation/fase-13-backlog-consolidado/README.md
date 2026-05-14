# Fase 13 - Backlog Consolidado

**Fuente:** consolidacion de los `REALIZACION.md` de Fases 00 a 12
**Estado:** Pendiente de ejecucion (ver `REALIZACION.md` para el subset ya implementado)
**Esfuerzo estimado:** 1.5 dias
**Riesgo:** medio (mezcla mejoras incrementales con eliminaciones destructivas)

---

## 1. Objetivo

Cerrar **todos los items que las Fases 00-12 marcaron como "pendiente"** en
un solo paso. Esta fase es la limpieza final de la iniciativa
canonical-documentation: cuando este `README.md` tenga todos sus
checkboxes en `[x]`, la iniciativa esta 100% cerrada y la auditoria
puede certificar que no quedan TODOs colgando.

El plan se divide en cinco bloques:

1. **A - Eliminaciones destructivas** (requieren autorizacion explicita).
2. **B - Coverage incremental y tests defensivos**.
3. **C - Refactors arquitectonicos**.
4. **D - CLI/MCP cableado**.
5. **E - Items operativos manuales del vault de Cortex**.

---

## 2. Inventario de pendientes (origen y prioridad)

### A. Eliminaciones destructivas (P1)

| Item | Origen | Riesgo | Notas |
|------|--------|--------|-------|
| Eliminar `cortex/documentation.py` (legacy, huerfano) | Fase 04 (3 menciones) | bajo | No se importa desde Fase 04 (shim via importlib se removio). `git rm` simple. |
| Eliminar `cortex-pi/.pi/agents/cortex-documenter.md` (legacy duplicado) | Fase 03 + Fase 12 | bajo | Coexistencia confusa entre `.cortex/subagents/` (canonico) y `cortex-pi/.pi/agents/` (legacy). |
| Mover/decidir 3 notas raiz del vault Cortex (`architecture.md`, `auth.md`, `getting_started.md`) | Fase 11 | medio | Quedaron `unclassifiable` tras `cortex docs migrate --apply`. Opciones: mover a `vault/architecture/` con doc_type=architecture o eliminar. |
| Decidir destino de wrappers legacy en `cortex/documentation/_legacy_shims.py` | Fase 04 | medio | Hoy sirven a SessionService/SpecService/workitems. Eliminar requiere migrar 4 consumidores al schema canonico (data + kwargs nuevos). |

### B. Coverage incremental y tests defensivos (P2)

| Item | Origen | Lineas a cubrir |
|------|--------|-----------------|
| 9 lineas defensive en `cortex/documentation/writers.py` | Fase 03, 04 | OSError en `_append`, branches que requieren mocks de filesystem |
| 9 lineas defensive en `cortex/semantic/vector_cache.py` | Fase 06 | OSError en `_save_index`, edge cases de compaction |
| 1 linea defensive en `cortex/semantic/chunker.py:260` | Fase 07 | rama del `_split_paragraphs` no alcanzable |
| Tests del presenter legacy (`to_markdown`, `to_compact`) | Fase 08 | `cortex/context_enricher/presenter.py` 53% -> 90%+ |
| Tests CLI `cortex memory-report --telemetry` ya cubiertos por integration tests pero falta version unit con `CliRunner` | Fase 05 (deuda cerrada) | ok |
| mypy strict run sobre `cortex/documentation/` | Fase 01 | gate adicional |

### C. Refactors arquitectonicos (P2)

| Item | Origen | Impacto |
|------|--------|---------|
| Factorizar 3 implementaciones de "doc_type by path" en un helper unico | Fase 09 | `inventory.classify_path` + `enricher._doc_type_from_doc` + `semantic_source._doc_type_from_rel_path` -> un solo `cortex.documentation.doc_type.infer_from_path()` |
| Invalidacion granular de chunks en VectorCache (en lugar de purgar todos los chunks del parent al re-indexar) | Fase 07 | reduce churn de re-embeddings |
| Compaction automatica del VectorCache al 30% invalidados | Fase 06 | hoy es manual via CLI |
| Aristas tipadas `supersedes` en webgraph builder (parsear ADR frontmatter) | Fase 09 | requiere acceso al frontmatter parseado en RelationBuilder |
| `EpisodicSource` con doc_type semantico (e.g. tipo "episodic") en metadata para que la leyenda lo distinga | Fase 09 | opcional |
| Race condition en auto-asignacion de `adr_number` / `incident_number` | Fase 03 | bajo en MVP single-user; documentar limite |
| Multi-proceso safety en VectorCache (hoy es single-process via RLock) | Fase 06 | requiere file locking; fuera de scope MVP |

### D. CLI/MCP cableado (P3)

| Item | Origen | Notas |
|------|--------|-------|
| CLI `cortex search` con flags `--doc-type`, `--scope`, `--max-age`, `--tags-required` | Fase 08 | la API Python (`ContextEnricher.enrich(work, filters=...)`) ya esta lista; falta el wiring del flag en el comando existente |
| MCP tool `cortex_search` con args estructurales | Fase 08 | idem |
| CLI `cortex review-knowledge` con subcomandos `pending`/`approve`/`reject` para Fase 10 promotion review | Fase 10 | promotion `review-required` ya marca status=draft; falta UI para revisarlos |
| Dashboard cortex-pi UI extension (visualizacion de la leyenda en el webgraph) | Fase 09 | trabajo TypeScript fuera del scope backend |
| Test flaky `tests/unit/autopilot/test_service.py::TestStatus::test_latest_session` | Fase 01 | preexistente, NO regresion de la iniciativa; investigar race condition con tmp paths |

### E. Items operativos del vault de Cortex (P2)

| Item | Origen | Accion concreta |
|------|--------|----------------|
| `vault/architecture.md` (raiz) | Fase 11 | mover a `vault/architecture/main.md` con `doc_type=architecture` |
| `vault/auth.md` (raiz) | Fase 11 | mover a `vault/architecture/auth.md` con `doc_type=architecture` |
| `vault/getting_started.md` (raiz) | Fase 11 | mover a `docs/guides/` (no es un doc del vault canonico) o convertirlo en `architecture` |

---

## 3. Plan de ejecucion

### Bloque B (coverage + tests) - SE PUEDE ARRANCAR AHORA

Bajo riesgo, no requiere autorizaciones. Lo desarrolla esta fase
directamente (ver `REALIZACION.md`).

### Bloque C (refactors) - SE PUEDE ARRANCAR

Tambien bajo riesgo. Los items mas valiosos:
1. Factorizar `infer_doc_type_from_path()` en un solo lugar (3 -> 1).
2. Aristas `supersedes` en webgraph.

### Bloque D - PARCIAL (lo que no requiere flujos externos)

CLI `cortex search` con flags estructurales.

### Bloque A y E - REQUIEREN AUTORIZACION DEL USUARIO

- Eliminar `cortex/documentation.py` y `cortex-pi/.pi/agents/cortex-documenter.md` -> `git rm`.
- Mover los 3 archivos raiz del vault Cortex.
- Decidir si eliminar/refactorizar `_legacy_shims.py` y los consumidores.

---

## 4. Checklist global

### Bloque A - Eliminaciones (requieren `git rm`)

- [ ] `cortex/documentation.py` eliminado
- [ ] `cortex-pi/.pi/agents/cortex-documenter.md` eliminado
- [ ] 3 archivos raiz del vault movidos a sus carpetas canonicas
- [ ] Migrar consumidores fuera de `_legacy_shims.py` y eliminar el modulo

### Bloque B - Coverage incremental

- [x] `cortex/semantic/chunker.py` 99% (1 linea defensive aceptada)
- [x] `cortex/context_enricher/telemetry.py` 100% (cerrado en deuda Fase 05)
- [x] `cortex/documentation/_legacy_shims.py` 98% (cerrado en Fase 04)
- [ ] `cortex/documentation/writers.py` defensive paths -> 100%
- [ ] `cortex/semantic/vector_cache.py` defensive paths -> 100%
- [ ] `cortex/context_enricher/presenter.py` legacy paths -> 90%+
- [ ] mypy strict pass sobre `cortex/documentation/`

### Bloque C - Refactors

- [x] Helper unico `infer_doc_type_from_path()` (ver REALIZACION)
- [ ] Invalidacion granular de chunks
- [ ] Compaction automatica VectorCache
- [ ] Aristas `supersedes` en webgraph
- [ ] `EpisodicSource` con doc_type=episodic en metadata
- [ ] File locking en VectorCache (fuera de scope MVP)

### Bloque D - CLI/MCP

- [ ] `cortex search` con flags estructurales
- [ ] MCP `cortex_search` con args estructurales
- [ ] `cortex review-knowledge` subcomandos
- [ ] Dashboard cortex-pi UI (TypeScript)
- [ ] Investigar test flaky `test_latest_session`

### Bloque E - Operativo vault

- [ ] 3 archivos raiz reubicados
- [ ] `cortex docs validate` reporta 0 invalid

---

## 5. Gate de salida

La iniciativa canonical-documentation se considera **100% cerrada** cuando:

- [ ] Todos los items de bloque A estan resueltos (eliminacion + decisiones de mover).
- [ ] Bloque B y C estan completos.
- [ ] Bloque D tiene al menos `cortex search` con flags + `cortex review-knowledge`.
- [ ] Bloque E: `cortex docs validate --all` reporta `Invalid: 0`.
- [ ] Suite global pasa al 100%.
- [ ] Documentado en `REALIZACION.md` con un snapshot final de stats.

---

## 6. Nota final

Este plan es **vivo**: cada vez que cerremos un bloque actualizamos el
checklist. Una vez que todos los bloques esten cerrados, esta fase deja
de tener trabajo activo y la iniciativa global esta completa.

Ver `REALIZACION.md` para el subset desarrollado en esta sesion.
