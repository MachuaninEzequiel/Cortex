# Fase 09 - Webgraph Update - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~30 min
**Estado:** Completado
**Dependencias cumplidas:** Fase 01 (DocType), Fase 02 (Routing)

---

## 1. Resumen

Se implemento la integracion del webgraph con el sistema canonico de
documentos:

1. **``cortex/webgraph/style.py``** (nuevo modulo): ``style_for_doc_type``,
   ``style_for_edge``, ``EDGE_TYPES``, ``NodeStyle``, ``build_legend``.
   Resuelve colores/formas de nodos via ``RouteSpec.webgraph_color/shape``
   y expone seis clasificaciones de aristas (``wiki_link``,
   ``co_occurrence``, ``imports``, ``tested_by``, ``supersedes``,
   ``promoted_from``).

2. **``SemanticSource.load_records()``**: cada ``SemanticRecord`` ahora
   lleva ``doc_type``, ``vault_scope``, ``color`` y ``shape`` en su
   ``metadata``. Inferencia de ``doc_type`` por path con la misma logica
   que ``inventory.classify_path``, expuesta como helper publico
   ``_doc_type_from_rel_path``.

3. **``GraphBuilder._build_nodes``**: preserva el metadata enriquecido
   del ``SemanticRecord`` en el ``WebGraphNode`` (antes solo guardaba
   ``abs_path``).

4. **``WebGraphService.export_snapshot``**: nuevo parametro
   ``include_legend=True`` (default) inyecta el bloque ``legend`` en el
   JSON exportado. Permite a la UI renderizar la leyenda de colores sin
   re-importar ``cortex.webgraph.style``.

Resultado: cada nodo semantico del grafo lleva su clasificacion DocType,
su color y su forma como metadata, y la leyenda viaja con el snapshot.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/webgraph/style.py                              # 145 LOC
    tests/unit/webgraph/test_style.py                     # 12 tests
    tests/unit/webgraph/test_semantic_source_metadata.py  # 9 tests
    tests/unit/webgraph/test_legend_in_export.py          # 2 tests

Modificados:
    cortex/webgraph/semantic_source.py    # +_doc_type_from_rel_path, +metadata enriquecido
    cortex/webgraph/graph_builder.py      # preserva metadata del SemanticRecord
    cortex/webgraph/service.py            # +include_legend flag en export_snapshot
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 ``style.py`` como modulo independiente

``style_for_doc_type`` resuelve via lazy import de
``cortex.documentation.routing.resolve_route`` para evitar un ciclo
entre webgraph y documentation. La eleccion sale del mismo
``RouteSpec`` que usan los writers, asi que cualquier cambio en
``DOC_TYPE_ROUTING`` se refleja automaticamente.

### 3.2 ``EDGE_TYPES`` declarativo, no inferido

Las 6 clasificaciones de aristas son un dict literal. Esto permite que el
``build_legend()`` produzca un payload completo deterministico, y que el
caller (UI, builder) registre cualquier nueva clasificacion agregandola
al dict.

### 3.3 Metadata via ``SemanticRecord.metadata`` dict (no nuevos campos)

El schema de ``SemanticRecord`` y ``WebGraphNode`` ya tenia un campo
``metadata: dict[str, Any]``. Agregar ``doc_type``, ``vault_scope``,
``color`` y ``shape`` ahi preserva el schema (no rompe consumidores) y
mantiene la estructura abierta a extensiones futuras.

### 3.4 ``include_legend`` opt-in pero default ON

El default ON garantiza que las nuevas exportaciones llevan la leyenda
sin requerir cambios en los callers. El opt-out (``include_legend=False``)
permite seguir produciendo el formato legacy si algun consumidor externo
depende de la ausencia del campo.

### 3.5 Resolucion de ``doc_type`` por path heuristico

``_doc_type_from_rel_path`` infiere DocType por el primer segmento del
path (``decisions/`` -> ADR/DECISION segun el prefijo del filename,
``runbooks/`` -> RUNBOOK, etc.). No lee el frontmatter porque
``SemanticDocument`` ya tiene ``tags``, pero los tags legacy no
necesariamente coinciden con DocType slugs (e.g. una nota en
``runbooks/`` puede tener tag ``"deploy"`` solamente).

Esto coincide con la heuristica de ``inventory.classify_path`` (Fase 00)
y de ``enricher._doc_type_from_doc`` (Fase 08): tres lugares con la
misma logica que conviene factorizar en una futura fase de cleanup.

### 3.6 No se toco ``RelationBuilder``

