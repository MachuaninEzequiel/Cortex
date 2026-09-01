"""
cortex.semantic.vault_reader
----------------------------
Reads, indexes and manages a markdown knowledge base (Obsidian vault).
Supports wiki-links ([[note]]), frontmatter tags and **semantic vector search**.

The vault is embedded using the same ``Embedder`` as the episodic layer,
so both memory types live in the same vector space — enabling true semantic
retrieval and cross-source Reciprocal Rank Fusion.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from cortex.documentation.common import yaml_dump_safe
from cortex.documentation.doc_type import DocType
from cortex.documentation.inventory import classify_path
from cortex.episodic.embedder import Embedder
from cortex.models import SemanticDocument
from cortex.security.paths import resolve_safe, validate_under_root
from cortex.semantic.chunker import Chunk, chunk_document
from cortex.semantic.markdown_parser import MarkdownParser
from cortex.semantic.vector_cache import DEFAULT_MODEL_NAME, VectorCache, cache_fingerprint

logger = logging.getLogger(__name__)

# Index file persisted alongside the vault
_INDEX_FILE = ".cortex_index.json"

# Fallback model identity used to salt cache fingerprints when the embedder
# object does not expose ``model_name`` (Fix A2/A3 wiring).
DEFAULT_EMBEDDING_MODEL = DEFAULT_MODEL_NAME


class VaultReader:
    """
    Indexes and searches a directory of markdown files using **vector
    embeddings** (semantic search) backed by an optional BM25 keyword
    signal.

    The vault is loaded lazily and cached in memory. Call :meth:`sync`
    after external edits to refresh the index.

    Args:
        vault_path:       Path to the root directory containing ``.md`` files.
        embedding_model:  Embedding model name (passed to ``Embedder``).
        embedding_backend: ``"local"`` or ``"openai"``.
    """

    def __init__(
        self,
        vault_path: str = "vault",
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_backend: str = "onnx",
        *,
        vector_cache: VectorCache | None = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self._parser = MarkdownParser()
        self._index: dict[str, SemanticDocument] = {}
        self._embeddings: dict[str, list[float]] = {}  # rel_path → vector
        self._embedder = Embedder(model_name=embedding_model, backend=embedding_backend)  # type: ignore[arg-type]
        self._loaded = False
        # BM25 pre-computed stats
        self._doc_lengths: dict[str, int] = {}
        self._avgdl: float = 0.0
        self._idf: dict[str, float] = {}
        # Persistent vector cache (Fase 06 of canonical-documentation).
        # When None, all vectors are recomputed on each sync — the legacy
        # behaviour. When provided, sync/index_file hit the cache by
        # fingerprint of the embedding text and only embed cache misses.
        self._vector_cache: VectorCache | None = vector_cache
        # Chunk index (Fase 07). When chunking is enabled for a doc_type
        # via DOC_TYPE_ROUTING, ``_chunks[chunk_id]`` carries the section
        # metadata for the corresponding entry in ``_embeddings``.
        # ``chunk_id`` falls back to ``rel_path`` for single-chunk docs.
        self._chunks: dict[str, Chunk] = {}
        # Ruta nativa Rust (Obra 03, Gate G1). Activa SOLO con CORTEX_NATIVE=1
        # y el módulo compilado; el default es la ruta Python pura (paridad).
        # ``_native_matrix`` es la matriz f64 C-contigua (n_chunks × dim)
        # empacada UNA vez por estado del índice — jamás por query (regla de
        # APIs batch/gruesas). Se invalida en cada mutación de _embeddings.
        self._native_matrix: Any = None  # np.ndarray | None (import diferido)
        self._native_warned = False
        # Índice BM25 nativo (G3): corpus + snapshot IDF en Rust. Se reconstruye
        # completo cuando ``_native_bm25_dirty`` (cualquier mutación del vault).
        self._native_bm25_index: Any = None
        self._native_bm25_paths: list[str] = []  # alineado con el índice Rust
        self._native_bm25_dirty = True

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def sync(self) -> int:
        """
        (Re-)index all markdown files in the vault — parse, chunk, embed
        and pre-compute BM25 statistics.

        Returns:
            Number of documents indexed (NOT chunks).
        """
        self._index.clear()
        self._embeddings.clear()
        self._chunks.clear()
        self._doc_lengths.clear()
        self._idf.clear()
        self._invalidate_native_caches()

        if not self.vault_path.exists():
            logger.warning("Vault path does not exist: %s", self.vault_path)
            return 0

        md_files = list(self.vault_path.rglob("*.md"))
        # Aggregate all chunks across docs for a single batch embed.
        chunk_buffer: list[Chunk] = []

        for path in md_files:
            try:
                doc = self._parser.parse(path)
                rel = str(path.relative_to(self.vault_path))
                self._index[rel] = doc
                doc_chunks = self._chunks_for_doc(rel, doc)
                for ch in doc_chunks:
                    self._chunks[ch.chunk_id] = ch
                    chunk_buffer.append(ch)
                # BM25 stays at doc level (legacy keyword fallback).
                search_text = f"{doc.title} {doc.content}"
                self._doc_lengths[rel] = len(search_text.split())
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", path, exc)

        # Batch embed every chunk in one shot, hitting the cache first.
        if chunk_buffer:
            chunk_ids = [c.chunk_id for c in chunk_buffer]
            texts = [c.embedding_text for c in chunk_buffer]
            vectors = self._embed_batch_with_cache(chunk_ids, texts)
            for cid, vec in zip(chunk_ids, vectors, strict=False):
                self._embeddings[cid] = vec

        # Pre-compute BM25 IDF
        self._invalidate_native_caches()
        self._compute_idf()
        docs = list(self._doc_lengths.values())
        self._avgdl = sum(docs) / len(docs) if docs else 1.0

        # Persist index metadata (embeddings are re-computed on load — see note)
        self._save_index_meta()

        self._loaded = True
        logger.info("Vault indexed: %d documents", len(self._index))
        return len(self._index)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.sync()

    # ------------------------------------------------------------------
    # Semantic (vector) search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5, use_embeddings: bool = True) -> list[SemanticDocument]:
        """
        **Hybrid Search** over the vault.

        Scoring is done at the chunk level (when chunking is enabled) and
        aggregated to the parent document by taking the max chunk score. The
        returned :class:`SemanticDocument` instances carry ``matched_chunk_id``
        and ``matched_section_title`` so callers can cite the relevant
        section.

        Args:
            query:          Natural-language query string.
            top_k:          Maximum number of documents to return.
            use_embeddings: If False, skips vector search and uses BM25 only.
        """
        self._ensure_loaded()

        if not use_embeddings or not self._embeddings:
            return self._bm25_search(query, top_k)

        query_vec = self._embedder.embed(query)
        # Fuente de scores: nativa Rust (CORTEX_NATIVE=1) o Python pura.
        # AMBAS producen los mismos bits; la agregación max-por-doc es UNA sola
        # ruta → paridad estructural del top-k.
        native_scores = self._native_scores(query_vec)
        if native_scores is not None:
            score_source: Iterable[float] = native_scores
        else:
            score_source = (
                self._cosine_similarity(query_vec, vec)
                for vec in self._embeddings.values()
            )
        # Aggregate chunks -> parent doc with max score.
        best_per_doc: dict[str, tuple[float, str]] = {}
        for chunk_id, score in zip(self._embeddings.keys(), score_source, strict=True):
            if score <= 0:
                continue
            chunk = self._chunks.get(chunk_id)
            parent = chunk.parent_path if chunk is not None else chunk_id
            current = best_per_doc.get(parent)
            if current is None or score > current[0]:
                best_per_doc[parent] = (score, chunk_id)

        scored: list[tuple[float, SemanticDocument]] = []
        for parent, (score, chunk_id) in best_per_doc.items():
            doc = self._index.get(parent)
            if doc is None:
                continue
            chunk = self._chunks.get(chunk_id)
            updates = {"score": score}
            if chunk is not None and chunk.chunk_id != parent:
                updates["matched_chunk_id"] = chunk.chunk_id
                updates["matched_section_title"] = chunk.section_title
            scored.append((score, doc.model_copy(update=updates)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    # ------------------------------------------------------------------
    # BM25 fallback
    # ------------------------------------------------------------------

    def _bm25_search(self, query: str, top_k: int, *, k1: float = 1.5, b: float = 0.75) -> list[SemanticDocument]:
        """BM25 keyword search — used when embeddings are unavailable."""
        terms = query.lower().split()
        if not terms:
            return []

        max(len(self._index), 1)

        # Ruta nativa Rust (Obra 03, Gate G3): top-k directo desde Rust con
        # scores bit-idénticos y desempate estable replicado (a igual score
        # gana el menor índice de inserción); model_copy diferido al top-k.
        # None ⇒ ruta Python pura (default, paridad).
        pares = self._native_bm25_topk(terms, k1, b, top_k)
        if pares is not None:
            return [
                self._index[self._native_bm25_paths[i]].model_copy(
                    update={"score": score}
                )
                for score, i in pares
            ]

        scored: list[tuple[float, SemanticDocument]] = []

        for rel_path, doc in self._index.items():
            text = (doc.title + " " + doc.content).lower()
            doc_len = self._doc_lengths.get(rel_path, 1)
            score = 0.0
            for term in terms:
                idf = self._idf.get(term, 0.0)
                if idf == 0:
                    continue
                tf = text.count(term)
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * doc_len / self._avgdl)
                score += idf * (numerator / denominator)
            if score > 0:
                doc_copy = doc.model_copy(update={"score": score})
                scored.append((score, doc_copy))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def _compute_idf(self) -> None:
        """Pre-compute IDF values from indexed documents."""
        n_docs = max(len(self._index), 1)
        term_doc_freq: dict[str, int] = {}

        for doc in self._index.values():
            text = (doc.title + " " + doc.content).lower()
            seen_terms: set[str] = set()
            for word in text.split():
                if word not in seen_terms:
                    term_doc_freq[word] = term_doc_freq.get(word, 0) + 1
                    seen_terms.add(word)

        for term, df in term_doc_freq.items():
            self._idf[term] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------
    # Native Rust scoring (Obra 03, Gate G1) — opt-in vía CORTEX_NATIVE=1
    # ------------------------------------------------------------------

    def _invalidate_native_caches(self) -> None:
        """Marca los cachés nativos como obsoletos (llamar tras mutar el índice).

        Cubre la matriz empacada del scoring (G1) y el índice BM25 nativo (G3).
        Ambos se reconstruyen lazy: una sola vez por estado del índice, en la
        próxima query nativa.
        """
        self._native_matrix = None
        self._native_bm25_dirty = True

    def _native_scores(self, query_vec: list[float]) -> list[float] | None:
        """Scores cosine batch vía Rust para TODOS los chunks (o ``None``).
        Devuelve ``None`` cuando la ruta nativa no aplica (flag apagado,
        módulo ausente o índice vacío) y la llamante usa la ruta Python pura —
        comportamiento idéntico al default (regla R5.6 del HANDOFF).

        Paridad bit-a-bit: el núcleo Rust replica la suma compensada de Neumaier
        del builtin ``sum()`` de CPython ≥3.12 (ver cortex-core::scoring).
        La matriz se empaca preservando el orden de inserción de ``_embeddings``
        y se cachea hasta la próxima mutación del índice.
        """
        if os.environ.get("CORTEX_NATIVE") != "1":
            return None
        try:
            from cortex_core import _native
            import numpy as np
        except ImportError:
            if not self._native_warned:
                logger.warning(
                    "CORTEX_NATIVE=1 pero cortex_core._native no está compilado; "
                    "se usa la ruta Python pura. Compilá con: .venv/bin/python -m "
                    "maturin develop --release -m rust/crates/cortex-py/Cargo.toml"
                )
                self._native_warned = True
            return None

        if not self._embeddings:
            return None

        dim = len(query_vec)
        if self._native_matrix is None or self._native_matrix.shape != (
            len(self._embeddings),
            dim,
        ):
            # Empacado UNA vez por estado de índice (orden de inserción del dict,
            # determinista desde sync()). C-contigua float64 → vista zero-copy en Rust.
            self._native_matrix = np.asarray(
                list(self._embeddings.values()), dtype=np.float64
            ).reshape(len(self._embeddings), -1)
        # El query es chico (dim floats): conversión explícita; la matriz grande
        # pasa como vista sin copia.
        return _native.cosine_scores(
            np.asarray(query_vec, dtype=np.float64), self._native_matrix
        ).tolist()

    def _native_bm25_ready(self) -> bool:
        """Garantiza índice BM25 nativo sincronizado; False sin módulo/flag.

        Reconstrucción completa y lazy ante cualquier mutación del vault
        (dirty flag). Devuelve True sólo con CORTEX_NATIVE=1 y módulo presente.
        """
        if os.environ.get("CORTEX_NATIVE") != "1":
            return False
        try:
            from cortex_core import _native
        except ImportError:
            if not self._native_warned:
                logger.warning(
                    "CORTEX_NATIVE=1 pero cortex_core._native no está compilado; "
                    "se usa la ruta Python pura. Compilá con: .venv/bin/python -m "
                    "maturin develop --release -m rust/crates/cortex-py/Cargo.toml"
                )
                self._native_warned = True
            return False

        if not self._index:
            return False

        if (
            self._native_bm25_dirty
            or self._native_bm25_index is None
            or len(self._native_bm25_index) != len(self._index)
        ):
            ix = _native.NativeBm25Index()
            paths = list(self._index.keys())
            batch = 500  # API gruesa: lotes grandes, jamás llamada-por-doc
            for i in range(0, len(paths), batch):
                lote = paths[i : i + batch]
                textos = [
                    f"{self._index[p].title} {self._index[p].content}".lower()
                    for p in lote
                ]
                lens = [self._doc_lengths.get(p, 1) for p in lote]
                ix.add_batch(lote, textos, lens)
            ix.set_stats(list(self._idf.keys()), list(self._idf.values()), float(self._avgdl))
            # Calentar el pool de threads de rayon FUERA de cualquier medición:
            # si no, la primera query paga el spawn (~ms) y contamina el p99.
            ix.search([], 0.0, 0.0)
            self._native_bm25_index = ix
            # Snapshot de rutas alineado con el orden interno del índice Rust:
            # top_k devuelve índices de documento, no rutas.
            self._native_bm25_paths = paths
            self._native_bm25_dirty = False
        return True

    def _native_bm25_scores(
        self, terms: list[str], k1: float, b: float
    ) -> list[float] | None:
        """Scores BM25 de TODO el corpus vía Rust (o ``None`` → ruta Python).

        Réplica bit a bit del bucle de ``_bm25_search`` (tf por substring,
        skip de idf==0, acumulación f64 secuencial). Usado por los tests de
        paridad; la ruta de búsqueda usa `_native_bm25_topk`.
        """
        if not self._native_bm25_ready():
            return None
        return self._native_bm25_index.search(terms, k1, b).tolist()

    def _native_bm25_topk(
        self, terms: list[str], k1: float, b: float, top_k: int
    ) -> list[tuple[float, int]] | None:
        """Top-K BM25 directo desde Rust (o ``None`` → ruta Python pura).

        Desempate replicado exactamente: a igual score gana el menor índice
        de inserción (equivale al sort estable descendente de Python sobre el
        orden de ``_index`` en el momento del rebuild).
        """
        if not self._native_bm25_ready():
            return None
        return [
            (score, int(i))
            for score, i in self._native_bm25_index.top_k(terms, k1, b, max(top_k, 1))
        ]

    # ------------------------------------------------------------------
    # Cache-aware embedding helpers (Fase 06)
    # ------------------------------------------------------------------

    def _drop_vector_cache(self, reason: str) -> None:
        """Degrade to direct embedding after a cache failure (Fix A2).

        Loudly visible (WARNING): a broken cache must slow things down or
        cost re-embeddings, but it must never corrupt results silently.
        """
        logger.warning(
            "Vector cache unusable (%s); continuing WITHOUT cache "
            "(vectors will be recomputed on next run)", reason,
        )
        self._vector_cache = None

    def _embed_single_with_cache(
        self, rel_path: str, search_text: str
    ) -> list[float]:
        """Embed one search_text, hitting the vector cache when available."""
        if self._vector_cache is None:
            return self._embedder.embed(search_text)

        model_name = getattr(self._embedder, "model_name", DEFAULT_EMBEDDING_MODEL)
        fp = cache_fingerprint(model_name, search_text)
        cached = self._vector_cache.get(fp)
        if cached is not None:
            return cached.tolist()

        vec = self._embedder.embed(search_text)
        try:
            import numpy as _np
            arr = _np.asarray(vec, dtype=_np.float32)
            self._vector_cache.put(fp, rel_path, arr)
        except Exception as exc:
            # Fix A2: cache write failures are degraded loudly to no-cache;
            # the freshly computed vector is still returned.
            self._drop_vector_cache(f"put failed for {rel_path}: {exc}")
        return vec

    def _embed_batch_with_cache(
        self, rel_paths: list[str], search_texts: list[str]
    ) -> list[list[float]]:
        """Batch embed, hitting the cache for known fingerprints first.

        Fix A2 semantics:
        - An embedder error is infrastructure failure → propagate wrapped
          ``RuntimeError`` with chunk context. Never return partial vectors.
        - A cache-write error is degradation → WARNING + continue without
          cache. Every result slot is still filled with a real vector.
        """
        if self._vector_cache is None:
            try:
                return list(self._embedder.embed_batch(list(search_texts)))
            except Exception as exc:
                raise RuntimeError(
                    f"embedding failed for {len(search_texts)} chunks "
                    f"(first: {rel_paths[0] if rel_paths else '?'})"
                ) from exc

        model_name = getattr(self._embedder, "model_name", DEFAULT_EMBEDDING_MODEL)
        fingerprints = [cache_fingerprint(model_name, text) for text in search_texts]

        # Resolve cache hits.
        results: list[list[float] | None] = [None] * len(rel_paths)
        miss_indices: list[int] = []
        for i, fp in enumerate(fingerprints):
            cached = self._vector_cache.get(fp)
            if cached is not None:
                results[i] = cached.tolist()
            else:
                miss_indices.append(i)

        # Batch embed the misses.
        if miss_indices:
            miss_texts = [search_texts[i] for i in miss_indices]
            first_miss_rel = rel_paths[miss_indices[0]]
            try:
                miss_vectors = self._embedder.embed_batch(miss_texts)
            except Exception as exc:
                raise RuntimeError(
                    f"embedding failed for chunk {first_miss_rel}"
                    f" (+{len(miss_texts) - 1} more)"
                ) from exc
            if len(miss_vectors) != len(miss_texts):
                raise RuntimeError(
                    f"embedder returned {len(miss_vectors)} vectors for "
                    f"{len(miss_texts)} chunks (first missing: {first_miss_rel})"
                )

            # Transactional cache write (all-or-nothing via batch_put).
            try:
                import numpy as _np
                items = [
                    (fingerprints[idx], rel_paths[idx],
                     _np.asarray(vec, dtype=_np.float32))
                    for idx, vec in zip(miss_indices, miss_vectors)
                ]
                self._vector_cache.batch_put(items)
                for idx, vec in zip(miss_indices, miss_vectors):
                    results[idx] = vec
            except Exception as exc:
                # Degrade loudly: keep going without cache, but every slot
                # still gets its freshly computed vector below.
                self._drop_vector_cache(f"batch_put failed at {first_miss_rel}: {exc}")
                for idx, vec in zip(miss_indices, miss_vectors):
                    results[idx] = list(vec)

        # Fail-fast guard: an incomplete result can never leave this method.
        if any(v is None for v in results):
            missing = [rel_paths[i] for i, v in enumerate(results) if v is None]
            raise RuntimeError(f"internal error: vectors missing for {missing[:3]}")

        return [v for v in results if v is not None]

    # ------------------------------------------------------------------
    # Chunking helpers (Fase 07)
    # ------------------------------------------------------------------

    def _chunks_for_doc(self, rel_path: str, doc: SemanticDocument) -> list[Chunk]:
        """Split a SemanticDocument into chunks honouring the routing table.

        When the doc_type cannot be inferred from the path (legacy notes,
        notes in unexpected folders) we fall back to a single chunk using
        the doc title as section title.
        """
        doc_type = self._resolve_doc_type(rel_path)
        if doc_type is None:
            # Fallback: single chunk, doc_type=GLOSSARY (least specific signal).
            return [
                Chunk(
                    parent_path=rel_path,
                    chunk_id=rel_path,
                    section_title=doc.title or "(untitled)",
                    section_position=0,
                    text=doc.content,
                    doc_type=DocType.GLOSSARY,
                    tags=tuple(doc.tags),
                )
            ]

        route = self._resolve_route(doc_type)
        if route is None or not route.chunking_enabled:
            return [
                Chunk(
                    parent_path=rel_path,
                    chunk_id=rel_path,
                    section_title=doc.title or "(untitled)",
                    section_position=0,
                    text=doc.content,
                    doc_type=doc_type,
                    tags=tuple(doc.tags),
                )
            ]

        return chunk_document(
            title=doc.title,
            content=doc.content,
            doc_type=doc_type,
            tags=doc.tags,
            parent_path=rel_path,
            min_words=route.chunking_min_words,
            boundary=route.chunking_boundary,
        )

    def _purge_chunks_for_parent(self, rel_path: str) -> None:
        """Remove every cached chunk that belonged to ``rel_path``.

        Called before re-indexing a file so stale chunks don't pollute search.
        """
        stale = [
            cid for cid, ch in self._chunks.items() if ch.parent_path == rel_path
        ]
        for cid in stale:
            self._chunks.pop(cid, None)
            self._embeddings.pop(cid, None)
        self._invalidate_native_caches()

    @staticmethod
    def _resolve_doc_type(rel_path: str) -> DocType | None:
        """Best-effort DocType inference from ``rel_path``.

        Uses the same path heuristics as ``inventory.classify_path`` to keep
        behaviour consistent between indexing and migration.
        """
        slug = classify_path(Path(rel_path), Path(""))
        if slug is None:
            # ``classify_path`` requires a vault root for absolute paths;
            # we pass an empty root and inspect via parts directly.
            parts = Path(rel_path).parts
            if not parts:
                return None
        else:
            try:
                return DocType(slug)
            except ValueError:
                return None
        # Fallback: classify by the first directory segment.
        parts = Path(rel_path).parts
        if len(parts) >= 2:
            first = parts[0]
            mapping = {
                "sessions": DocType.SESSION,
                "handoffs": DocType.HANDOFF,
                "specs": DocType.SPEC,
                "decisions": (
                    DocType.ADR
                    if Path(rel_path).stem.upper().startswith("ADR-")
                    else DocType.DECISION
                ),
                "incidents": DocType.INCIDENT,
                "postmortems": DocType.POSTMORTEM,
                "runbooks": DocType.RUNBOOK,
                "architecture": DocType.ARCHITECTURE,
                "changelog": DocType.CHANGELOG,
                "hu": DocType.HU,
                "glossary": DocType.GLOSSARY,
            }
            return mapping.get(first)
        return None

    @staticmethod
    def _resolve_route(doc_type: DocType) -> Any | None:
        """Look up the routing spec for ``doc_type``; return None on miss."""
        try:
            # Lazy import to keep the semantic layer independent of the
            # documentation routing module at import time.
            from cortex.documentation.routing import resolve_route
            return resolve_route(doc_type)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save_index_meta(self) -> None:
        """Save lightweight index metadata (BM25 stats) to disk."""
        meta: dict[str, Any] = {
            "doc_lengths": self._doc_lengths,
            "avgdl": self._avgdl,
            "idf": self._idf,
        }
        meta_path = self.vault_path / _INDEX_FILE
        try:
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
        except OSError:
            logger.debug("Could not persist index meta to %s", meta_path)

    # Decision (Fix A5): ``_load_index_meta`` was REMOVED, not wired.
    # Rationale: ``sync()`` recomputes BM25 stats from already-parsed docs on
    # every cold start, and embeddings are never restored from disk either,
    # so a meta-only restore would produce an inconsistent half-index while
    # saving nothing measurable. The saved meta stays useful as a diagnostic
    # artifact and for future Fase C/E consumers; it is written through
    # :meth:`_persist_after_write` after every vault write.

    # ------------------------------------------------------------------
    # Read / search (public)
    # ------------------------------------------------------------------

    def get(self, relative_path: str) -> SemanticDocument | None:
        """Retrieve a document by its relative path inside the vault."""
        self._ensure_loaded()
        return self._index.get(relative_path)

    def count(self) -> int:
        self._ensure_loaded()
        return len(self._index)

    def iter_documents(self) -> Iterable[tuple[str, SemanticDocument]]:
        """
        Iterate over indexed semantic documents.

        Returns:
            Tuples of ``(relative_path, SemanticDocument)``.

        Notes:
            - This is a read-only public view for downstream consumers such as
              ``cortex.webgraph``.
            - Callers receive model copies so they cannot mutate the in-memory
              index held by ``VaultReader``.
        """
        self._ensure_loaded()
        for rel_path, doc in self._index.items():
            yield rel_path, doc.model_copy(deep=True)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def index_file(self, relative_path: str) -> bool:
        """
        Vectorize and index a single file from the vault.
        Avoids a full vault scan (sync).
        """
        path = resolve_safe(self.vault_path, relative_path)
        if not path.exists():
            logger.error("Cannot index non-existent file: %s", path)
            return False
        
        try:
            doc = self._parser.parse(path)
            self._index[relative_path] = doc

            # Drop any prior in-memory chunks for this parent so re-indexing
            # is clean.
            self._purge_chunks_for_parent(relative_path)

            # Chunk the doc (route table decides whether to split).
            chunks = self._chunks_for_doc(relative_path, doc)

            # Item #4 — granular cache invalidation. Drop cached chunk
            # entries that no longer exist in the re-parsed document, so the
            # cache reflects the new structure without re-embedding chunks
            # whose body fingerprint is unchanged.
            if self._vector_cache is not None:
                cached_chunks = self._vector_cache.get_chunk_fingerprints(relative_path)
                if cached_chunks:
                    current_ids = {c.chunk_id for c in chunks}
                    stale_ids = [
                        cid for cid in cached_chunks if cid not in current_ids
                    ]
                    if stale_ids:
                        self._vector_cache.invalidate_chunks(stale_ids)

            for ch in chunks:
                self._chunks[ch.chunk_id] = ch
            if chunks:
                chunk_ids = [c.chunk_id for c in chunks]
                texts = [c.embedding_text for c in chunks]
                vectors = self._embed_batch_with_cache(chunk_ids, texts)
                for cid, vec in zip(chunk_ids, vectors, strict=False):
                    self._embeddings[cid] = vec
            self._invalidate_native_caches()

            # Update BM25 metadata for this file
            search_text = f"{doc.title} {doc.content}"
            word_count = len(search_text.split())
            self._doc_lengths[relative_path] = word_count
            
            # Recalculate average doc length
            if self._doc_lengths:
                self._avgdl = sum(self._doc_lengths.values()) / len(self._doc_lengths)
            
            # Update IDF stats
            self._compute_idf()
            
            # Save lightweight meta (without full sync)
            self._persist_after_write()
            return True
        except Exception as e:
            logger.error("Failed to index file %s: %s", relative_path, e)
            return False

    def create_note(
        self,
        title: str,
        content: str,
        *,
        subfolder: str = "",
        tags: list[str] | None = None,
    ) -> Path:
        """
        Create a new markdown note in the vault.

        Args:
            title:      Note title (used as filename).
            content:    Markdown body.
            subfolder:  Optional subdirectory inside the vault.
            tags:       Front-matter tags.

        Returns:
            Path to the newly created file.
        """
        if subfolder:
            folder = resolve_safe(self.vault_path, subfolder)
        else:
            folder = self.vault_path
        folder.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "_")
        path = validate_under_root(folder / f"{slug}.md", self.vault_path)

        # Safe YAML frontmatter using yaml.dump
        frontmatter_dict: dict[str, Any] = {"title": title, "tags": tags or []}
        frontmatter = "---\n" + yaml_dump_safe(frontmatter_dict) + "---\n\n"
        path.write_text(frontmatter + content, encoding="utf-8")

        # Refresh index entry (chunk-aware).
        rel = str(path.relative_to(self.vault_path))
        doc = self._parser.parse(path)
        self._index[rel] = doc
        self._purge_chunks_for_parent(rel)
        chunks = self._chunks_for_doc(rel, doc)
        for ch in chunks:
            self._chunks[ch.chunk_id] = ch
        if chunks:
            chunk_ids = [c.chunk_id for c in chunks]
            texts = [c.embedding_text for c in chunks]
            vectors = self._embed_batch_with_cache(chunk_ids, texts)
            for cid, vec in zip(chunk_ids, vectors, strict=False):
                self._embeddings[cid] = vec
        self._invalidate_native_caches()
        search_text = f"{title} {content}"
        word_count = len(search_text.split())
        self._doc_lengths[rel] = word_count
        # Re-compute avgdl
        docs = list(self._doc_lengths.values())
        self._avgdl = sum(docs) / len(docs) if docs else 1.0
        # Update IDF
        self._compute_idf()
        self._persist_after_write()

        logger.info("Note created: %s", path)
        return path

    @staticmethod
    def _merge_frontmatter(existing_text: str, new_content: str) -> str:
        """Merge ``new_content`` into ``existing_text`` keeping frontmatter (A5).

        The existing YAML frontmatter block (title, tags, custom keys) is
        preserved verbatim; only the body is replaced. If ``new_content``
        already carries its own frontmatter it is treated as a complete
        document and written as-is.
        """
        if new_content.lstrip("﻿").startswith("---"):
            return new_content
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", existing_text, re.DOTALL)
        if not match:
            return new_content
        return f"---\n{match.group(1)}\n---\n\n{new_content}"

    def _persist_after_write(self) -> None:
        """Persist index metadata after ANY vault write (Fix A5).

        Single funnel so a new write path cannot forget to sync BM25 meta.
        """
        self._save_index_meta()

    def update_note(self, relative_path: str, new_content: str) -> bool:
        """Overwrite the body of an existing note, preserving frontmatter.

        Fix A5: previously this wrote ``new_content`` raw over the whole
        file, destroying the original title/tags frontmatter.
        Returns True on success.
        """
        path = resolve_safe(self.vault_path, relative_path)
        if not path.exists():
            return False
        existing = path.read_text(encoding="utf-8")
        path.write_text(
            self._merge_frontmatter(existing, new_content), encoding="utf-8"
        )
        self._index[relative_path] = self._parser.parse(path)

        # Re-embed (chunk-aware + cache-aware).
        doc = self._index[relative_path]
        self._purge_chunks_for_parent(relative_path)
        chunks = self._chunks_for_doc(relative_path, doc)
        for ch in chunks:
            self._chunks[ch.chunk_id] = ch
        if chunks:
            chunk_ids = [c.chunk_id for c in chunks]
            texts = [c.embedding_text for c in chunks]
            vectors = self._embed_batch_with_cache(chunk_ids, texts)
            for cid, vec in zip(chunk_ids, vectors, strict=False):
                self._embeddings[cid] = vec
        self._invalidate_native_caches()
        search_text = f"{doc.title} {doc.content}"
        self._doc_lengths[relative_path] = len(search_text.split())
        docs = list(self._doc_lengths.values())
        self._avgdl = sum(docs) / len(docs) if docs else 1.0
        self._compute_idf()
        self._persist_after_write()

        return True


