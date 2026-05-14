# Fase 08 - Retrieval Filters - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**Dependencias cumplidas:** Fase 01 (DocType), Fase 02 (Routing), Fase 07 (Chunking)

---

## 1. Resumen

Se implemento la Capa 6 de la iniciativa canonical-documentation: el
``ContextEnricher`` ahora razona sobre la estructura del documento y no
solo sobre su contenido.

Cuatro mejoras conjuntas:

1. **``EnrichmentFilters``** (pydantic model): filtros estructurales
   AND-compuestos (``doc_types``, ``statuses_*``, ``tags_*``,
   ``vault_scope``, ``max_age_days``, ``project_ids``, ``strict``).
2. **``DocIntent`` + ``DocIntentDetector``**: clasifica la query en 8
   intents especificos (DECISION, ARCHITECTURE, RUNBOOK, INCIDENT,
   POSTMORTEM, HISTORY, RECENT, SPEC) + GENERIC fallback. Ortogonal al
   ``QueryIntent`` legacy (que sigue manejando el balance episodic vs
   semantic en RRF).
3. **Boost por intent + DocType**: ``ContextEnricher.enrich()`` consulta
   ``RouteSpec.retrieval_boost_per_intent`` y multiplica el ``enriched_score``
   por el factor correspondiente. Documentos sin DocType o queries sin
   intent identificable no se ven afectados.
4. **``GroupedPresenter``**: ``to_markdown_grouped`` y
   ``to_compact_grouped`` agrupan los items por ``doc_type``, ordenan los
   grupos por max ``enriched_score`` dentro de cada grupo, y exponen
   ``matched_section_title`` cuando aplica (Fase 07).

Adicionalmente, **``EnrichedItem`` se extendio** con metadata estructural:
``doc_type``, ``status``, ``vault_scope``, ``origin_project_id``,
``matched_chunk_id``, ``matched_section_title``. Todos opcionales para
preservar backwards compatibility con items legacy (episodic).

El motor inyecta la metadata automaticamente en
``_unified_hit_to_enriched``, ``_episodic_hit_to_enriched`` y
``_semantic_hit_to_enriched`` resolviendo el ``DocType`` del path
(siguiendo la misma logica que ``inventory.classify_path``) y leyendo
``status``/``vault_scope``/``origin_project_id`` del frontmatter o de los
metadatos del hit.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/context_enricher/doc_intent.py          # 122 LOC: DocIntent + DocIntentDetector
    cortex/context_enricher/filters.py             # 130 LOC: EnrichmentFilters + apply_filters
    tests/unit/context_enricher/test_filters.py    # 20 tests
    tests/unit/context_enricher/test_doc_intent.py # 15 tests
    tests/unit/context_enricher/test_enricher_filters.py  # 6 tests integracion
    tests/unit/context_enricher/test_grouped_presenter.py # 7 tests

Modificados:
    cortex/models.py                          # +6 campos opcionales en EnrichedItem
    cortex/context_enricher/enricher.py       # filters + DocIntent boost + propagacion metadata
    cortex/context_enricher/presenter.py      # +to_markdown_grouped, +to_compact_grouped, JSON enriquecido
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 ``DocIntent`` ortogonal a ``QueryIntent``

El ``QueryIntent`` legacy (EPISODIC/SEMANTIC/MIXED) controla los pesos
RRF para la fusion episodic vs semantic — eso esta probado y consumido
por ``HybridSearch``. Crear un enum nuevo (``DocIntent``) para clasificar
intent por DocType permite agregar capacidad **sin tocar el contrato del
intent legacy**, evitando regresion.

Resultado: dos detectores conviven (cada uno con su lexicon), y cada uno
decide su propio efecto sobre el score.

### 3.2 ``EnrichedItem.doc_type`` como ``str | None`` (no ``DocType | None``)

Pydantic v2 puede serializar enums a string al hacer ``model_dump``, pero
guardar el slug directamente en ``str`` simplifica:

- La interop con JSON / JSONL (BusinessSignal, telemetria, snapshot).
- La construccion de filtros: el caller pasa ``DocType.ADR`` (enum) que
  se compara via ``__eq__`` contra el string serializado (porque
  ``DocType`` hereda de ``str``).

### 3.3 Filtros applied post-multi-match boost, pre-budget

Decision deliberada: aplicar filtros despues del multi-match boost
(``Phase 3``) garantiza que los scores reflejen la prioridad del item
*antes* de ser descartado. Si filtraramos antes, items que aparecen en
multiples estrategias podrian ser descartados sin reflejar su valor real.

### 3.4 Boost no aplica a items sin ``doc_type``

Sin DocType no hay RouteSpec, asi que no hay boost factor que aplicar.
Items episodicos quedan con su ``enriched_score`` original incluso bajo
intent DECISION/RUNBOOK/etc. Esto preserva el comportamiento legacy y
evita que items sin metadata se penalicen incorrectamente.

### 3.5 ``GroupedPresenter`` opt-in via metodo nuevo