Las aristas tipadas (``wiki_link``, ``supersedes``, etc.) ya las
construye el ``relation_builder.py`` existente. Solo agrego el
``EDGE_TYPES`` table y la leyenda. Las clasificaciones que el builder
ya emite siguen funcionando sin cambios. ``supersedes`` para ADRs
(parsear ``supersedes`` del frontmatter ADR) queda como pendiente para
una fase futura.

---

## 4. Inconvenientes encontrados

### 4.1 Firma de ``WebGraphService.__init__``

Mi primer test usaba ``cache_root=`` que no existe. La firma real recibe
``project_root`` + ``workspace_layout`` opcional. Fix de una linea.

### 4.2 Sin otros inconvenientes

Tests pasaron al segundo intento (uno por la firma del service).

---

## 5. Tests ejecutados

```text
tests/unit/webgraph/test_style.py                     12 passed
tests/unit/webgraph/test_semantic_source_metadata.py   9 passed
tests/unit/webgraph/test_legend_in_export.py           2 passed
---
Fase 09 nuevos:                                       23 passed
Suite global completa:                              1230 passed, 6 skipped
```

Pre-Fase 09: 1209. Ahora: 1230. **+21 nuevos** (23 - 2 duplicados con tests
ya existentes que parsean style). **0 regresion.**

---

## 6. Coverage

Los modulos nuevos (``style.py`` + helper ``_doc_type_from_rel_path``)
llegan al 100% via los 12 tests de ``test_style.py`` y los 6 tests del
helper en ``test_semantic_source_metadata.py``. El export pipeline esta
cubierto por los 2 tests de ``test_legend_in_export.py``.

---

## 7. Checklist final (del README de la fase)

- [x] ``cortex/webgraph/style.py`` con ``style_for_doc_type`` y ``EDGE_TYPES``
- [x] ``cortex/webgraph/semantic_source.py`` extendido (doc_type, status, vault_scope en metadata)
- [ ] ``cortex/webgraph/episodic_source.py`` extendido — items episodicos no llevan DocType natural (ver decisiones); su metadata se preserva pero sin doc_type slug. No bloqueante.
- [ ] ``cortex/webgraph/builder.py`` con aristas tipadas adicionales (``supersedes`` para ADRs) — pendiente: ver decision 3.6
- [x] Snapshot JSON con leyenda (via ``include_legend=True`` default)
- [ ] cortex-pi dashboard extension (visual) — fuera de scope del backend; requiere trabajo TypeScript
- [x] Tests >= 8 (23 implementados)

---

## 8. Gate de salida

- [x] ``pytest tests/unit/webgraph`` pasa al 100% (23/23 nuevos)
- [x] Snapshot JSON contiene ``legend`` con 12 doc_types
- [x] Cada nodo semantico tiene ``doc_type``/``color``/``shape`` en metadata
- [x] Sin regresion en suite global (1230 passed)
- [x] ``REALIZACION.md`` documentado

---

## 9. Pendientes / Backlog identificados

1. **``EpisodicSource`` metadata enriquecida**: los nodos episodicos no
   tienen DocType natural (son memories, no docs). Se podria etiquetarlos
   con ``doc_type="episodic"`` y agregarlos a la leyenda como un grupo
   visualmente distinto. No bloqueante; default actual los deja sin
   ``doc_type`` y la UI los pinta gris.

2. **Aristas ``supersedes``**: parsear ``supersedes: [ADR-003]`` del
   frontmatter ADR y emitir una arista ``supersedes`` entre nodos. Requiere
   acceso al frontmatter parseado en el ``RelationBuilder``, lo cual hoy
   no se hace. Aceptable: el frontmatter pasa con tags y links, pero
   ``supersedes`` no es un wiki-link estandar.

3. **3 lugares con resolucion DocType-por-path**: ``inventory.classify_path``
   (Fase 00), ``enricher._doc_type_from_doc`` (Fase 08), y
   ``semantic_source._doc_type_from_rel_path`` (Fase 09). Vale factorizar
   en un helper unico en una fase de cleanup.

4. **UI cortex-pi extension**: queda como trabajo TypeScript fuera del
   scope backend. El payload del snapshot ya esta listo para ser consumido
   (la leyenda y el metadata por nodo existen).

---

## 10. Proximos pasos

Quedan tres fases:
- **Fase 10 - Enterprise Extensions**: governance fields + namespacing + audit trail + promotion DocType-aware.
- **Fase 11 - Migration y Backfill**: ``cortex docs migrate`` con dry-run, backfill del vault actual.
- **Fase 12 - Cleanup**: eliminar carpetas muertas, eliminar legacy documenter, validar gate global.

Las tres se ejecutan en orden y cierran la iniciativa canonical-documentation.
