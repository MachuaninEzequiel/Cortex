# Fase 07 - Chunking

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Completada (2026-05-14) - ver [`REALIZACION.md`](REALIZACION.md)
**Esfuerzo estimado:** 2.5 dias (real: ~1 hora)
**Riesgo:** alto
**Dependencias:** Fase 06

---

## 1. Objetivo

Implementar la **Sub-capa 5a (Chunking)**:
- `Chunker` que splittea documentos por H2/H3 con metadata de seccion.
- Embedding text enriquecido con `doc_type` y `tags`.
- `VaultReader` modificado para indexar chunks en vez de documentos enteros.
- Agregacion chunk -> doc al hacer search (score doc = max score chunks).
- Backwards compatibility con `SemanticDocument` API publica.

Riesgo alto porque cambia el contrato interno de `VaultReader._embeddings` (de `dict[rel_path, vec]` a `dict[chunk_id, vec]`).

---

## 2. Archivos a crear / tocar

```text
cortex/semantic/
    chunker.py                       # NUEVO: chunk_document, Chunk class
    vault_reader.py                  # EXTENDIDO: chunk-based indexing y search
    markdown_parser.py               # EXTENDIDO: extract H2/H3 boundaries

cortex/models.py                     # EXTENDIDO: SemanticDocument.matched_chunk_id

tests/unit/semantic/
    test_chunker.py
    test_vault_reader_chunking.py

tests/performance/
    test_retrieval_recall.py         # A/B chunking vs no chunking
```

---

## 3. Responsabilidades

### `chunker.py`

Especificacion completa en `vectorization-design.md` seccion 3. Resumen:

```python
@dataclass(frozen=True)
class Chunk:
    parent_path: str
    chunk_id: str
    section_title: str
    section_position: int
    text: str
    doc_type: DocType
    tags: list[str]
    word_count: int

    @property
    def embedding_text(self) -> str:
        tags_str = " ".join(self.tags) if self.tags else ""
        return f"{self.doc_type.value} {tags_str} {self.section_title} {self.text}".strip()


def chunk_document(
    title: str,
    content: str,
    doc_type: DocType,
    tags: list[str],
    *,
    parent_path: str,
    min_words: int = 500,
    boundary: str = "h2",
    overlap_words: int = 0,
) -> list[Chunk]:
    """Split content into chunks for indexing."""
    if _word_count(content) < min_words:
        return [_make_single_chunk(content, title, doc_type, tags, parent_path)]

    if boundary == "h2":
        return _split_by_h2(content, title, doc_type, tags, parent_path, overlap_words)
    elif boundary == "h3":
        return _split_by_h2_or_h3(content, title, doc_type, tags, parent_path, overlap_words)
    elif boundary == "paragraph":
        return _split_by_paragraph(content, title, doc_type, tags, parent_path, overlap_words)
    else:
        raise ValueError(f"Unknown boundary: {boundary}")


def _word_count(text: str) -> int:
    return len(text.split())


def _make_single_chunk(content, title, doc_type, tags, parent_path) -> Chunk:
    return Chunk(
        parent_path=parent_path,
        chunk_id=parent_path,  # mismo que parent si no se splittea
        section_title=title,
        section_position=0,
        text=content,
        doc_type=doc_type,
        tags=tags,
        word_count=_word_count(content),
    )


H2_PATTERN = re.compile(r"^##\s+(.+?)$", re.MULTILINE)
H3_PATTERN = re.compile(r"^###\s+(.+?)$", re.MULTILINE)


def _split_by_h2(content, title, doc_type, tags, parent_path, overlap_words) -> list[Chunk]:
    """Split content by H2 headers."""
    # Find all H2 positions
    matches = list(H2_PATTERN.finditer(content))
    if not matches:
        return [_make_single_chunk(content, title, doc_type, tags, parent_path)]

    chunks = []
    # Prefix (text before first H2)
    if matches[0].start() > 0:
        prefix_text = content[:matches[0].start()].strip()
        if prefix_text:
            chunks.append(_make_chunk(prefix_text, "(prefix)", 0, doc_type, tags, parent_path))

    # Each H2 section
    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        section_start = match.end()
        section_end = matches[i+1].start() if i+1 < len(matches) else len(content)
        section_text = content[section_start:section_end].strip()

        # Overlap from previous chunk
        if overlap_words > 0 and i > 0 and chunks:
            prev_words = chunks[-1].text.split()
            overlap = " ".join(prev_words[-overlap_words:])
            section_text = overlap + " " + section_text

        chunks.append(_make_chunk(
            section_text, section_title, i + 1, doc_type, tags, parent_path
        ))

    return chunks


def _make_chunk(text, section_title, position, doc_type, tags, parent_path) -> Chunk:
    section_slug = slugify(section_title)
    return Chunk(
        parent_path=parent_path,
        chunk_id=f"{parent_path}#h2-{section_slug}",
        section_title=section_title,
        section_position=position,
        text=text,
        doc_type=doc_type,
        tags=tags,
        word_count=_word_count(text),
    )
```

