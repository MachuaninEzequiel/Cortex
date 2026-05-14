# Fase 07 - Chunking - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**Dependencias cumplidas:** Fase 06

---

## 1. Resumen

Se implemento la Sub-capa 5a (chunking inteligente):

1. **`cortex/semantic/chunker.py`** con `chunk_document()` y la dataclass
   `Chunk`. Soporta boundary `h2`, `h3` y `paragraph`, con overlap_words
   opcional para preservar contexto entre chunks adyacentes.
2. **`SemanticDocument`** extendido con `matched_chunk_id` y
   `matched_section_title` opcionales: cuando un doc chunkeado gana una
   busqueda, el caller sabe que seccion citar.
3. **`VaultReader`** integrado con el chunker: `sync()`, `index_file()`,
   `create_note()` y `update_note()` ahora producen un set de chunks por
   doc, cada uno embedido como vector independiente. La cache de Fase 06
   y los chunks comparten layout (el cache key es el fingerprint del
   `embedding_text` del chunk).
4. **`search()`** agrega chunk-score -> doc-score por max y devuelve los
   top-K documentos con metadata del chunk ganador.
5. **A/B recall test** que verifica que el chunking no pierde precisión
   en docs largos: una query que toca solo la *cola* del documento sigue
   recuperando el doc correcto (la seccion relevante se embedea por
   separado).

El chunker es config-driven via `DOC_TYPE_ROUTING`: cada DocType declara
`chunking_enabled`, `chunking_min_words` y `chunking_boundary`.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/semantic/chunker.py                            # 282 LOC: chunk_document, Chunk
    tests/unit/semantic/test_chunker.py                   # 22 tests
    tests/unit/semantic/test_vault_reader_chunking.py     # 7 tests
    tests/integration/test_chunking_recall.py             # 2 tests A/B

Modificados:
    cortex/models.py                # +matched_chunk_id, +matched_section_title
    cortex/semantic/vault_reader.py # _chunks dict, sync/index_file/create_note/update_note chunk-aware, search() agrega por parent
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 Chunk = unidad atomica de cache + retrieval

`VaultReader._embeddings` pasa de `dict[rel_path, vec]` a
`dict[chunk_id, vec]`. Para single-chunk docs el `chunk_id` coincide con
`rel_path`, asi que el comportamiento existente (un doc -> un embedding)
se preserva como caso degenerado.

Beneficios:
- El cache de Fase 06 funciona sin cambios: cada chunk tiene su
  `fingerprint` propio y se cachea/invalida por separado.
- La invalidacion granular permite re-indexar solo las secciones modificadas
  (TODO en el futuro; actualmente la re-indexacion purga TODOS los chunks
  del parent y re-genera).

### 3.2 Routing dicta el chunking

El chunker no decide cuando chunkar. La decision vive en
`DOC_TYPE_ROUTING[<doc_type>]`:
- `SESSION` y `HANDOFF` tienen `chunking_enabled=False` (notas cortas).
- `ADR`, `RUNBOOK`, `POSTMORTEM`, `INCIDENT`, `SPEC`, `ARCHITECTURE`,
  `CHANGELOG` tienen `chunking_enabled=True`.
- `HU` y `GLOSSARY` tienen `chunking_enabled=False` (data items cortos).

Cada DocType decide tambien su `chunking_min_words` (default 400-500) y
`chunking_boundary` (default `"h2"`).

### 3.3 Doc-score = max(chunk-scores)

En `search()`, despues de scorear cada chunk vs query, agrupamos por
`parent_path` y nos quedamos con el chunk de mejor score:

```python
best_per_doc[parent] = (max_score, best_chunk_id)
```

**Razon:** una nota es relevante si al menos UNA de sus secciones es
relevante. Usar el max preserva ese semantico. Una alternativa (avg)
penalizaria docs largos con secciones irrelevantes.

### 3.4 `matched_chunk_id`/`matched_section_title` opcionales

Para single-chunk docs (`chunk_id == parent_path`), ambos quedan en
`None`. Para multi-chunk, se populan con el chunk ganador. Asi consumers
existentes que no conocen los campos siguen funcionando sin cambios.

### 3.5 Embedding text incluye doc_type + tags + section_title

`Chunk.embedding_text` produce:

```
"<doc_type.value> <tags> <section_title> <text>"
```

Esto inyecta senal estructural en cada vector, mejorando la diferenciacion
entre secciones similares de docs distintos (e.g. dos ADR con "Decision"
sections).

### 3.6 Fallback robusto cuando el DocType no se infiere

Si el path no matchea ningun subfolder canonico (legacy notes en raiz,
notas en carpetas raras), el chunker no falla: produce un single chunk con
`doc_type=GLOSSARY` (fallback neutro). El doc sigue siendo indexable y
buscable.

### 3.7 Helpers internos vs API publica

Agregue 4 helpers privados al `VaultReader`:
- `_chunks_for_doc(rel_path, doc)`: chunkea un doc segun routing.
- `_purge_chunks_for_parent(rel_path)`: limpia chunks viejos antes de re-indexar.
- `_resolve_doc_type(rel_path)`: infiere DocType del path (Windows/Unix safe).
- `_resolve_route(doc_type)`: lazy import de `routing.resolve_route`.

