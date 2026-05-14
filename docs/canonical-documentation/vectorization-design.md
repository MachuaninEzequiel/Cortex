# Vectorization Design - Chunking, Persistencia, Embedding Strategy

**Documento:** diseno completo de la capa de vectorizacion (Capa 5)
**Audiencia:** implementadores
**Estado:** especificacion normativa

---

## 1. Objetivos

1. **Maximizar recall en notas largas** mediante chunking por seccion.
2. **Reducir cold start** persistiendo vectores en disco con invalidacion correcta.
3. **Inyectar senal estructural** incluyendo `doc_type` y `tags` en el texto a embedear.
4. **Evitar re-computo** compartiendo cache entre vault local y enterprise.
5. **Preservar API publica** de `VaultReader` para no romper consumidores.

---

## 2. Estado actual vs objetivo

| Aspecto | Hoy | Objetivo |
|---|---|---|
| Embedding por nota | 1 vector | 1 vector si nota <500 palabras, N vectores si mas |
| Texto embedeado | `title + content` | `doc_type + tags + title + section_title + chunk_text` |
| Persistencia vectores | No (solo BM25 stats) | Si, en `.cortex/vectors/` |
| Cold start vault 1k notas | ~8s | <100ms |
| Sync local <-> enterprise | No | Si, por `fingerprint` |
| Truncacion silenciosa | Si (>512 tokens) | No (chunking previene) |

---

## 3. Sub-capa 5a: Chunking

### 3.1 Modulo

```text
cortex/semantic/
    chunker.py            # NUEVO
```

### 3.2 Contrato

```python
# cortex/semantic/chunker.py
from dataclasses import dataclass
from cortex.documentation.doc_type import DocType

@dataclass(frozen=True)
class Chunk:
    parent_path: str                # ej: "decisions/ADR-007-foo.md"
    chunk_id: str                   # ej: "decisions/ADR-007-foo.md#h2-decision"
    section_title: str              # ej: "Decision"
    section_position: int           # 0, 1, 2, ...
    text: str                       # contenido del chunk
    doc_type: DocType
    tags: list[str]
    word_count: int

    @property
    def embedding_text(self) -> str:
        """Texto efectivo a embedear con senal estructural."""
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
    boundary: str = "h2",                # "h2" | "h3" | "paragraph"
    overlap_words: int = 0,
) -> list[Chunk]:
    """Split content into chunks for indexing.

    Args:
        title: Note title (used as section_title for the first chunk if no H2 exists).
        content: Markdown body (sin frontmatter).
        doc_type: DocType del documento padre.
        tags: Tags del documento padre.
        parent_path: Ruta relativa al vault root.
        min_words: Si content tiene menos palabras, devuelve 1 chunk con todo.
        boundary: Donde splittear ("h2", "h3" o "paragraph").
        overlap_words: Palabras solapadas entre chunks consecutivos.

    Returns:
        Lista de Chunk. Garantia: si content es no vacio, retorna >= 1 chunk.
    """
```

### 3.3 Algoritmo de splitting

**Paso 1: Decision de chunking.**

```python
if word_count(content) < min_words:
    return [single_chunk(content, section_title=title, position=0)]
```

**Paso 2: Identificar boundaries.**

Regex para H2/H3:
```python
H2_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
H3_PATTERN = re.compile(r"^###\s+(.+)$", re.MULTILINE)
```

**Paso 3: Split por boundary.**

- Para `boundary="h2"`: split en lineas que matchean H2_PATTERN.
- Para `boundary="h3"`: split en lineas que matchean H2 OR H3.
- Para `boundary="paragraph"`: split por doble newline.

**Paso 4: Crear `Chunk` por seccion.**

- `section_title` = texto del header (sin "##").
- `text` = contenido bajo el header hasta el siguiente header del mismo nivel o superior.
- `chunk_id` = `f"{parent_path}#h2-{slugify(section_title)}"`.

**Paso 5: Overlap (si overlap_words > 0).**

- Cada chunk arrastra las ultimas `overlap_words` palabras del chunk anterior.

### 3.4 Edge cases

| Caso | Comportamiento |
|---|---|
| Content sin H2 | Single chunk con `section_title=title` |
| Content con solo H3 (sin H2) y `boundary=h2` | Single chunk |
| Content empieza con texto antes del primer H2 | Chunk inicial con `section_title="(prefix)"` |
| H2 sin contenido | Chunk con `text=""` (skip al embedear) |
| Markdown malformado | Best effort: pasa lo que puede, log warning |

### 3.5 Tests obligatorios