### Integracion en `VaultReader`

```python
# cortex/semantic/vault_reader.py - EXTENSION

class VaultReader:
    def __init__(self, ...):
        # ...
        self._chunks: dict[str, Chunk] = {}        # chunk_id -> Chunk
        # _embeddings ahora indexado por chunk_id, no rel_path
        # _index sigue indexado por rel_path (parent doc)

    def index_file(self, relative_path: str) -> bool:
        path = resolve_safe(self.vault_path, relative_path)
        if not path.exists():
            return False

        doc = self._parser.parse(path)
        self._index[relative_path] = doc

        # Resolve doc_type
        doc_type = self._resolve_doc_type(doc, relative_path)
        route = resolve_route(doc_type) if doc_type else None

        # Chunk
        if route and route.chunking_enabled:
            chunks = chunk_document(
                title=doc.title, content=doc.content,
                doc_type=doc_type, tags=doc.tags,
                parent_path=relative_path,
                min_words=route.chunking_min_words,
                boundary=route.chunking_boundary,
            )
        else:
            chunks = [_make_single_chunk(doc.content, doc.title, doc_type or DocType.SPEC, doc.tags, relative_path)]

        # Invalidate old chunks for this parent
        old_chunk_ids = [cid for cid in self._chunks if self._chunks[cid].parent_path == relative_path]
        for cid in old_chunk_ids:
            self._chunks.pop(cid, None)
            self._embeddings.pop(cid, None)

        # Index new chunks with cache
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            chunk_fp = compute_fingerprint(chunk.embedding_text)
            vec = self._vector_cache.get(chunk_fp)
            if vec is None:
                vec = self._embedder.embed(chunk.embedding_text)
                self._vector_cache.put(chunk_fp, chunk.chunk_id, vec)
            self._embeddings[chunk.chunk_id] = vec

        # Update BM25 (still doc-level)
        self._update_bm25_stats(relative_path, doc)
        return True

    def search(self, query: str, top_k: int = 5, use_embeddings: bool = True) -> list[SemanticDocument]:
        """Hybrid search. Returns top-k docs (not chunks).

        Score per doc = max score across its chunks.
        """
        self._ensure_loaded()

        if not use_embeddings or not self._embeddings:
            return self._bm25_search(query, top_k)

        query_vec = self._embedder.embed(query)

        # Score all chunks
        chunk_scores: list[tuple[float, str]] = []
        for chunk_id, vec in self._embeddings.items():
            score = self._cosine_similarity(query_vec, vec)
            if score > 0:
                chunk_scores.append((score, chunk_id))

        # Aggregate to doc level
        doc_best: dict[str, tuple[float, str]] = {}
        for score, chunk_id in chunk_scores:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                continue
            parent = chunk.parent_path
            if parent not in doc_best or score > doc_best[parent][0]:
                doc_best[parent] = (score, chunk_id)

        # Sort and top-k
        sorted_docs = sorted(doc_best.items(), key=lambda kv: kv[1][0], reverse=True)[:top_k]

        results = []
        for parent_path, (score, chunk_id) in sorted_docs:
            doc = self._index[parent_path]
            chunk = self._chunks[chunk_id]
            doc_copy = doc.model_copy(update={
                "score": score,
                "matched_chunk_id": chunk_id,
                "matched_section_title": chunk.section_title,
            })
            results.append(doc_copy)
        return results
```

