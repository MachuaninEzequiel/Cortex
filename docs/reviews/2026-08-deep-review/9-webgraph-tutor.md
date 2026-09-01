# Deep Review — WebGraph / Tutor / Skills (subsistema 9)

> Reconstruido desde la revisión del subagente rev-webgraph-tutor (entregado por mensajes por límite de turno).
> Alcance: cortex/webgraph/**, cortex/tutor/**, cortex/skills/** — todos los archivos leídos completos.

## Arquitectura
- `WebGraphService` (service.py) orquesta `SemanticSource` (VaultReader→SemanticRecord) + `EpisodicSource` (EpisodicMemoryStore→EpisodicRecord) → `GraphBuilder` → `RelationBuilder` (6 tipos de aristas explicables con evidence) → `WebGraphCache` (fingerprint sha256 de config+mtree mtimes+episodic token).
- Entradas: CLI `cortex webgraph serve/export/doctor`, setup orchestrator, doctor.py.
- Salidas: snapshot JSON (+leyenda), Flask UI (vis-network).
- Federación compone N proyectos prefijando ids `project::node`.

## Invariantes clave
- ids `semantic:<relpath>` / `episodic:<memory_id>`.
- Edges no direccionales colapsan por (type,min,max) salvo wikilink/supersedes/superseded_by (relation_builder.py:72-77).
- Degree se computa pre-filtrado de nodos; scope via metadata['scope'] inyectada post-build.

## Hallazgos

1. **BUG DE CACHÉ POR SCOPE** (service.py:59-87): el fingerprint del cache no incluye `scope`. build_snapshot(mode='hybrid', scope='local') guarda el snapshot FILTRADO con clave (mode, fingerprint); una llamada posterior con scope=None devuelve desde cache el snapshot recortado a 'local'. Corrupción silenciosa para federación y UI.
2. **LEYENDA/ESTILOS DESCONECTADOS** (style.py:347-383 vs relation_builder.py): EDGE_TYPES declara wiki_link/co_occurrence/imports/tested_by/promoted_from, pero RelationBuilder emite wikilink/same_spec_reference/same_file_reference/shared_tag/shared_entity/semantic_neighbor. Solo supersedes/superseded_by coinciden. Además app.js duplica nodePalette hardcodeado (app.js:29-44) mientras style.py deriva de RouteSpec — dos fuentes de verdad divergidas.
3. **O(n²) EN PRODUCCIÓN** (relation_builder.py): `_add_cross_source_edges` (l.228-262) itera episódico×semántico y re-tokeniza todo el contenido semántico dentro del loop interno. `_add_semantic_neighbors` calcula cosine O(n²) DOS veces (l.275-281 y l.289-306), en Python puro sobre embeddings de 384 dims. `load_records` embebe un doc por vez sin batching (semantic_source.py:235).
4. **KeyError → HTTP 500** (service.py:119, federation.py:307): get_node_detail hace nodes_by_id[node_id] sin validar; server.py:55-59 no captura nada. server.py:52-53 tampoco valida `mode` del query param (pydantic ValidationError → 500).
5. **SEGURIDAD /api/open inconsistente** (server.py:72-90): en modo single-project usa resolve_safe_vault_path (openers.py:256-263), pero en federado (l.87-88) abre resolved_path directo SIN guard. Header X-Cortex-WebGraph spoofable; app.js inyecta label/summary vía innerHTML (app.js:60-63, 96-101) — XSS si el vault tiene HTML hostil.
6. **FEDERACIÓN CARA Y DUPLICADA** (federation.py): build_snapshot ignora use_cache (`del use_cache`, l.243); get_node_detail/get_subgraph reconstruyen el snapshot federado COMPLETO por request; get_subgraph duplica el BFS de service.get_subgraph con otra implementación. __init__ instancia todos los WebGraphService (Chroma+ONNX) eager.
7. **DUPLICACIÓN LITERAL**: _read_project_config y _normalize_summary copiadas idénticas en semantic_source.py:122-134/271-275 y episodic_source.py:254-259/271-275. Enterprise append traga TODAS las excepciones silenciosamente (service.py:188-189).
8. **skills/__init__.py**: install_skills traga excepciones por skill (l.70-71) y por archivo (l.92-93): installs parciales silenciosos. Copia read_text/write_text rompe con binarios. SKILL_NAMES (l.24-30) se sincroniza a mano con directorios reales.
9. **tutor**: guide_path en protocolo TutorTopic (engine.py:75-87) pero NADIE lo consume — campo muerto en 7 topics. Cada topic repite ~40 líneas de properties boilerplate. HintEngine.render importa el privado _safe_console (hint.py:272).

## Salud: 6.5/10
Bien testeado (10 archivos en tests/unit/webgraph), contratos pydantic claros, separación source/builder/cache correcta. Riesgos: bugs activos de cache/scope, leyenda divergente, hotspots O(n²), duplicación federation/service, errores silenciosos, sin tests de tutor ni frontend.

## Orden sugerido para cambio grande
1. Cache key: agregar scope+legend al fingerprint.
2. Unificar estilos: app.js debe consumir payload['legend']; eliminar paletas hardcodeadas.
3. Módulo compartido para _read_project_config/_normalize_summary; precomputar tokens fuera del loop O(n²).
4. Fragilidad máxima: RelationBuilder (heurísticas de tokens) y contrato implícito service↔federation.