```python
# tests/unit/semantic/test_chunker.py

def test_short_doc_single_chunk():
    """Doc with <500 words returns single chunk."""

def test_long_doc_multiple_chunks_h2():
    """Doc with 3 H2 sections returns 3 chunks."""

def test_no_h2_returns_single_chunk():
    """Doc with no H2 returns single chunk."""

def test_h3_boundary():
    """boundary='h3' splits on H3 too."""

def test_overlap():
    """overlap_words=20 includes 20 trailing words in next chunk."""

def test_embedding_text_includes_metadata():
    """Chunk.embedding_text includes doc_type and tags."""

def test_chunk_id_unique():
    """All chunks have unique chunk_id."""

def test_empty_section_handled():
    """H2 with no body produces chunk with text=''."""

def test_prefix_text_before_first_h2():
    """Text before first H2 becomes a (prefix) chunk."""
```

---

## 4. Sub-capa 5b: Cache de vectores en disco

### 4.1 Modulo

```text
cortex/semantic/
    vector_cache.py       # NUEVO
```

### 4.2 Layout en disco

```text
.cortex/vectors/
    index.json            # {fingerprint: {chunk_id, dim, offset, schema_version}}
    chunks.bin            # array binario np.float32 contiguous
```

`chunks.bin` es un single file con concatenacion de vectores. `index.json` mapea fingerprint a (offset, dim) para leer del binario.

### 4.3 Contrato

```python
# cortex/semantic/vector_cache.py
from pathlib import Path
import numpy as np
from dataclasses import dataclass

@dataclass(frozen=True)
class CacheEntry:
    fingerprint: str
    chunk_id: str
    offset: int       # posicion en chunks.bin
    dim: int          # 384 para all-MiniLM-L6-v2
    schema_version: int


class VectorCache:
    """Persistent cache for embedding vectors.

    Layout:
        .cortex/vectors/index.json   - JSON map of fingerprint -> CacheEntry
        .cortex/vectors/chunks.bin   - contiguous float32 array

    Thread-safety: writes use file lock; reads are lock-free.
    """

    def __init__(self, cache_dir: Path): ...

    def get(self, fingerprint: str) -> np.ndarray | None:
        """Retrieve vector by fingerprint. Returns None on miss."""

    def put(self, fingerprint: str, chunk_id: str, vector: np.ndarray) -> None:
        """Store vector. Idempotent: same fingerprint overwrites."""

    def batch_get(self, fingerprints: list[str]) -> dict[str, np.ndarray]:
        """Bulk get; returns only hits."""

    def batch_put(self, items: list[tuple[str, str, np.ndarray]]) -> None:
        """Bulk put."""

    def invalidate(self, fingerprint: str) -> bool:
        """Remove entry. Returns True if existed."""

    def invalidate_by_chunk_id(self, chunk_id: str) -> int:
        """Remove all entries for a chunk_id (used when parent doc deleted)."""

    def compact(self) -> None:
        """Reclaim space from invalidated entries. Rewrites chunks.bin."""

    def stats(self) -> dict:
        """Return cache statistics."""
```

### 4.4 Algoritmo de invalidacion

Tres triggers:

1. **Fingerprint mismatch:** al re-indexar una nota, su nuevo fingerprint difiere del cacheado. Entrada vieja queda huerfana.
2. **Schema version bump:** si el schema del frontmatter cambia, invalidacion masiva.
3. **mtime drift:** archivo .md fue modificado externamente. `mtime > cache.created_at`.

**Compaction:**

- Trigger: > 30% del binario es huerfano.
- Procedimiento: re-leer todas las entradas activas, escribir nuevo binario, actualizar index.json atomicamente.

### 4.5 Performance esperada

| Operacion | Sin cache | Con cache |
|---|---|---|
| Cold start vault 1000 notas | 8000ms (embed) | 80ms (mmap + index parse) |
| Cold start vault 10000 notas | 80000ms | 800ms |
| Hit ratio tipico (re-indexacion) | 0% | 95%+ |
| Memoria de proceso | igual | mas vectores en mmap (lazy load) |

### 4.6 Tests obligatorios

```python
# tests/unit/semantic/test_vector_cache.py

def test_put_get_roundtrip():
    """put then get returns same vector."""

def test_miss_returns_none():
    """get on unknown fingerprint returns None."""

def test_batch_put_get():
    """batch operations consistent with individual."""

def test_idempotent_put():
    """Same fingerprint twice overwrites without growth."""

def test_invalidate():
    """Invalidate removes entry."""

def test_compact_reclaims_space():
    """compact reduces chunks.bin size after invalidations."""

def test_concurrent_reads():
    """Multiple readers don't block each other."""

def test_atomic_writes():
    """Index update is atomic (no partial state visible)."""

def test_persistence_across_restarts():
    """Cache survives process restart."""

def test_schema_version_bump_invalidates_all():
    """Increasing schema_version invalidates all entries."""
```

