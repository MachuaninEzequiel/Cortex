# Plan — Deuda tecnica residual (canonical-documentation)

**Fecha:** 2026-05-15
**Origen:** auditoria cruzada de las 4 iniciativas (docs/agents, docs/autopilot, docs/enterprise, docs/canonical-documentation).
**Estado:** Pendiente de ejecucion.
**Scope:** los **12 items** de deuda tecnica que quedaron despues del cierre de las Fases 00-13 y la cirugia de limpieza (commits `32aa2e9` + `a1ad5ac`).
**Esfuerzo estimado total:** 28-35 horas (~4 dias persona).
**Riesgo agregado:** medio-bajo. Solo #10 toca hot paths (services); el resto son aislados.

---

## Resumen ejecutivo

| # | Item | Origen | Esfuerzo | Riesgo | Recomendado en sprint |
|---|------|--------|----------|--------|------------------------|
| 1 | mypy strict sobre `cortex/documentation/` | Fase 01 | 2-3h | bajo | Dia 1 |
| 2 | Tests presenter.py legacy paths | Fase 08 | 2h | bajo | Dia 1 |
| 3 | Auto-compaction VectorCache 30% | Fase 06 | 2h | medio | Dia 4 |
| 4 | Invalidacion granular de chunks | Fase 07 | 4h | medio | Dia 4 |
| 5 | Aristas `supersedes` tipadas en webgraph | Fase 09 | 3h | bajo | Dia 2 |
| 6 | EpisodicSource con doc_type=episodic | Fase 09 | 1h | bajo | Dia 1 |
| 7 | CLI `cortex search` flags estructurales | Fase 08 | 2h | bajo | Dia 2 |
| 8 | MCP tool `cortex_search` con args estructurales | Fase 08 | 2h | bajo | Dia 2 |
| 9 | CLI `cortex review-knowledge pending/approve/reject` | Fase 10 | 4h | medio | Dia 4 |
| 10 | Migrar 4 consumers de `_legacy_shims.py` + git rm | Fase 04 | 4-5h | medio | Dia 3 |
| 11 | Dashboard cortex-pi UI extension (TypeScript) | Fase 09 | 4-6h | bajo | Diferido (sprint UI) |
| 12 | File locking VectorCache multi-process | Fase 06 | 3-4h | medio | Diferido 0.6.x |

