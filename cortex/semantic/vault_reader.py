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
import re
from pathlib import Path
from typing import Any

from cortex.episodic.embedder import Embedder
from cortex.semantic.markdown_parser import MarkdownParser
from cortex.models import SemanticDocument

logger = logging.getLogger(__name__)

# Index file persisted alongside the vault
_INDEX_FILE = ".cortex_index.json"


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
        embedding_backend: str = "local",
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

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def sync(self) -> int:
        """
        (Re-)index all markdown files in the vault — parse, embed, and
        pre-compute BM25 statistics.

        Returns:
            Number of documents indexed.
        """
        self._index.clear()
        self._embeddings.clear()
        self._doc_lengths.clear()
        self._idf.clear()

        if not self.vault_path.exists():
            logger.warning("Vault path does not exist: %s", self.vault_path)
            return 0

        md_files = list(self.vault_path.rglob("*.md"))
        texts: list[tuple[str, str]] = []  # (rel_path, search_text)

        for path in md_files:
            try:
                doc = self._parser.parse(path)
                rel = str(path.relative_to(self.vault_path))
                self._index[rel] = doc
                search_text = f"{doc.title} {doc.content}"
                texts.append((rel, search_text))
                self._doc_lengths[rel] = len(search_text.split())
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", path, exc)

        # Batch embed
        if texts:
            rel_paths, search_texts = zip(*texts)
            vectors = self._embedder.embed_batch(list(search_texts))
            for rel, vec in zip(rel_paths, vectors):
                self._embeddings[rel] = vec

        # Pre-compute BM25 IDF
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

    def search(self, query: str, top_k: int = 5) -> list[SemanticDocument]:
        """
        **Semantic vector search** over the vault.

        Embeds the query and ranks documents by cosine similarity.
        Falls back to BM25 keyword search if no embeddings are available.

        Args:
            query:  Natural-language query string.
            top_k:  Maximum number of results.

        Returns:
            Documents ranked by cosine similarity (or BM25 fallback).
        """
        self._ensure_loaded()

        if not self._embeddings:
            return self._bm25_search(query, top_k)

        query_vec = self._embedder.embed(query)
        scored: list[tuple[float, SemanticDocument]] = []

        for rel_path, doc_vec in self._embeddings.items():
            score = self._cosine_similarity(query_vec, doc_vec)
            if score > 0:
                doc = self._index[rel_path]
                doc_copy = doc.model_copy(update={"score": score})
                scored.append((score, doc_copy))

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

        n_docs = max(len(self._index), 1)
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
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

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

    def _load_index_meta(self) -> bool:
        """Load BM25 index metadata if available. Returns True on success."""
        meta_path = self.vault_path / _INDEX_FILE
        if not meta_path.exists():
            return False
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self._doc_lengths = meta.get("doc_lengths", {})
            self._avgdl = meta.get("avgdl", 1.0)
            self._idf = meta.get("idf", {})
            return True
        except (json.JSONDecodeError, OSError):
            return False

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

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

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
        folder = self.vault_path / subfolder if subfolder else self.vault_path
        folder.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "_")
        path = folder / f"{slug}.md"

        # Safe YAML frontmatter using yaml.dump
        frontmatter_dict: dict[str, Any] = {"title": title, "tags": tags or []}
        frontmatter = "---\n" + yaml_dump_safe(frontmatter_dict) + "---\n\n"
        path.write_text(frontmatter + content, encoding="utf-8")

        # Refresh index entry
        rel = str(path.relative_to(self.vault_path))
        self._index[rel] = self._parser.parse(path)
        search_text = f"{title} {content}"
        self._embeddings[rel] = self._embedder.embed(search_text)
        word_count = len(search_text.split())
        self._doc_lengths[rel] = word_count
        # Re-compute avgdl
        docs = list(self._doc_lengths.values())
        self._avgdl = sum(docs) / len(docs) if docs else 1.0
        # Update IDF
        self._compute_idf()

        logger.info("Note created: %s", path)
        return path

    def update_note(self, relative_path: str, new_content: str) -> bool:
        """Overwrite the body of an existing note. Returns True on success."""
        path = self.vault_path / relative_path
        if not path.exists():
            return False
        path.write_text(new_content, encoding="utf-8")
        self._index[relative_path] = self._parser.parse(path)

        # Re-embed
        doc = self._index[relative_path]
        search_text = f"{doc.title} {doc.content}"
        self._embeddings[relative_path] = self._embedder.embed(search_text)
        self._doc_lengths[relative_path] = len(search_text.split())
        docs = list(self._doc_lengths.values())
        self._avgdl = sum(docs) / len(docs) if docs else 1.0
        self._compute_idf()

        return True


def yaml_dump_safe(data: dict) -> str:
    """Dump a dict to YAML string safely (handles special characters)."""
    import yaml
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)