---

## 5. Sub-capa 5c: Embedding strategy con frontmatter

### 5.1 Cambio en `VaultReader.sync()` y `index_file()`

```python
# cortex/semantic/vault_reader.py - EXTENSION

def index_file(self, relative_path: str) -> bool:
    """Re-index a single file using chunking + cache."""

    path = resolve_safe(self.vault_path, relative_path)
    if not path.exists():
        return False

    doc = self._parser.parse(path)
    fingerprint = compute_fingerprint(doc.content)

    # Resolve doc_type from frontmatter or routing
    doc_type = self._resolve_doc_type(doc.frontmatter, relative_path)

    # Get RouteSpec for chunking settings
    route = resolve_route(doc_type)

    # Chunk if enabled
    if route.chunking_enabled:
        chunks = chunk_document(
            title=doc.title,
            content=doc.content,
            doc_type=doc_type,
            tags=doc.tags,
            parent_path=relative_path,
            min_words=route.chunking_min_words,
            boundary=route.chunking_boundary,
        )
    else:
        chunks = [_make_single_chunk(doc, doc_type, relative_path)]

    # Embed with cache
    for chunk in chunks:
        chunk_fp = compute_fingerprint(chunk.embedding_text)
        vector = self._vector_cache.get(chunk_fp)
        if vector is None:
            vector = self._embedder.embed(chunk.embedding_text)
            self._vector_cache.put(chunk_fp, chunk.chunk_id, vector)
        self._embeddings[chunk.chunk_id] = vector

    # Update BM25 stats (chunk-level)
    # ...
    return True
```

### 5.2 Texto efectivo a embedear

```text
embedding_text = f"{doc_type} {tags_joined} {section_title} {chunk_text}"
```

Ejemplo concreto:

```text
adr embedding performance onnx Decision Adopt ONNX backend for embeddings because...
```

vs hoy:

```text
ADR-007: Use ONNX backend for embeddings  Adopt ONNX backend for embeddings because...
```

El nuevo texto da al modelo senal de:
- `doc_type=adr` -> el modelo aprende que es una decision.
- `tags=embedding,performance,onnx` -> contexto semantico.
- `section_title=Decision` -> el chunk es la decision, no el contexto.

### 5.3 Backwards compatibility

`VaultReader.search()` API publica no cambia. Internamente:
- Top-k retorna chunks, agregados a nivel parent doc (max score).
- `SemanticDocument` resultante tiene campo extra opcional `matched_chunk_id` para que el presenter sepa que seccion citar.

```python
class SemanticDocument(BaseModel):
    # ... campos existentes
    matched_chunk_id: str | None = None        # NUEVO
    matched_section_title: str | None = None   # NUEVO
```

### 5.4 Agregacion chunk -> doc

```python
def search(self, query: str, top_k: int = 5) -> list[SemanticDocument]:
    """Search chunks, return top-k DOCUMENTS (not chunks).

    A document's score = max(scores of its chunks).
    """
    query_vec = self._embedder.embed(query)

    # Score all chunks
    chunk_scores: list[tuple[float, str]] = []  # (score, chunk_id)
    for chunk_id, vec in self._embeddings.items():
        score = cosine(query_vec, vec)
        if score > 0:
            chunk_scores.append((score, chunk_id))

    # Aggregate to doc level
    doc_best: dict[str, tuple[float, str]] = {}  # parent_path -> (score, chunk_id)
    for score, chunk_id in chunk_scores:
        parent = self._chunk_to_parent(chunk_id)
        if parent not in doc_best or score > doc_best[parent][0]:
            doc_best[parent] = (score, chunk_id)

    # Sort and top-k
    sorted_docs = sorted(doc_best.items(), key=lambda kv: kv[1][0], reverse=True)[:top_k]

    results = []
    for parent_path, (score, chunk_id) in sorted_docs:
        doc = self._index[parent_path]
        doc_copy = doc.model_copy(update={
            "score": score,
            "matched_chunk_id": chunk_id,
            "matched_section_title": self._chunk_section_title(chunk_id),
        })
        results.append(doc_copy)
    return results
```

---

## 6. Sub-capa 5d: Sync local <-> enterprise por `fingerprint`

### 6.1 Cuando aplica

Durante promotion:

