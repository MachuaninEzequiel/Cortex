# Fase 06 - Vector Persistence

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Pendiente de ejecucion
**Esfuerzo estimado:** 1.5 dias
**Riesgo:** medio
**Dependencias:** ninguna (puede ir en paralelo con Fase 05)

---

## 1. Objetivo

Implementar la **Sub-capa 5b (Cache de vectores en disco)**:
- `VectorCache` class con get/put/invalidate.
- Layout en disco `.cortex/vectors/` con `index.json` + `chunks.bin`.
- Invalidacion por `fingerprint`, `schema_version`, `mtime`.
- Compaction de espacio reclamado.
- Integracion con `VaultReader.index_file()` y `sync()`.

Beneficio principal: cold start de vault de 1000 notas pasa de 8s a <100ms.

---

## 2. Archivos a crear / tocar

```text
cortex/semantic/
    vector_cache.py                  # NUEVO: VectorCache class
    vault_reader.py                  # EXTENDIDO: usar VectorCache en sync/index_file

cortex/cli/
    docs_vectorization.py            # NUEVO: subcomando 'cortex docs vectorization'

tests/unit/semantic/
    test_vector_cache.py
    test_vault_reader_with_cache.py

tests/performance/
    test_cold_start_perf.py          # NUEVO con benchmark
```

---

## 3. Responsabilidades

### `vector_cache.py`