Ninguno expuesto en `__all__`. Los consumers usan la API publica
(`sync`, `index_file`, `search`).

### 3.8 Overlap_words como parametro avanzado

`overlap_words > 0` carga las ultimas N palabras del chunk previo al
inicio del siguiente. Util para queries que cruzan boundaries (e.g. una
frase que termina justo en un H2). Default 0 (sin overlap) porque
duplica contenido y crece el cache.

---

## 4. Inconvenientes encontrados

### 4.1 Path normalization Windows vs POSIX en tests

`str(path.relative_to(vault))` en Windows usa `\\` mientras que mis tests
asumian `/`. Solucion: tests leen el `parent_path` real desde
`r._chunks.values()` en lugar de hardcodear el path. Tests ahora son
portables.

### 4.2 Test del chunker con body mal construido

Un test inicial usaba `"## Section A\nA " * 200` para simular un doc
largo. Eso produce un solo header H2 (no 200), porque las repeticiones
quedan en medio de la misma linea. Solucion: rewrite con 3 H2 sections
explicitos. Bug del test, no del chunker.

### 4.3 Sin otros inconvenientes

Smoke test inicial paso al primer intento. La integracion VaultReader +
chunker + VectorCache funciono sin friccion.

---

## 5. Tests ejecutados

```text
tests/unit/semantic/test_chunker.py                  22 passed
tests/unit/semantic/test_vault_reader_chunking.py     7 passed
tests/integration/test_chunking_recall.py             2 passed
---
Fase 07 nuevos:                                      31 passed
Suite global completa:                            1159 passed, 6 skipped
```

Pre-Fase 07 (post deuda 05): 1127. Ahora: 1159. **+32 nuevos** (31 Fase 07
+ 1 test paragraph overlap adicional para cobertura). **0 regresion.**

---

## 6. Coverage

```text
cortex/semantic/chunker.py            82/83   99%
cortex/semantic/vault_reader.py       ~78%    (no toda la clase es Fase 07; el chunking nuevo si esta cubierto)
```

La unica linea sin cubrir en `chunker.py` es el return defensive del
`_split_paragraphs` cuando todas las paragrafos se filtran a vacio
(unreachable bajo la guarda del `content.strip()` inicial). Aceptable.

`vault_reader.py` baja a 78% porque los tests de Fase 07 no ejercitan
todas las ramas legacy (BM25 fallback, frontmatter persistence, etc.).
Las ramas chunking nuevas SI estan cubiertas. Las ramas legacy ya tenian
sus propios tests en suites previas.

---

## 7. Checklist final (del README de la fase)

- [x] `cortex/semantic/chunker.py` con `chunk_document` y `Chunk`
- [x] `VaultReader.index_file()` chunk-aware
- [x] `VaultReader.search()` agrega por max chunk score
- [x] `SemanticDocument` extendido con `matched_chunk_id`/`matched_section_title`
- [x] Tests chunker >= 9 (22 implementados)
- [x] Tests vault_reader chunking >= 6 (7 implementados)
- [x] Tests A/B recall (2 implementados)
- [x] Coverage chunker >= 90% (99%)

---

## 8. Gate de salida

- [x] `pytest tests/unit/semantic/test_chunker.py tests/unit/semantic/test_vault_reader_chunking.py` pasa al 100% (29/29)
- [x] A/B recall test confirma que chunking no pierde precision en docs largos
- [x] Search retorna docs con `matched_chunk_id` poblado cuando aplica
- [x] Cold start con chunking + cache: re-sync hits all cached chunks (verified)
- [x] Sin regresion en suite global (1159 passed)
- [x] `REALIZACION.md` documentado

---

## 9. Pendientes / Backlog identificados

1. **Invalidacion granular de cache por chunk**: actualmente cuando se
   modifica un doc, todos sus chunks se borran del `_embeddings` dict.
   Una optimizacion futura podria comparar fingerprints viejos y nuevos
   por seccion y solo invalidar los chunks cambiados. Bajo impacto:
   re-indexar de cero usa la cache para chunks sin cambios (siguen siendo
   hits).

2. **Markdown parser AST-based**: el chunker usa regex para H2/H3. Una
   version futura podria delegar a `markdown-it-py` para soportar HTML
   embebido, tables, listas anidadas, etc. No bloqueante.

3. **`vault_reader.py` coverage 78%**: el bajo numero refleja el legacy
   path (BM25 fallback, index_meta persistence) que tiene sus propios
   tests en otras suites. No agrega valor moverlas a Fase 07.

4. **Test con corpus mas grande**: el A/B recall actual usa 2 ADRs. Para
   validar quality real conviene un corpus de 30-50 docs con relevance
   judgments. No bloqueante para MVP.

---

## 10. Proximos pasos

Fase 07 cierra el motor de retrieval semantico canonico. Fase 08
(retrieval filters) extiende el `ContextEnricher` con filtros estructurales
(`doc_types`, `min_status`, `tags_required`) y boost por intent. La capa
de chunks ahora permite a Fase 08 referenciar secciones especificas en el
output del enricher.