### Extension de `SemanticDocument`

```python
# cortex/models.py - EXTENSION

class SemanticDocument(BaseModel):
    # ... existentes
    score: float = 0.0
    matched_chunk_id: str | None = None       # NUEVO
    matched_section_title: str | None = None  # NUEVO
```

### Extension de `markdown_parser.py`

```python
# cortex/semantic/markdown_parser.py - EXTENSION

class MarkdownParser:
    # ... existente

    def extract_sections(self, content: str) -> list[Section]:
        """Extract H2 and H3 sections with positions."""
        # Util para chunker
```

---

## 4. Tests

### `test_chunker.py`

```python
def test_short_doc_single_chunk():
    chunks = chunk_document(
        title="T", content="short content under 500 words",
        doc_type=DocType.ADR, tags=["a"], parent_path="x.md",
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "x.md"
    assert chunks[0].section_title == "T"

def test_long_doc_with_h2_multiple_chunks():
    content = (
        "Intro paragraph.\n\n"
        "## Section A\nContent of A. " * 100 + "\n\n"
        "## Section B\nContent of B. " * 100
    )
    chunks = chunk_document(
        title="T", content=content,
        doc_type=DocType.RUNBOOK, tags=[], parent_path="x.md",
        min_words=100,
    )
    # Esperamos prefix + section A + section B
    assert len(chunks) == 3
    assert chunks[0].section_title == "(prefix)"
    assert chunks[1].section_title == "Section A"
    assert chunks[2].section_title == "Section B"

def test_no_h2_returns_single_chunk_even_if_long():
    content = "Plain text with no H2 " * 200
    chunks = chunk_document(
        title="T", content=content,
        doc_type=DocType.SPEC, tags=[], parent_path="x.md",
        min_words=100,
    )
    assert len(chunks) == 1

def test_h3_boundary_splits_on_h3():
    content = (
        "Intro.\n\n## Main\nMain text.\n\n### Sub A\n" + "Sub A text. " * 100 +
        "\n\n### Sub B\n" + "Sub B text. " * 100
    )
    chunks = chunk_document(
        title="T", content=content, doc_type=DocType.ADR, tags=[],
        parent_path="x.md", boundary="h3", min_words=100,
    )
    assert any(c.section_title == "Sub A" for c in chunks)
    assert any(c.section_title == "Sub B" for c in chunks)

def test_overlap_includes_trailing_words():
    """overlap_words=10 incluye 10 palabras del chunk previo."""

def test_embedding_text_includes_doc_type():
    chunks = chunk_document(
        title="T", content="x" * 100, doc_type=DocType.RUNBOOK, tags=["deploy"],
        parent_path="x.md",
    )
    assert "runbook" in chunks[0].embedding_text
    assert "deploy" in chunks[0].embedding_text

def test_chunk_id_unique():
    """Cada chunk tiene chunk_id distinto."""

def test_empty_section_text_handled():
    """H2 sin contenido produce chunk con text vacio."""

def test_prefix_text_before_first_h2():
    """Texto antes del primer H2 entra como (prefix)."""

def test_chunk_word_count():
    """word_count refleja palabras reales."""

@given(content=st.text(min_size=100, max_size=10000))
def test_chunk_always_returns_at_least_one(content):
    chunks = chunk_document(title="T", content=content, doc_type=DocType.SPEC,
                            tags=[], parent_path="x.md")
    assert len(chunks) >= 1
```

### `test_vault_reader_chunking.py`

```python
def test_indexed_long_doc_has_multiple_chunks(tmp_vault):
    """Long doc indexes as multiple chunks."""

def test_search_returns_doc_with_matched_chunk_id(tmp_vault):
    """Search result has matched_chunk_id populated."""

def test_short_doc_no_chunking(tmp_vault):
    """Short doc remains a single chunk."""

def test_modify_doc_invalidates_old_chunks(tmp_vault):
    """Modify content -> old chunks removed, new chunks added."""

def test_search_score_is_max_chunk_score(tmp_vault):
    """Score del doc = max score de sus chunks."""

def test_chunking_disabled_for_session(tmp_vault):
    """Sessions no se chunkean (config en routing)."""
```