```python
# cortex/semantic/vector_cache.py
from pathlib import Path
from dataclasses import dataclass, asdict
import numpy as np
import json
import threading
import struct

CACHE_SCHEMA_VERSION = 1
VECTOR_DTYPE = np.float32
VECTOR_DIM = 384  # all-MiniLM-L6-v2


@dataclass(frozen=True)
class CacheEntry:
    fingerprint: str
    chunk_id: str
    offset: int        # byte offset in chunks.bin
    dim: int
    schema_version: int


@dataclass
class CacheStats:
    total_entries: int
    valid_entries: int
    invalidated_entries: int   # entries marked deleted but not compacted
    size_bytes: int
    hit_count: int
    miss_count: int

    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total else 0.0


class VectorCache:
    """Persistent cache for embedding vectors.

    Layout:
        cache_dir/index.json       - map fingerprint -> CacheEntry
        cache_dir/chunks.bin       - contiguous float32 array
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = cache_dir / "index.json"
        self._bin_path = cache_dir / "chunks.bin"
        self._lock = threading.RLock()
        self._index: dict[str, CacheEntry] = {}
        self._invalidated: set[str] = set()
        self._hit_count = 0
        self._miss_count = 0
        self._load()

    def _load(self) -> None:
        """Load index from disk. If schema mismatch, reset."""
        if not self._index_path.exists():
            return
        try:
            with self._index_path.open() as f:
                raw = json.load(f)
            if raw.get("schema_version") != CACHE_SCHEMA_VERSION:
                # Schema changed; reset
                self._reset_corrupt()
                return
            self._index = {
                fp: CacheEntry(**entry)
                for fp, entry in raw.get("entries", {}).items()
            }
            self._invalidated = set(raw.get("invalidated", []))
        except (json.JSONDecodeError, KeyError, ValueError):
            self._reset_corrupt()

    def _reset_corrupt(self) -> None:
        """Reset cache on corruption."""
        self._index = {}
        self._invalidated = set()
        if self._bin_path.exists():
            self._bin_path.unlink()

    def get(self, fingerprint: str) -> np.ndarray | None:
        """Retrieve vector by fingerprint. Returns None on miss."""
        with self._lock:
            entry = self._index.get(fingerprint)
            if entry is None or fingerprint in self._invalidated:
                self._miss_count += 1
                return None
            self._hit_count += 1
            return self._read_vector_at(entry.offset, entry.dim)

    def put(self, fingerprint: str, chunk_id: str, vector: np.ndarray) -> None:
        """Store vector. If fingerprint exists, overwrites."""
        with self._lock:
            if vector.dtype != VECTOR_DTYPE:
                vector = vector.astype(VECTOR_DTYPE)
            if vector.shape != (VECTOR_DIM,):
                raise ValueError(f"Expected shape ({VECTOR_DIM},), got {vector.shape}")

            # If already exists, invalidate old entry
            if fingerprint in self._index:
                self._invalidated.add(fingerprint)

            # Append to chunks.bin
            offset = self._bin_path.stat().st_size if self._bin_path.exists() else 0
            with self._bin_path.open("ab") as f:
                f.write(vector.tobytes())

            self._index[fingerprint] = CacheEntry(
                fingerprint=fingerprint,
                chunk_id=chunk_id,
                offset=offset,
                dim=VECTOR_DIM,
                schema_version=CACHE_SCHEMA_VERSION,
            )
            self._invalidated.discard(fingerprint)
            self._save_index()

    def batch_get(self, fingerprints: list[str]) -> dict[str, np.ndarray]:
        """Bulk get. Returns dict of hits only."""
        return {fp: vec for fp in fingerprints if (vec := self.get(fp)) is not None}

    def batch_put(self, items: list[tuple[str, str, np.ndarray]]) -> None:
        """Bulk put. items = list of (fingerprint, chunk_id, vector)."""
        for fp, cid, vec in items:
            self.put(fp, cid, vec)

    def invalidate(self, fingerprint: str) -> bool:
        """Mark entry as invalidated. Returns True if existed."""
        with self._lock:
            if fingerprint in self._index:
                self._invalidated.add(fingerprint)
                self._save_index()
                return True
            return False

    def invalidate_by_chunk_id(self, chunk_id: str) -> int:
        """Invalidate all entries for a chunk_id. Returns count invalidated."""
        with self._lock:
            count = 0
            for fp, entry in list(self._index.items()):
                if entry.chunk_id.startswith(chunk_id):
                    self._invalidated.add(fp)
                    count += 1
            if count > 0:
                self._save_index()
            return count

    def compact(self) -> None:
        """Reclaim space from invalidated entries. Rewrites chunks.bin."""
        with self._lock:
            # Read all valid entries
            valid = {fp: e for fp, e in self._index.items() if fp not in self._invalidated}

            # Read their vectors
            vectors = {fp: self._read_vector_at(e.offset, e.dim) for fp, e in valid.items()}

            # Rewrite bin atomically
            tmp_bin = self._bin_path.with_suffix(".tmp")
            new_index: dict[str, CacheEntry] = {}
            with tmp_bin.open("wb") as f:
                for fp, vec in vectors.items():
                    offset = f.tell()
                    f.write(vec.tobytes())
                    new_index[fp] = CacheEntry(
                        fingerprint=fp,
                        chunk_id=valid[fp].chunk_id,
                        offset=offset,
                        dim=VECTOR_DIM,
                        schema_version=CACHE_SCHEMA_VERSION,
                    )

            # Atomic rename
            tmp_bin.replace(self._bin_path)
            self._index = new_index
            self._invalidated = set()
            self._save_index()

    def stats(self) -> CacheStats:
        size = self._bin_path.stat().st_size if self._bin_path.exists() else 0
        return CacheStats(
            total_entries=len(self._index),
            valid_entries=len(self._index) - len(self._invalidated),
            invalidated_entries=len(self._invalidated),
            size_bytes=size,
            hit_count=self._hit_count,
            miss_count=self._miss_count,
        )

    def _read_vector_at(self, offset: int, dim: int) -> np.ndarray:
        with self._bin_path.open("rb") as f:
            f.seek(offset)
            data = f.read(dim * 4)  # float32 = 4 bytes
        return np.frombuffer(data, dtype=VECTOR_DTYPE)

    def _save_index(self) -> None:
        """Persist index.json atomically."""
        data = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "entries": {fp: asdict(e) for fp, e in self._index.items()},
            "invalidated": list(self._invalidated),
        }
        tmp = self._index_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(self._index_path)
```

### Integracion en `VaultReader`

```python
# cortex/semantic/vault_reader.py - EXTENSION

class VaultReader:
    def __init__(self, vault_path, ..., vector_cache: VectorCache | None = None):
        # ...
        self._vector_cache = vector_cache or self._default_cache()

    def _default_cache(self) -> VectorCache:
        from cortex.workspace.layout import resolve_workspace_layout
        layout = resolve_workspace_layout(...)
        return VectorCache(layout.workspace_root / ".cortex" / "vectors")

    def sync(self) -> int:
        # ... existing logic, pero usando cache:
        for path in md_files:
            try:
                doc = self._parser.parse(path)
                rel = str(path.relative_to(self.vault_path))
                self._index[rel] = doc

                # Compute fingerprint
                fp = compute_fingerprint(doc.title + " " + doc.content)

                # Try cache first
                vec = self._vector_cache.get(fp)
                if vec is None:
                    vec = self._embedder.embed(doc.title + " " + doc.content)
                    self._vector_cache.put(fp, rel, vec)
                self._embeddings[rel] = vec
            except Exception as exc:
                logger.warning(...)
        # ...

    def index_file(self, relative_path: str) -> bool:
        # Same pattern: use cache
        ...
```