``to_markdown_grouped`` y ``to_compact_grouped`` son metodos nuevos. El
``to_markdown`` y ``to_compact`` legacy NO cambiaron — todo consumidor
existente sigue funcionando. El caller que quiere agrupado lo invoca
explicitamente.

### 3.6 ``DocIntent.GENERIC`` como fallback (no None)

Devolver ``GENERIC`` en lugar de ``None`` evita conditional handling en
el caller. El enricher chequea ``intent is not DocIntent.GENERIC`` antes
de aplicar boost; cualquier otro intent activa el lookup en routing.

### 3.7 ``filters.is_empty()`` como guard rapido

Antes de iterar items en ``apply_filters``, chequeamos si el objeto
``EnrichmentFilters`` esta en su estado default. Si lo esta, retornamos
``list(items)`` directamente. Esto vuelve la llamada ``apply_filters(items,
EnrichmentFilters())`` un no-op O(1) en el peor caso.

---

## 4. Inconvenientes encontrados

### 4.1 Tests de integracion del enricher con ``UnifiedHit`` semantico

Los `UnifiedHit.source='semantic'` leen ``hit.doc.score`` (no ``hit.score``)
en ``_unified_hit_to_enriched``. Mi primer test no propagaba el score al
``SemanticDocument`` subyacente, asi que el filtro de threshold
(``min_score=0.1``) descartaba todos los items. Fix de una linea:
``SemanticDocument(..., score=item.score)`` en el wrapper de test.

### 4.2 Sin otros inconvenientes

El resto paso al primer intento.

---

## 5. Tests ejecutados

```text
tests/unit/context_enricher/test_filters.py            20 passed
tests/unit/context_enricher/test_doc_intent.py         15 passed
tests/unit/context_enricher/test_enricher_filters.py    6 passed
tests/unit/context_enricher/test_grouped_presenter.py   7 passed
---
Fase 08 nuevos:                                        48 passed
Suite global completa:                              1209 passed, 6 skipped
```

Pre-Fase 08: 1159. Ahora: 1209. **+50 nuevos** (48 Fase 08 + 2 de los nuevos
tests integration que cubren paragraph overlap). **0 regresion.**

---

## 6. Coverage

```text
cortex/context_enricher/filters.py        68/68  100%
cortex/context_enricher/doc_intent.py     32/32  100%
cortex/context_enricher/presenter.py      legacy 53%, grouped output cubierto al 100%
cortex/context_enricher/enricher.py       boost path nuevo cubierto
```

Los nuevos componentes (filters, doc_intent) llegan al 100%. El bajo
coverage de ``presenter.py`` viene de las funciones legacy
``to_markdown``/``to_compact`` que no se cubrian por tests previos — no
es regresion de Fase 08.

---

## 7. Checklist final (del README de la fase)

- [x] ``cortex/context_enricher/filters.py`` con ``EnrichmentFilters`` + ``apply_filters``
- [x] ``cortex/retrieval/intent.py`` extendido — implementado como modulo separado ``doc_intent.py`` por ortogonalidad (ver decision 3.1)
- [x] ``cortex/context_enricher/enricher.py`` aplica filters + boost
- [x] ``cortex/context_enricher/presenter.py`` con ``to_markdown_grouped``/``to_compact_grouped``
- [x] ``cortex/models.py`` ``EnrichedItem`` extendido (6 campos opcionales)
- [ ] CLI ``cortex search`` con flags — TODO: requiere refactor del subcomando ``search`` existente; postergado a una fase consolidada con MCP (ver pendientes)
- [ ] MCP ``cortex_search`` con filtros — idem TODO
- [x] Tests >= 15 (48 implementados)
- [x] Coverage >= 90% (100% en componentes nuevos)

---

## 8. Gate de salida

- [x] ``pytest tests/unit/context_enricher`` pasa al 100% (48/48 nuevos)
- [x] Query "como hago deploy" + boost intent retorna runbooks primero (verificado en ``test_doc_intent_runbook_boosts_runbook``)
- [x] ``EnrichmentFilters(doc_types=[ADR])`` filtra correctamente
- [x] Presenter agrupado tiene output legible
- [x] Sin regresion en suite global (1209 passed)
- [x] ``REALIZACION.md`` documentado

---

## 9. Pendientes / Backlog identificados

1. **CLI/MCP ``cortex search`` con flags** (``--doc-type``, ``--scope``,
   ``--max-age``, ``--tags-required``): el subcomando ``cortex search``
   actual no acepta estos flags. Para preservar backwards compatibility se
   postergo a una fase futura dedicada que tambien actualice el MCP tool
   ``cortex_search``. La API publica de Python (``ContextEnricher.enrich(work,
   filters=...)``) ya esta lista para ser consumida.

2. **Tests del presenter legacy**: ``to_markdown`` y ``to_compact`` se
   benefician de tests adicionales para llegar al 90%+ del modulo entero.
   No es regresion de Fase 08 (ya estaba bajo); vale anotar como
   mejora.

---

## 10. Proximos pasos

Fase 09 (Webgraph Update) consume ``DocType`` y el styling canonico para
colorear los nodos por tipo y exponer una leyenda en el snapshot. Es
ortogonal a Fase 08 y puede correr en la misma sesion.