**Si se cierra todo el core (excluye #11 UI y #12 multi-proc):** 10 items en ~3 dias.

---

## Item 1 — mypy strict sobre `cortex/documentation/`

### Descripcion

El proyecto corre mypy con `strict = false` (`pyproject.toml:93`). El modulo canonico `cortex/documentation/` nunca paso un gate `strict = true`.

### Por que importa

- Es el modulo core del schema canonico. Cualquier `Any` implicito, return no tipado o `dict` sin TypedDict erosiona la confianza en los pydantic schemas.
- Marcado explicitamente como gate adicional en Fase 01.

### Propuesta de solucion

1. Agregar override en `pyproject.toml`:
   ```toml
   [[tool.mypy.overrides]]
   module = "cortex.documentation.*"
   strict = true
   ```
2. Correr `mypy cortex/documentation/`. Areas problematicas esperadas:
   - `_legacy_shims.py` — kwargs flexibles, dataclass coercion. **Nota:** si #10 se ejecuta antes que #1, este archivo desaparece y se simplifica este item.
   - `writers.py` — coercion de status/tags en `_coerce_status`, `_coerce_tags`.
   - `validation.py` — pydantic `Any` que aparecen en `model_validator`.
3. Fixear cada error: anotaciones explicitas, `cast()` donde sea inevitable, narrow types.
4. Agregar a CI (`.github/workflows/ci-pull-request.yml`) un paso opcional:
   ```yaml
   - name: Mypy strict (documentation module)
     run: mypy cortex/documentation/
     continue-on-error: false
   ```

### Esfuerzo
2-3h (depende del numero de errores).

### Riesgo
Bajo. No toca runtime, solo anotaciones.

### Dependencias
- **Recomendado:** ejecutar despues de #10 (eliminacion de `_legacy_shims.py`), porque el shim concentra los kwargs flexibles dificiles de tipar.

### Test plan
- `mypy --strict cortex/documentation/` retorna 0 errors.
- Suite global (`pytest --no-cov`) sigue en 1416 passed.

---

## Item 2 — Tests presenter.py legacy paths

### Descripcion

`cortex/context_enricher/presenter.py` tiene 53% coverage. Las funciones legacy `to_markdown()` y `to_compact()` estan cubiertas solo por integration tests, no unit.

### Por que importa

Presenter es el ultimo gate antes del prompt que ve el LLM. Un bug silencioso ahi (items truncados, formato corrompido, confidence label ausente) degrada el contexto inyectado sin que ningun test lo capture.

### Propuesta de solucion

1. Mapear paths sin cobertura leyendo `cortex/context_enricher/presenter.py`. Esperar:
   - Branch de budget cutoff (`max_chars` exhausto).
   - Branch de `items` vacio.
   - Branch de items con `confidence` label vs sin.
   - Branch de items con `doc_type` desconocido.
   - Branch de unicode/emoji preservation.
2. Crear `tests/unit/context_enricher/test_presenter_legacy.py`:
   ```python
   class TestToMarkdown:
       def test_empty_items_returns_header_only(self): ...
       def test_truncates_to_max_chars(self): ...
       def test_renders_confidence_label_when_present(self): ...
       def test_skips_doc_type_if_unknown(self): ...
       def test_unicode_preserved(self): ...

   class TestToCompact:
       def test_one_line_per_item(self): ...
       def test_handles_unicode(self): ...
       def test_respects_max_chars(self): ...
   ```
3. Target: `to_markdown` y `to_compact` >= 95%. Total presenter.py >= 90%.

### Esfuerzo
2h.

### Riesgo
Bajo. Solo agrega tests.

### Dependencias
Ninguna.

### Test plan
```bash
pytest tests/unit/context_enricher/test_presenter_legacy.py --cov=cortex.context_enricher.presenter --cov-report=term
```
Coverage de presenter.py >= 90%.

---

## Item 3 — Auto-compaction VectorCache al 30% invalidados

### Descripcion

`VectorCache.compact()` existe pero solo se invoca manualmente via CLI (`cortex docs vectorize compact`). Si invalidas muchos chunks (re-indexar 30%+ del vault), el archivo `chunks.bin` crece sin compactar y la fragmentacion degrada I/O.

### Por que importa

Para vaults grandes (>10000 notas), la fragmentacion del cache aumenta I/O time linealmente. Auto-compaction es la diferencia entre `cortex sync-vault` que tarda 2s vs 15s en vaults grandes.

### Propuesta de solucion

1. En `cortex/semantic/vector_cache.py::VectorCache`:
   ```python
   def __init__(self, ..., auto_compact: bool = True, auto_compact_threshold: float = 0.30):
       self._auto_compact = auto_compact
       self._auto_compact_threshold = auto_compact_threshold

   def _maybe_auto_compact(self) -> None:
       if not self._auto_compact:
           return
       total = len(self._index)
       if total == 0:
           return
       invalid_count = sum(1 for e in self._index.values() if e.get("invalidated"))
       if (invalid_count / total) >= self._auto_compact_threshold:
           self.compact()
   ```
2. Llamar `_maybe_auto_compact()` al final de `invalidate()` y `invalidate_by_chunk_id()`.
3. Hacer opt-out via `VectorCache(auto_compact=False)` para tests deterministas.
4. Threshold leible desde `config.yaml`:
   ```yaml
   semantic:
     vector_cache:
       auto_compact: true
       auto_compact_threshold: 0.30
   ```
5. Wire en `cortex/core.py::AgentMemory.__init__` para pasar el setting al VectorCache.

### Esfuerzo
2h.

### Riesgo
Medio. `invalidate*()` es hot path en `sync-vault`. Hay que asegurar que el chequeo sea O(n) sobre `self._index` y no degrade el caso comun.

### Dependencias
- **Sinergia con #4:** si se hace primero #4 (granular invalidation), la auto-compaction tiene mejores datos (no purga tanto). Hacer #4 antes que #3.

### Test plan
- `tests/unit/semantic/test_vector_cache.py::TestAutoCompact`:
  - `test_triggers_at_threshold` — invalidar 4 de 10 entradas, verificar compact se llamo.
  - `test_no_compact_below_threshold` — invalidar 2 de 10, verificar compact NO se llamo.
  - `test_opt_out_disables_auto_compact` — auto_compact=False, invalidar 9 de 10, verificar no compact.
  - `test_threshold_from_config` — pasar threshold custom, verificar respeta.

---

## Item 4 — Invalidacion granular de chunks

### Descripcion

Al re-indexar un archivo, `VectorCache.invalidate_by_chunk_id(parent_path)` purga TODOS los chunks de ese parent doc. Si solo cambio un seccion (un chunk de 8), igual se recalculan los 8.

### Por que importa

Re-embedding tiene costo. Una nota de 4000 palabras con 8 chunks tarda ~2s en re-embedearse con MiniLM-L6. Si solo cambio el chunk 3, deberiamos invalidar y re-embedear solo ese.

Para vaults activos con notas grandes (architecture.md, runbooks largos), esto representa **>5x speedup** en `cortex sync-vault`.

### Propuesta de solucion

1. Asegurar que `cortex/semantic/chunker.py::Chunker.split()` ya emite `Chunk.fingerprint` por chunk (sha256 del texto del chunk). Si no esta, agregarlo.
2. Agregar metodo en `VectorCache`:
   ```python
   def get_chunk_fingerprints(self, parent_path: str) -> dict[str, str]:
       """Return {chunk_id: fingerprint} for all chunks of a parent doc."""
       return {
           chunk_id: entry["fingerprint"]
           for chunk_id, entry in self._index.items()
           if chunk_id.startswith(parent_path + "#") or chunk_id == parent_path
       }
   ```
3. En `cortex/semantic/vault_reader.py::VaultReader.index_file()`, antes de llamar `invalidate_by_chunk_id`:
   ```python
   def _granular_reindex(self, path: str, new_chunks: list[Chunk]) -> int:
       """Re-embed only chunks whose fingerprint changed. Returns embed_call_count."""
       cached_fps = self._cache.get_chunk_fingerprints(path)
       embed_count = 0
       seen_ids = set()
       for chunk in new_chunks:
           seen_ids.add(chunk.id)
           if cached_fps.get(chunk.id) != chunk.fingerprint:
               vector = self._embedder.embed(chunk.text)
               self._cache.put(chunk.fingerprint, chunk.id, vector)
               embed_count += 1
       # Eliminar chunks que ya no existen en el doc actualizado
       removed = set(cached_fps) - seen_ids
       for chunk_id in removed:
           self._cache.invalidate_by_chunk_id(chunk_id)
       return embed_count
   ```
4. Llamar `_granular_reindex` en lugar del purge total.
5. Backward-compat: si el cache no tiene `fingerprint` por chunk (vault recien creado o cache vacio), fallback al comportamiento actual.

### Esfuerzo
4h.

### Riesgo
Medio. Toca hot path de indexacion. Bug puede causar busqueda con chunks stale.

### Dependencias
Ninguna. Pero sinergia con #3.

### Test plan
- `tests/unit/semantic/test_chunker_granular.py`:
  - `test_unchanged_chunks_not_reembedded` — indexar doc 4 chunks, modificar texto fuera de chunks, re-indexar, mock embedder count == 0.
  - `test_only_modified_chunk_reembedded` — modificar 1 chunk de 4, count == 1.
  - `test_new_chunk_embedded` — agregar nueva seccion (5to chunk), count == 1.
  - `test_removed_chunk_invalidated` — eliminar 1 chunk, verificar `invalidate_by_chunk_id` se llamo para ese.
- `tests/integration/test_vault_reader_granular.py`: e2e con archivo .md real.

---

## Item 5 — Aristas `supersedes` tipadas en webgraph

### Descripcion

El webgraph muestra nodos coloreados por DocType (Fase 09) y aristas wiki-link genericas. Pero los ADRs declaran `supersedes: [ADR-003]` en frontmatter — esa relacion semantica NO aparece como arista tipada/coloreada distinta.

### Por que importa

Permite ver visualmente la cadena de decisiones arquitectonicas. "ADR-007 supersedes ADR-003" es una relacion mas fuerte que un wiki-link y merece visibilidad propia.

### Propuesta de solucion

1. Extender `cortex/webgraph/contracts.py::Edge`:
   ```python
   class Edge(BaseModel):
       source: str
       target: str
       kind: Literal["wikilink", "supersedes", "superseded_by", "related", "links"] = "wikilink"
       color: str | None = None
       dasharray: str | None = None  # SVG dasharray para distinguir tipo
   ```
2. En `cortex/webgraph/relation_builder.py::RelationBuilder.build()`, agregar paso de parseo de frontmatter:
   ```python
   def _build_typed_edges(self, docs: list[SemanticDocument]) -> list[Edge]:
       edges = []
       for doc in docs:
           fm = self._parse_frontmatter(doc.path)
           if not fm:
               continue
           for target in fm.get("supersedes", []):
               edges.append(Edge(
                   source=doc.id,
                   target=self._resolve_target(target),
                   kind="supersedes",
                   color="#d9534f",
                   dasharray="5,5",
               ))
           for target in fm.get("superseded_by", []):
               edges.append(Edge(
                   source=doc.id,
                   target=self._resolve_target(target),
                   kind="superseded_by",
                   color="#9e9e9e",
                   dasharray="2,4",
               ))
           for target in fm.get("links", []):
               edges.append(Edge(source=doc.id, target=self._resolve_target(target), kind="links"))
       return edges
   ```
3. Agregar `cortex/webgraph/style.py::EDGE_STYLES`:
   ```python
   EDGE_STYLES = {
       "wikilink": {"color": "#999", "dasharray": None},
       "supersedes": {"color": "#d9534f", "dasharray": "5,5"},
       "superseded_by": {"color": "#9e9e9e", "dasharray": "2,4"},
       "related": {"color": "#5bc0de", "dasharray": "3,3"},
       "links": {"color": "#777", "dasharray": None},
   }
   ```
4. Update `cortex/webgraph/service.py` para incluir `edge_legend` en `meta.json`.
5. Resolver target: si `supersedes: [ADR-003]`, buscar la nota con `adr_number=3` en el vault para resolver al `Node.id` correcto. Helper:
   ```python
   def _resolve_target(self, target: str) -> str:
       """ADR-003 -> ID del nodo en el grafo."""
       if target.startswith("ADR-"):
           number = int(target.split("-")[1])
           for doc in self._docs:
               if doc.frontmatter.get("adr_number") == number:
                   return doc.id
       return target  # fallback: literal
   ```

### Esfuerzo
3h.

### Riesgo
Bajo. Extension aislada al RelationBuilder. Backward-compat: si frontmatter no tiene `supersedes`, comportamiento igual.

### Dependencias
Ninguna.

### Test plan
- `tests/unit/webgraph/test_typed_edges.py`:
  - `test_supersedes_creates_typed_edge` — vault con ADR-001 y ADR-007 (que supersedes ADR-001) -> edge con kind="supersedes".
  - `test_unresolved_supersedes_target_falls_back_to_literal` — ADR no encontrado, edge.target == "ADR-999".
  - `test_edge_legend_in_meta_json` — meta.json contiene `edge_legend` con 5 entradas.

---

## Item 6 — EpisodicSource con doc_type=episodic en metadata

### Descripcion

Los nodos episodic en el webgraph se renderean sin `doc_type` -> no aparecen en la leyenda (que se construye por DocType), causando confusion visual.

### Por que importa

Cosmetica + claridad: la leyenda dice "ADR, Spec, Runbook..." pero los nodos morados/distintos del costado quedan sin etiqueta. El usuario no entiende que son memorias episodicas.

### Propuesta de solucion

1. En `cortex/webgraph/episodic_source.py::EpisodicSource.fetch()`, al construir cada `Node`:
   ```python
   node = Node(
       id=...,
       label=...,
       kind="episodic",
       metadata={
           "doc_type": "episodic",  # NUEVO
           ...
       },
   )
   ```
2. En `cortex/webgraph/style.py`, agregar entrada en `DOC_TYPE_STYLES`:
   ```python
   "episodic": NodeStyle(
       color="#9b59b6",
       shape="diamond",
       label="Episodic Memory",
   ),
   ```
3. Update `cortex/webgraph/service.py::build_legend()` para incluir "episodic" si hay nodos de ese tipo en el grafo.

### Esfuerzo
1h.

### Riesgo
Bajo.

### Dependencias
Ninguna.

### Test plan
- `tests/unit/webgraph/test_episodic_metadata.py`:
  - `test_episodic_node_has_doc_type` — fetch, verificar `node.metadata["doc_type"] == "episodic"`.
  - `test_legend_includes_episodic_when_present` — graph con memorias, legend incluye entry.

---

## Item 7 — CLI `cortex search` con flags estructurales

### Descripcion

El comando `cortex search "query"` retorna el payload RRF crudo sin filtros. El comando paralelo `cortex docs search` (creado en Fase 13) si tiene los flags (`--doc-type`, `--scope`, etc.), pero los adopters esperan que el comando original los soporte.

### Por que importa

Friccion para adopters. `cortex search "auth" --doc-type adr` deberia funcionar. Tener que descubrir un comando secundario es UX pobre.

### Propuesta de solucion

1. Extraer la logica de construccion de filtros a un helper compartido. Crear `cortex/cli/_search_filters.py`:
   ```python
   from cortex.context_enricher.filters import EnrichmentFilters

   def build_enrichment_filters_from_cli(
       doc_type: list[str] | None,
       exclude_doc_type: list[str] | None,
       status: list[str] | None,
       tag: list[str] | None,
       tag_any: list[str] | None,
       scope: str,
       max_age_days: int | None,
       project_id: list[str] | None,
       strict: bool,
   ) -> EnrichmentFilters:
       """Build EnrichmentFilters from CLI flags. Used by `cortex search` and `cortex docs search`."""
       ...
   ```
2. Refactor `cortex/cli/docs_search.py` para usar el helper.
3. En `cortex/cli/main.py`, extender el comando `cortex search`:
   ```python
   @app.command("search")
   def search_command(
       query: str,
       top_k: int = 5,
       doc_type: list[str] = typer.Option(None, "--doc-type"),
       exclude_doc_type: list[str] = typer.Option(None, "--exclude-doc-type"),
       status: list[str] = typer.Option(None, "--status"),
       tag: list[str] = typer.Option(None, "--tag"),
       tag_any: list[str] = typer.Option(None, "--tag-any"),
       scope: str = typer.Option("local", "--scope"),
       max_age_days: int | None = typer.Option(None, "--max-age-days"),
       project_id: list[str] = typer.Option(None, "--project-id"),
       strict: bool = typer.Option(False, "--strict"),
       format: str = typer.Option("text", "--format", help="text|json|compact"),
   ) -> None:
       memory = AgentMemory()
       if not any([doc_type, exclude_doc_type, status, tag, tag_any, max_age_days, strict]):
           # Path legacy sin filtros: RRF crudo + formato actual
           results = memory.retriever.search(query, top_k=top_k)
           _print_legacy(results, format)
           return
       # Path nuevo con filtros: usar enricher
       filters = build_enrichment_filters_from_cli(...)
       enriched = memory.enricher.enrich(work=WorkContext(text=query), filters=filters)
       _print_enriched(enriched, format)
   ```
4. Backward-compat: si no se pasan flags, el output es identico al actual.

### Esfuerzo
2h.

### Riesgo
Bajo. El helper ya existe en `docs_search.py`, solo se extrae.

### Dependencias
Ninguna (pero sinergia con #8).

### Test plan
- `tests/unit/cli/test_search.py`:
  - `test_search_legacy_no_filters_returns_rrf` — sin flags, output es RRF crudo (backward-compat).
  - `test_search_with_doc_type_filters` — `--doc-type adr` retorna solo ADRs.
  - `test_search_with_scope_enterprise` — scope filter funciona.
  - `test_search_json_format` — `--format json` valido JSON parseable.

---

## Item 8 — MCP tool `cortex_search` con args estructurales

### Descripcion

El MCP server expone `cortex_search` con args `query` + `top_k` solo. No expone los filtros estructurales (`doc_type`, `scope`, etc.) que ya estan en la API Python (`ContextEnricher.enrich(work, filters=...)`).

### Por que importa

Agentes IA (Claude Code, Cursor, etc.) que usan el MCP server no pueden filtrar busquedas desde el LLM. Misma friccion que #7 pero para el camino MCP.

### Propuesta de solucion

1. En `cortex/mcp/server.py`, extender el schema de input del tool `cortex_search`:
   ```python
   class CortexSearchArgs(BaseModel):
       query: str
       top_k: int = 5
       doc_type: list[str] | None = None
       exclude_doc_type: list[str] | None = None
       status: list[str] | None = None
       tag: list[str] | None = None
       tag_any: list[str] | None = None
       scope: Literal["local", "enterprise", "all"] = "local"
       max_age_days: int | None = None
       project_id: list[str] | None = None
       strict: bool = False
   ```
2. Agregar helper paralelo a #7: `cortex/mcp/_search_filters.py::build_enrichment_filters_from_mcp(args)`. **NOTA:** puede unificarse con el de #7 si la firma soporta dict/object (sugerido).
3. En el handler de `cortex_search`:
   ```python
   if any([args.doc_type, args.exclude_doc_type, args.status, args.tag, args.tag_any, args.max_age_days, args.strict]):
       filters = build_enrichment_filters_from_mcp(args)
       enriched = self._memory.enricher.enrich(work=WorkContext(text=args.query), filters=filters)
       return enriched.to_prompt_format()
   else:
       # Backward-compat: payload RRF crudo
       results = self._memory.retriever.search(args.query, top_k=args.top_k)
       return _format_results(results)
   ```
4. Update tool registration con el nuevo schema (JSON Schema autogenerado por pydantic).

### Esfuerzo
2h.

### Riesgo
Bajo.

### Dependencias
- **Recomendado:** hacer #7 primero para tener el helper de filtros listo.

### Test plan
- `tests/unit/mcp/test_cortex_search_filters.py`:
  - `test_search_no_filters_backward_compat` — args sin filtros, output igual que antes.
  - `test_search_doc_type_filter` — filtra ADRs.
  - `test_search_scope_enterprise` — scope respetado.
  - `test_search_invalid_doc_type_returns_error` — doc_type="banana" rechaza con MCP error.

---

## Item 9 — CLI `cortex review-knowledge pending/approve/reject`

### Descripcion

Fase 10 (Enterprise extensions) marca notas promovibles como `status: draft` cuando requieren review. Pero NO existe CLI para listar/aprobar/rechazar. Es un workflow incompleto.

### Por que importa

Sin esto, las notas que requieren review quedan en `status: draft` para siempre. El operador enterprise no tiene UI/CLI para procesar la cola.

### Propuesta de solucion

1. Crear `cortex/cli/review_knowledge.py`:
   ```python
   import typer
   from pathlib import Path
   from cortex.workspace.layout import WorkspaceLayout
   from cortex.documentation.validation import parse_frontmatter
   from cortex.enterprise.promotion_doctype import mark_as_accepted, mark_as_rejected

   review_app = typer.Typer(help="Manage promotion review queue.")

   @review_app.command("pending")
   def pending_command(
       scope: str = typer.Option("enterprise", "--scope"),
       doc_type: list[str] | None = typer.Option(None, "--doc-type"),
   ) -> None:
       """List notes in status: draft awaiting promotion review."""
       layout = WorkspaceLayout.discover(Path.cwd())
       vault_root = layout.enterprise_vault_path if scope == "enterprise" else layout.vault_path
       pending = []
       for md_path in vault_root.rglob("*.md"):
           fm = parse_frontmatter(md_path)
           if fm.get("status") == "draft" and (not doc_type or fm.get("doc_type") in doc_type):
               pending.append({
                   "path": str(md_path.relative_to(vault_root)),
                   "doc_type": fm.get("doc_type"),
                   "owner": fm.get("owner"),
                   "created_at": fm.get("created_at"),
               })
       _print_table(pending)

   @review_app.command("approve")
   def approve_command(
       path: str = typer.Argument(...),
       reviewer: str = typer.Option(..., "--reviewer"),
       reason: str = typer.Option("", "--reason"),
   ) -> None:
       """Promote a draft note to status: accepted and add audit_trail entry."""
       layout = WorkspaceLayout.discover(Path.cwd())
       full_path = (layout.enterprise_vault_path / path).resolve()
       mark_as_accepted(full_path, reviewer=reviewer, reason=reason)
       typer.echo(f"[OK] {path} -> status: accepted")

   @review_app.command("reject")
   def reject_command(
       path: str = typer.Argument(...),
       reviewer: str = typer.Option(..., "--reviewer"),
       reason: str = typer.Option(..., "--reason"),
       delete: bool = typer.Option(False, "--delete"),
   ) -> None:
       """Reject a draft note. By default moves to rejected/; with --delete removes."""
       layout = WorkspaceLayout.discover(Path.cwd())
       full_path = (layout.enterprise_vault_path / path).resolve()
       mark_as_rejected(full_path, reviewer=reviewer, reason=reason, delete=delete)
       action = "deleted" if delete else "moved to rejected/"
       typer.echo(f"[OK] {path} -> {action}")
   ```
2. Si los helpers `mark_as_accepted` y `mark_as_rejected` no existen en `cortex/enterprise/promotion_doctype.py`, agregarlos:
   ```python
   def mark_as_accepted(path: Path, *, reviewer: str, reason: str = "") -> None:
       """Update note frontmatter: status=accepted, append audit_trail."""
       ...

   def mark_as_rejected(path: Path, *, reviewer: str, reason: str, delete: bool = False) -> None:
       ...
   ```
3. Registrar en `cortex/cli/main.py`:
   ```python
   from cortex.cli.review_knowledge import review_app
   app.add_typer(review_app, name="review-knowledge")
   ```

### Esfuerzo
4h (CLI + helpers + tests).

### Riesgo
Medio. Modifica frontmatter de notas enterprise. Hay que cuidar concurrencia (no escribir si la nota cambio entre `pending` y `approve`).

### Dependencias
- `cortex/enterprise/promotion_doctype.py` debe tener (o se le agrega) `mark_as_accepted` y `mark_as_rejected`.

### Test plan
- `tests/unit/cli/test_review_knowledge.py`:
  - `test_pending_lists_draft_notes` — tmp enterprise vault con 3 notas draft + 2 accepted -> pending lista 3.
  - `test_approve_changes_status_to_accepted` — antes draft, despues accepted, audit_trail con reviewer.
  - `test_reject_moves_to_rejected_folder` — sin --delete, nota en rejected/.
  - `test_reject_with_delete_removes_file` — con --delete, file no existe.
  - `test_approve_fails_if_not_draft` — nota accepted, approve devuelve error.

---

## Item 10 — Migrar 4 consumers de `_legacy_shims.py` y eliminar el shim

### Descripcion

`cortex/documentation/_legacy_shims.py` define wrappers (`write_session_note`, `write_spec_note`, `write_tracked_item_note`) con firmas Fase 0 que delegan a los canonicos (`write_session_note_canonical`, etc.). Consumers actuales:

- `cortex/services/session_service.py:22`
- `cortex/services/spec_service.py:22`
- `cortex/workitems/service.py:83`
- Re-export en `cortex/documentation/__init__.py:74`
- Tests varios que importan los nombres legacy.

### Por que importa

Deuda explicita marcada en `feedback_no_technical_debt`. Mientras existan dos APIs (legacy kwargs + canonica dataclass), un agente IA puede usar la equivocada. La cirugia de Fase 13 dejo este item como bloque A pendiente con autorizacion dada.

### Propuesta de solucion

**Por consumer (ordenado por blast radius creciente):**

1. **`cortex/services/session_service.py:22`:**
   - Antes: `from cortex.documentation import write_session_note` (shim).
   - Despues:
     ```python
     from cortex.documentation import write_session_note_canonical
     from cortex.documentation.data import SessionData
     ```
   - Refactor del metodo `SessionService.create_session(...)`:
     ```python
     def create_session(self, *, title, spec_summary, ...) -> Path:
         data = SessionData(
             title=title,
             spec_summary=spec_summary,
             changes_made=changes_made or [],
             files_touched=files_touched or [],
             key_decisions=key_decisions or [],
             next_steps=next_steps or [],
             tags=tags or [],
             session_id=str(uuid.uuid4()),
             pr=...,
             branch=...,
             commit=...,
         )
         return write_session_note_canonical(self._vault, data=data)
     ```
   - Tests: `tests/unit/services/test_session_service.py` — pueden necesitar update si verifican firmas.

2. **`cortex/services/spec_service.py:22`:** analogo con `SpecData`.

3. **`cortex/workitems/service.py:83`:**
   - Antes: `from cortex.documentation import write_tracked_item_note` (shim).
   - Despues: usar `write_hu_note` con `HUData`.
   - Mapping: `tracked_item` -> `HUData(external_id=..., source=...)`.

4. **`cortex/documentation/__init__.py:74`:** eliminar el import del shim.

5. **Tests:** buscar usos de `write_session_note`, `write_spec_note`, `write_tracked_item_note` (nombres legacy):
   ```bash
   grep -rn "from cortex.documentation import write_session_note\b" tests/
   ```
   Actualizar imports a los canonicos.

6. **`cortex/documentation/_legacy_shims.py`:** `git rm`.

### Esfuerzo
4-5h.

### Riesgo
Medio. Services son hot path. Recomendado:
- Un commit por consumer (4 commits + 1 final que elimina el shim).
- Correr pytest entre cada commit.

### Dependencias
- Ninguna. Pero **bloqueante para #1** (mypy strict): el shim concentra los kwargs flexibles dificiles de tipar.

### Test plan
- Baseline antes: `pytest -q` (1416 passed).
- Despues de cada commit: pytest debe mantener 1416 passed.
- Verificar: `grep -rn "_legacy_shims" cortex/ tests/` retorna 0 matches.

---

## Item 11 — Dashboard cortex-pi UI extension (TypeScript)

### Descripcion

El webgraph backend ya emite `doc_type` por nodo y aristas tipadas (post #5+#6). Pero el dashboard de cortex-pi (TypeScript) no consume esa metadata enriquecida.

### Por que importa

Usuarios que usan Pi como IDE no ven la leyenda enriquecida ni las aristas typed. Cosmetica, no funcional.

### Propuesta de solucion

1. Localizar el codigo TS del dashboard:
   ```bash
   find cortex-pi/ -name "*.tsx" -o -name "*.ts" | xargs grep -l "webgraph\|snapshot-semantic"
   ```
2. Leer como consume actualmente `snapshot-semantic.json` y `meta.json`.
3. Implementar:
   - Render de leyenda usando `meta.json.legend`.
   - Colorizacion de nodos por `node.metadata.doc_type` (usando `meta.json.legend[doc_type].color`).
   - Aristas con `kind`, color, dasharray (desde `meta.json.edge_legend`).
4. Smoke manual: abrir Pi dashboard con un vault Cortex real, verificar leyenda visible y aristas coloreadas.

### Esfuerzo
4-6h (depende del estado del codigo TS).

### Riesgo
Bajo (solo UI).

### Dependencias
- **#5** (aristas typed) — el TS necesita los `edge.kind` para colorearlas.
- **#6** (episodic doc_type) — el TS necesita la leyenda episodic.

### Test plan
Smoke manual + screenshots en `docs/canonical-documentation/fase-09-webgraph-update/REALIZACION.md`.

### Recomendacion
**Diferir a sprint UI dedicado.** No es bloqueante para el cierre de la iniciativa canonical-documentation.

---

## Item 12 — File locking VectorCache multi-process

### Descripcion

`VectorCache` usa `threading.RLock` para safety dentro de un proceso. Si dos procesos cortex corren en paralelo (CLI `cortex sync-vault` + MCP server activo + autopilot finish simultaneamente), pueden corromper `chunks.bin` o `index.json`.

### Por que importa

Para single-user dev no es problema (convencion: no correr dos procesos). Para production multi-proceso (CI + dev local + MCP server) si.

Plan original (Fase 06) marca este item como "fuera de scope MVP".

### Propuesta de solucion

1. Agregar dependencia `fasteners>=0.19` (o `portalocker>=2.8` para Windows compat) a `pyproject.toml`:
   ```toml
   dependencies = [
       ...,
       "fasteners>=0.19",  # multi-process file locking
   ]
   ```
2. En `cortex/semantic/vector_cache.py::VectorCache`:
   ```python
   import fasteners
   from pathlib import Path

   class VectorCache:
       def __init__(self, persist_dir: Path, ..., lock_timeout: float = 30.0):
           self._persist_dir = persist_dir
           self._lockfile = persist_dir / "lock"
           self._inter_process_lock = fasteners.InterProcessLock(str(self._lockfile))
           self._lock_timeout = lock_timeout

       def _acquire(self) -> None:
           acquired = self._inter_process_lock.acquire(timeout=self._lock_timeout)
           if not acquired:
               raise TimeoutError(f"VectorCache lock not acquired in {self._lock_timeout}s. Another process holds it.")

       def _release(self) -> None:
           self._inter_process_lock.release()

       def put(self, ...):
           self._acquire()
           try:
               # logica actual
           finally:
               self._release()
       # Idem para get, invalidate, compact.
   ```
3. Test multi-proceso:
   ```python
   # tests/integration/test_vector_cache_multiprocess.py
   import subprocess
   def test_concurrent_puts_no_corruption(tmp_path):
       proc1 = subprocess.Popen([..., "put 1000 entries"])
       proc2 = subprocess.Popen([..., "put 1000 entries"])
       proc1.wait(); proc2.wait()
       # Verificar que el cache tiene 2000 entries sin corrupcion
   ```

### Esfuerzo
3-4h (implementacion) + 2h (testing exhaustivo).

### Riesgo
Medio. Concurrencia es dificil de debuggear. En Windows, fasteners puede tener edge cases.

### Dependencias
- Nueva dependencia (`fasteners` o `portalocker`).
- Decidir compat: si Windows es target, validar la libreria.

### Test plan
- `tests/integration/test_vector_cache_multiprocess.py`:
  - `test_concurrent_puts_no_corruption`
  - `test_lock_timeout_raises`
  - `test_lock_released_on_exception`

### Recomendacion
**Postergar a 0.6.x.** Marcado explicitamente "fuera de scope MVP" en Fase 06.

---

## Plan ordenado de ejecucion

### Si se ejecuta TODA la deuda (12 items):

| Dia | Items | Esfuerzo | Justificacion |
|-----|-------|----------|---------------|
| **1** | #2, #6, #5 | ~6h | Low-risk wins: tests + cosmetica webgraph. Sin dependencias. |
| **2** | #7, #8 | ~4h | CLI/MCP wiring. Extraer helper compartido. Sinergia entre los 2. |
| **3** | #10 | ~5h | Legacy shim cleanup. Commit por consumer (4 commits + 1 git rm). Blast radius medio. |
| **4** | #1, #4, #3, #9 | ~10h | mypy strict (post-#10 es mas facil), granular invalidation + auto-compaction (sinergia), enterprise review CLI. |
| Diferido | #11, #12 | ~10h | UI TS y multi-proc, no bloqueantes. |

**Cierre core (10 items, sin #11 y #12):** ~25 horas, 3 dias.
**Cierre total (12 items):** ~35 horas, 4 dias.

### Si se ejecuta solo lo critico (closeable hoy):

Items obligatorios para certificar "0 deuda tecnica formal" segun `feedback_no_technical_debt`:
- #1 (mypy strict — gate explicito)
- #2 (presenter tests — coverage gap explicito)
- #10 (legacy shim — deuda explicitamente marcada)
- #9 (review-knowledge — workflow enterprise incompleto)

**Esfuerzo critico:** ~14 horas, 2 dias.

---

## Gate de salida del plan

La deuda residual canonical-documentation se considera **cerrada al 100%** cuando:

- [ ] mypy strict pasa sobre `cortex/documentation/` (Item #1).
- [ ] `cortex/context_enricher/presenter.py` >= 90% coverage (Item #2).
- [ ] `VectorCache` auto-compacta al threshold configurado (Item #3).
- [ ] Re-indexar 1 chunk de un doc grande no re-embedea los otros 7 (Item #4).
- [ ] Webgraph muestra aristas typed `supersedes` con color distintivo (Item #5).
- [ ] Webgraph legend incluye "Episodic Memory" (Item #6).
- [ ] `cortex search "auth" --doc-type adr` funciona (Item #7).
- [ ] MCP `cortex_search` acepta filtros estructurales (Item #8).
- [ ] `cortex review-knowledge pending/approve/reject` operativo (Item #9).
- [ ] `cortex/documentation/_legacy_shims.py` eliminado, 4 consumers migrados (Item #10).
- [ ] (Opcional) Dashboard cortex-pi muestra leyenda enriquecida (Item #11).
- [ ] (Opcional) `VectorCache` soporta multi-proceso (Item #12).
- [ ] Suite global pasa al 100% (>=1416 tests, baseline post-cirugia).
- [ ] `cortex docs validate --all` reporta `Invalid: 0` (ya cumplido).
- [ ] `cortex doctor` sin errores (ya cumplido).

---

## Notas finales

1. **No improvises:** cada item tiene paths exactos, nombres de funciones reales, code sketches. Si encuentras discrepancia entre el plan y el codigo, **el codigo manda** — actualiza el plan con el hallazgo y procede.

2. **Test-first cuando aplique:** items #2, #5, #6, #9 son agregar tests + agregar codigo. Empezar por los tests fallando para validar el contrato.

3. **Commits granulares:** especialmente #10 (un commit por consumer). Si algo falla, rollback es trivial.

4. **Validacion entre items:** despues de cada item, correr `pytest --no-cov` para asegurar 0 regresiones.

5. **Skip-friendly:** si un item bloquea (e.g., #1 mypy revela 100 errores), saltearlo y volver al final. El orden es sugerido, no rigido.

6. **Memoria persistente:** al cerrar este plan, actualizar memoria con el cierre real.

---

## Referencias cruzadas

- Plan original: `docs/canonical-documentation/README.md`
- Fase 13 backlog: `docs/canonical-documentation/fase-13-backlog-consolidado/README.md`
- REALIZACION Fase 13: `docs/canonical-documentation/fase-13-backlog-consolidado/REALIZACION.md`
- Cirugia previa (cleanup commits): `32aa2e9` (eliminaciones + migraciones), `a1ad5ac` (fix backport cortex-sync).
- Memoria: `~/.claude/.../memory/project_cortex_ci_pipeline.md`, `feedback_no_technical_debt.md`.