### `test_retrieval_recall.py` (performance/quality)

```python
def test_chunking_improves_recall_in_long_docs(corpus_long_docs, eval_queries):
    """Recall@5 mejora con chunking en notas largas."""
    recall_without = _eval_recall(corpus_long_docs, eval_queries, chunking=False)
    recall_with = _eval_recall(corpus_long_docs, eval_queries, chunking=True)
    assert recall_with - recall_without >= 0.25  # objetivo de +25%
```

---

## 5. Criterios de diseno

- **Chunk_id es path + anchor:** `decisions/ADR-007.md#h2-decision`.
- **Backwards compat:** API publica de `VaultReader.search()` retorna `SemanticDocument`, no chunks.
- **Score agregado por max:** preserva el mejor match sin promediar.
- **Chunking config-driven:** RouteSpec dicta si chunkea y como.
- **Re-indexacion invalida chunks viejos:** evita drift.
- **`matched_chunk_id` y `matched_section_title`** son opcionales en `SemanticDocument`.

---

## 6. Checklist

- [x] `cortex/semantic/chunker.py` con `chunk_document` y helpers
- [x] `VaultReader.index_file()` chunk-aware
- [x] `VaultReader.search()` agrega por max chunk score
- [x] `SemanticDocument` extendido con campos opcionales
- [x] Tests chunker >= 9 (22 implementados)
- [x] Tests vault_reader chunking >= 6 (7 implementados)
- [x] Tests performance recall A/B >= 1 (2 implementados)
- [x] Coverage >= 90% (99% en chunker)

---

## 7. Gate de salida

- `pytest tests/unit/semantic/test_chunker.py tests/unit/semantic/test_vault_reader_chunking.py` pasa al 100%.
- A/B test con corpus de prueba muestra +25% recall en docs > 1000 palabras.
- Search retorna docs con `matched_chunk_id` poblado.
- Cold start con chunking + cache < 200ms para 1000 notas.
- `REALIZACION.md` documentado.

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Chunking rompe API existente | `SemanticDocument` campos opcionales; consumidores siguen funcionando |
| Score agregado por max sub-estima | Test contra promedio; max es elegido a proposito |
| Re-indexar olvida cleanup chunks viejos | Test explicito verifica invalidacion |
| Overhead de chunk metadata | Aceptable; chunks son ligeros |
| Markdown malformado rompe parser | try/except con fallback single chunk |
| Chunks demasiado pequenos (H2 con poco contenido) | OK; embedding sigue siendo informativo |
| Doc sin H2 + > min_words se queda como single chunk | OK; documented behavior |
| RouteSpec.chunking_enabled mal configurado | Default True; sessions explicitamente False |
| Performance de chunking en sync inicial | Batch embedding; cache hits aceleran |
| Recall delta < 25% en algunos corpus | Aceptable si > 15%; reportar y revisar config |

---

## 9. Notas para agentes implementadores

1. **Empezar por `chunker.py`** con todos los tests pasando antes de integrar.
2. **Test del A/B recall con corpus controlado.** Necesario para validar el objetivo.
3. **No tocar `MarkdownParser.parse()` API publica.** Solo agregar helpers.
4. **Chunks con `(prefix)` legitimo.** No filtrarlos.
5. **`section_title` puede tener caracteres especiales.** Usar slugify cuidadoso.
6. **Cleanup de chunks viejos al re-index** es crucial. Sin esto, hay drift.
7. **Cache hit rate debe seguir alto.** Verificar con stats.

---

## 10. Referencias

- `docs/canonical-documentation/vectorization-design.md` - especificacion completa
- `docs/canonical-documentation/architecture.md` - Capa 5a
- `cortex/semantic/markdown_parser.py` - parser base
- `cortex/semantic/vault_reader.py` - integracion