### CLI `cortex docs vectorization`

```python
# cortex/cli/docs_vectorization.py

import typer
from cortex.semantic.vector_cache import VectorCache

app = typer.Typer(help="Vectorization cache operations.")


@app.command()
def stats():
    """Print cache statistics."""
    cache = _get_cache()
    s = cache.stats()
    typer.echo(f"Total entries: {s.total_entries}")
    typer.echo(f"Valid: {s.valid_entries}")
    typer.echo(f"Invalidated: {s.invalidated_entries}")
    typer.echo(f"Size: {s.size_bytes / 1024:.1f} KB")
    typer.echo(f"Hit rate: {s.hit_rate*100:.1f}%")


@app.command()
def compact():
    """Reclaim space from invalidated entries."""
    cache = _get_cache()
    before = cache.stats().size_bytes
    cache.compact()
    after = cache.stats().size_bytes
    typer.echo(f"Compacted: {before/1024:.1f}KB -> {after/1024:.1f}KB")


@app.command()
def clear():
    """Clear entire cache (will be rebuilt on next sync)."""
    cache = _get_cache()
    # Clear all
    ...
```

Registrar en docs_subcommand:

```python
from cortex.cli.docs_vectorization import app as vec_app
docs_app.add_typer(vec_app, name="vectorization")
```

---

## 4. Tests

### `test_vector_cache.py`

```python
import pytest
import numpy as np
from cortex.semantic.vector_cache import VectorCache, CacheStats

def test_put_get_roundtrip(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    vec = np.random.rand(384).astype(np.float32)
    cache.put("fp1", "chunk1", vec)
    retrieved = cache.get("fp1")
    np.testing.assert_array_equal(retrieved, vec)

def test_miss_returns_none(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    assert cache.get("unknown") is None

def test_batch_put_get(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    items = [(f"fp{i}", f"c{i}", np.random.rand(384).astype(np.float32)) for i in range(5)]
    cache.batch_put(items)
    results = cache.batch_get(["fp0", "fp1", "fp2", "fp99"])
    assert len(results) == 3
    assert "fp99" not in results

def test_invalidate(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    vec = np.random.rand(384).astype(np.float32)
    cache.put("fp1", "chunk1", vec)
    assert cache.invalidate("fp1") is True
    assert cache.get("fp1") is None

def test_invalidate_nonexistent(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    assert cache.invalidate("fp1") is False

def test_invalidate_by_chunk_id(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "doc1.md#h2-section", np.random.rand(384).astype(np.float32))
    cache.put("fp2", "doc1.md#h2-other", np.random.rand(384).astype(np.float32))
    cache.put("fp3", "doc2.md#h2-x", np.random.rand(384).astype(np.float32))
    count = cache.invalidate_by_chunk_id("doc1.md")
    assert count == 2

def test_compact_reclaims_space(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    for i in range(10):
        cache.put(f"fp{i}", f"c{i}", np.random.rand(384).astype(np.float32))
    for i in range(5):
        cache.invalidate(f"fp{i}")
    size_before = cache.stats().size_bytes
    cache.compact()
    size_after = cache.stats().size_bytes
    assert size_after < size_before

def test_persistence_across_restarts(tmp_path):
    cache_dir = tmp_path / "vectors"
    cache1 = VectorCache(cache_dir)
    vec = np.random.rand(384).astype(np.float32)
    cache1.put("fp1", "chunk1", vec)
    del cache1

    cache2 = VectorCache(cache_dir)
    retrieved = cache2.get("fp1")
    np.testing.assert_array_equal(retrieved, vec)

def test_schema_version_mismatch_resets(tmp_path):
    """If schema_version changes, cache is reset."""

def test_corrupt_index_json_resets(tmp_path):
    """Corrupted index.json triggers reset."""

def test_stats_hit_miss_counts(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    cache.put("fp1", "c1", np.random.rand(384).astype(np.float32))
    cache.get("fp1")
    cache.get("fp1")
    cache.get("unknown")
    stats = cache.stats()
    assert stats.hit_count == 2
    assert stats.miss_count == 1
    assert stats.hit_rate == 2/3

def test_concurrent_writes_safe(tmp_path):
    """Multiple threads can write without corruption."""
    import threading
    cache = VectorCache(tmp_path / "vectors")
    def worker(idx):
        vec = np.random.rand(384).astype(np.float32)
        cache.put(f"fp{idx}", f"c{idx}", vec)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert cache.stats().total_entries == 20

def test_vector_dtype_converted(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    vec_f64 = np.random.rand(384).astype(np.float64)
    cache.put("fp1", "c1", vec_f64)
    retrieved = cache.get("fp1")
    assert retrieved.dtype == np.float32

def test_invalid_dimension_raises(tmp_path):
    cache = VectorCache(tmp_path / "vectors")
    vec = np.random.rand(100).astype(np.float32)
    with pytest.raises(ValueError):
        cache.put("fp1", "c1", vec)
```