```python
def promote_to_enterprise(local_path: str, enterprise_vault: VaultReader) -> None:
    """Promote a note from local to enterprise."""
    local_doc = local_vault.get(local_path)
    fp = local_doc.frontmatter.fingerprint

    # Si enterprise ya tiene el vector con este fingerprint, no re-embedea.
    cached_vec = enterprise_vault._vector_cache.get(fp)
    if cached_vec is not None:
        # Reuse: copy entry to enterprise cache
        ...
    else:
        # Miss: enterprise embedea normalmente
        enterprise_vault.index_file(target_path)
```

### 6.2 Ganancia

Para promociones bulk (ej: 100 ADRs a la vez), enterprise no re-embedea ninguno. Ahorra ~100 * 50ms = 5s.

Mas importante: garantiza que **vector enterprise == vector local** para el mismo contenido (no hay drift entre embedders ligeramente distintos).

---

## 7. Sub-capa 5e: Boost por tipo en retrieval

Ver `retrieval-design.md` seccion 4 para detalle. La vectorizacion provee:

- `doc_type` en `Chunk.embedding_text` -> el vector ya conoce el tipo.
- `RouteSpec.retrieval_boost_per_intent` -> tabla de boost multiplicativo.

El boost se aplica en el `enricher`, no en el `vault_reader`.

---

## 8. Configuracion

```yaml
# config.yaml - seccion vectorization
vectorization:
  embedder:
    model: all-MiniLM-L6-v2
    backend: onnx
  chunking:
    enabled: true
    default_boundary: h2
    default_min_words: 500
    default_overlap_words: 0
  cache:
    enabled: true
    cache_dir: .cortex/vectors
    compact_threshold: 0.3   # compact when 30% huerfano
```

---

## 9. Migracion del estado actual

### 9.1 Backfill de vectores

Primera ejecucion tras la implementacion:

1. Vault tiene N notas, cache vacio.
2. `VaultReader.sync()` se ejecuta.
3. Cada nota se chunkifica, se embedea, se persiste en cache.
4. Cold start posterior: <100ms (cache hit).

### 9.2 Rollback

Si la vectorizacion nueva tiene problemas:

1. `cortex docs vectorization rollback` borra `.cortex/vectors/`.
2. Volver al code base anterior.
3. Sync re-construye sin chunking ni cache.

### 9.3 Coexistencia con ChromaDB (memoria episodica)

ChromaDB persiste sus propios vectores separadamente. La memoria episodica NO se chunka (cada entry es chunk implicito ya). Solo la memoria semantica (vault) se beneficia.

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Chunking degrada precision para notas cortas | Skip si <500 palabras (configurable) |
| Cache corrupto bloquea startup | Fallback a re-embed si parse falla; checksum del cache |
| Disco se llena con vectores | `cortex docs vectorization stats` muestra uso; compact periodico |
| Embeddings con metadata cambian semantica | A/B test antes de habilitar por default |
| Race condition al escribir cache | File lock + atomic rename |
| Vector dimension cambia (modelo diferente) | `schema_version` del cache fuerza invalidacion |
| Compatibility con memoria episodica | Ambas usan misma `Embedder` instance; mismo modelo, mismo espacio |

---

## 11. Metricas a monitorear

| Metrica | Definicion | Objetivo |
|---|---|---|
| Cache hit rate | hits / (hits + misses) | >= 90% en operacion normal |
| Cold start time | tiempo desde init a primer search | <100ms para 1000 notas |
| Chunk count distribution | histograma de chunks por nota | mediana 1-2, p95 <= 10 |
| Search latency p50/p95 | tiempo de search() | <50ms / <200ms |
| Cache size | bytes en `.cortex/vectors/` | <100MB para 10k notas |
| Recall delta (A/B test) | recall@5 con chunking vs sin | +25% en notas >1000 palabras |

---

## 12. Decisiones clave

1. **Single binary file (`chunks.bin`)** vs un archivo por vector: binary file es mas rapido para cold start (1 syscall) y mas eficiente en disco.
2. **`np.float32`** vs `float64`: 384 dims * 4 bytes = 1.5KB por vector; 10k vectores = 15MB. Aceptable.
3. **Chunking por H2 default** vs paragraph: H2 es coarse pero coherente; paragraph fragmenta demasiado.
4. **Embedding text incluye doc_type/tags** vs solo content: pequena perdida de generalidad, gran ganancia de precision tematica.
5. **Cache invalidacion por fingerprint** vs por mtime: fingerprint es robusto a re-renderizado equivalente.
6. **Compact manual/auto-trigger** vs siempre: trigger automatico al 30% huerfano evita degradacion sin overhead constante.