### `test_vault_reader_with_cache.py`

```python
def test_sync_uses_cache_on_second_run(tmp_vault):
    """Second sync hits cache for unchanged docs."""
    vault = VaultReader(tmp_vault, vector_cache=VectorCache(tmp_path / "vectors"))
    vault.sync()
    stats1 = vault._vector_cache.stats()

    vault.sync()
    stats2 = vault._vector_cache.stats()
    assert stats2.hit_count > stats1.hit_count

def test_index_file_uses_cache(tmp_vault):
    """Single file index uses cache if available."""

def test_modified_file_invalidates_cache_entry(tmp_vault):
    """Changing content -> new fingerprint -> cache miss -> re-embed."""
```

### `test_cold_start_perf.py`

```python
@pytest.mark.benchmark
def test_cold_start_1000_notes_with_cache(benchmark, vault_1000_notes_cached):
    """<100ms with valid cache."""
    def cold_start():
        vault = VaultReader(vault_1000_notes_cached.path)
        _ = vault.search("test")
    benchmark(cold_start)
    assert benchmark.stats["mean"] < 0.1

@pytest.mark.benchmark
def test_cold_start_1000_notes_no_cache(benchmark, vault_1000_notes_no_cache):
    """Worst case for comparison."""
    benchmark(cold_start)
    # No strict assertion; just measure
```

---

## 5. Criterios de diseno

- **Single binary file** (`chunks.bin`): mas eficiente que un archivo por vector.
- **Append-only writes:** evita corruption.
- **Compaction explicita:** no automatic en runtime.
- **Atomic index updates:** tmp file + rename.
- **Schema versioning del cache** distinto del schema versioning del frontmatter.
- **`float32` fijo:** 384 dims * 4 bytes = 1.5KB por vector.
- **Thread-safe con RLock.**

---

## 6. Checklist

- [ ] `cortex/semantic/vector_cache.py` con `VectorCache`, `CacheEntry`, `CacheStats`
- [ ] `VaultReader.sync()` y `index_file()` usan cache
- [ ] CLI `cortex docs vectorization stats/compact/clear`
- [ ] Tests >= 15
- [ ] Tests de performance con benchmark
- [ ] Coverage >= 90%
- [ ] Persistencia verificada (restart)

---

## 7. Gate de salida

- `pytest tests/unit/semantic/test_vector_cache.py tests/unit/semantic/test_vault_reader_with_cache.py` pasa al 100%.
- `pytest tests/performance/test_cold_start_perf.py` muestra cold start < 100ms con cache.
- `cortex docs vectorization stats` funciona.
- Hit rate > 90% en test de stress (re-indexing).
- `REALIZACION.md` documentado.

---

## 8. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Corrupcion del bin por crash mid-write | Append-only; un crash deja bytes huerfanos pero index sigue valido |
| Index.json corrupto | Detect + reset; recompute desde sync |
| Compaction in-progress falla | tmp file rename atomico |
| Schema mismatch | Detect + reset masivo |
| Concurrencia | RLock; tests verifican |
| Disk full | Catch I/O error, fallback a in-memory para esa sesion |
| Modelo cambia dim | schema_version bump invalida todo |
| numpy serialization issues | Probar con varios numpy versions en CI |

---

## 9. Notas para agentes implementadores

1. **Empezar por tests basicos** (put/get) antes que features avanzadas (compact, concurrent).
2. **No usar pickle.** JSON + raw bytes es mas portable y robusto.
3. **Atomic writes con tmp + rename.** No escribir directo al archivo final.
4. **Float32 estricto.** No mezclar dtypes.
5. **Thread-safe desde el principio.** Refactor a posteriori es caro.
6. **CLI minimalista en MVP.** Stats, compact, clear.
7. **No prematuro mmap.** Lectura por seek+read es suficiente para 384 dims.

---

## 10. Referencias

- `docs/canonical-documentation/vectorization-design.md` - especificacion completa
- `docs/canonical-documentation/architecture.md` - Capa 5b
- `cortex/semantic/vault_reader.py` - integracion
