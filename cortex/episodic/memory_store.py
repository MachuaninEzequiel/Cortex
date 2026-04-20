"""
cortex.episodic.memory_store
----------------------------
ChromaDB-backed episodic memory store with semantic search.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings

from cortex.episodic.embedder import Embedder
from cortex.models import EpisodicHit, MemoryEntry

logger = logging.getLogger(__name__)


class EpisodicMemoryStore:
    """
    Stores and retrieves episodic memories using ChromaDB.

    Each memory is embedded and stored with its metadata so it can be
    found later via semantic similarity search.

    Args:
        persist_dir:       Directory for ChromaDB persistent storage.
        embedding_model:   Embedding model name.
        embedding_backend: ``"local"`` or ``"openai"``.
        collection_name:   ChromaDB collection identifier.
    """

    def __init__(
        self,
        persist_dir: str = ".memory/chroma",
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_backend: str = "onnx",
        collection_name: str = "cortex_episodic",
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.embedder = Embedder(
            model_name=embedding_model,
            backend=embedding_backend,  # type: ignore[arg-type]
        )

        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._cache_token = 0
        self._entries_cache: list[MemoryEntry] | None = None
        self._entries_cache_token = -1
        self._entity_index_cache: dict[str, dict[str, list[MemoryEntry]]] | None = None
        self._entity_index_cache_token = -1
        logger.info(
            "EpisodicMemoryStore initialized — collection '%s' has %d entries",
            collection_name,
            self._collection.count(),
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        content: str,
        memory_type: str = "general",
        tags: list[str] | None = None,
        files: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Embed and persist a new memory. Returns the stored entry."""
        # Extract entities from content
        entities = self._extract_entities(content)
        
        # Merge entities with extra_metadata
        metadata = dict(extra_metadata or {})
        if entities:
            metadata["entities"] = entities
        
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            files=files or [],
            metadata=metadata,
        )
        embedding = self.embedder.embed(content)
        self._collection.add(
            ids=[entry.id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[self._serialize_metadata(entry)],
        )
        self._invalidate_caches()
        logger.debug("Stored memory %s [%s]", entry.id, memory_type)
        return entry

    def _extract_entities(self, content: str) -> dict[str, list[str]]:
        """Extract structured entities (functions, classes, etc.) from content."""
        import re
        
        ENTITY_PATTERNS = {
            "function": [
                re.compile(r"(?:def|function|async\s+function)\s+(\w+)\s*\("),
                re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(.*\)\s*=>"),  # Arrow functions
                re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\*?\s*\([^)]*\)"),  # Function expressions
            ],
            "class": [
                re.compile(r"class\s+(\w+)"),
                re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*class\s*{"),  # Class expressions
            ],
            "endpoint": [
                re.compile(
                    r"(?:@app\.(?:route|get|post|put|delete|patch|head|options))\(\s*[\"']([^\"']+)[\"']"
                ),
                re.compile(
                    r"router\.(?:get|post|put|delete|patch|head|options)\(\s*[\"']([^\"']+)[\"']"
                ),
                re.compile(
                    r"(?:app\.)?(?:get|post|put|delete|patch|head|options)\(\s*[\"']([^\"']+)[\"']"
                ),
            ],
            "error": [
                re.compile(r"(?:Error|Exception|TypeError|ValueError|KeyError):\s*(.+)"),
                re.compile(r"throw\s+new\s+(\w+Error)\s*\("),
                re.compile(r"catch\s*\(\s*\w+\s+(\w+Error)"),
            ],
            "config_key": [
                re.compile(r"(?:process\.env|os\.environ)\[['\"](\w+)['\"]\]"),
                re.compile(r"config\.get\(\s*['\"](\w+)['\"]\s*\)"),
                re.compile(r"settings\.\s*(\w+)"),
            ],
            "dependency": [
                re.compile(r"(?:import\s+.*\s+from\s+|require\s*\()\s*[\"']([^\"']+)[\"']"),
                re.compile(r"from\s+([\w./-]+)\s+import"),
                re.compile(r"import\s+([\w./-]+)"),
            ],
            "variable": [
                re.compile(r"(?:const|let|var)\s+(\w+)\s*="),
            ],
            "constant": [
                re.compile(r"(?:const\s+(\w+)\s*=)|(?:#\s*define\s+(\w+))"),
            ],
        }
        
        entities = {}
        for entity_type, patterns in ENTITY_PATTERNS.items():
            matches = []
            for pattern in patterns:
                matches.extend(pattern.findall(content))
            if matches:
                # Clean up matches and remove duplicates
                cleaned_matches = []
                for match in matches:
                    if isinstance(match, tuple):
                        # Take the first non-empty group
                        cleaned_match = next((m for m in match if m), "")
                    else:
                        cleaned_match = match
                    if cleaned_match and cleaned_match not in cleaned_matches:
                        cleaned_matches.append(cleaned_match)
                entities[entity_type] = cleaned_matches[:15]  # Increased cap to 15
        return entities

    def search(self, query: str, top_k: int = 5, use_embeddings: bool = True) -> list[EpisodicHit]:
        """
        Return the top-k most relevant memories for a query.
        
        Args:
            query: The search string.
            top_k: Max results.
            use_embeddings: If False, performs a simple keyword search via ChromaDB 
                            'where_document' without using the embedding model.
        """
        if self._collection.count() == 0:
            return []

        if not use_embeddings:
            # Bypass: Simple keyword search via ChromaDB 'where_document'
            # This does NOT trigger the embedder or ONNX loading.
            results = self._collection.query(
                where_document={"$contains": query},
                n_results=min(top_k, self._collection.count()),
                include=["documents", "metadatas"],
            )
            
            hits: list[EpisodicHit] = []
            if results["documents"]:
                for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                    entry = self._deserialize_metadata(doc, meta)
                    hits.append(EpisodicHit(entry=entry, score=1.0)) # Flat score for keyword match
            return hits

        # Vector Search (Normal flow - triggers ONNX load if first call)
        embedding = self.embedder.embed(query)
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[EpisodicHit] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            entry = self._deserialize_metadata(doc, meta)
            # Convert cosine distance -> similarity score [0, 1]
            score = max(0.0, 1.0 - dist)
            hits.append(EpisodicHit(entry=entry, score=score))

        return hits

    def search_by_entity(self, entity_type: str, entity_value: str, top_k: int = 5) -> list[EpisodicHit]:
        """Search for memories that mention a specific entity (function, class, etc.)."""
        if self._collection.count() == 0:
            return []

        hits = self._search_by_entity_where(entity_type, entity_value)
        if not hits:
            hits = self._search_by_entity_legacy(entity_type, entity_value)

        hits.sort(key=lambda x: x.score, reverse=True)
        return hits[:top_k]

    def delete(self, memory_id: str) -> bool:
        """Remove a memory by ID. Returns True only if the ID existed."""
        # ChromaDB silently succeeds even for non-existent IDs, so we must
        # check existence first to return an accurate result.
        try:
            existing = self._collection.get(ids=[memory_id], include=[])
            if not existing["ids"]:
                return False
            self._collection.delete(ids=[memory_id])
            self._invalidate_caches()
            return True
        except Exception:
            return False

    def count(self) -> int:
        return self._collection.count()

    @property
    def cache_token(self) -> int:
        """Mutation token for downstream caches derived from this store."""
        return self._cache_token

    def list_entries(self) -> list[MemoryEntry]:
        """Return every stored entry, using an in-process cache when possible."""
        if self._entries_cache is not None and self._entries_cache_token == self._cache_token:
            return list(self._entries_cache)

        all_results = self._collection.get(include=["documents", "metadatas"])
        documents = all_results.get("documents") or []
        metadatas = all_results.get("metadatas") or []
        entries = [
            self._deserialize_metadata(doc, meta)
            for doc, meta in zip(documents, metadatas)
        ]
        self._entries_cache = entries
        self._entries_cache_token = self._cache_token
        return list(entries)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_metadata(entry: MemoryEntry) -> dict:
        """Flatten MemoryEntry fields into ChromaDB-compatible metadata."""
        metadata = {
            "id": entry.id,
            "memory_type": entry.memory_type,
            "tags": json.dumps(entry.tags),
            "files": json.dumps(entry.files),
            "timestamp": entry.timestamp.isoformat(),
            "metadata_json": json.dumps(entry.metadata, sort_keys=True),
        }

        entities = entry.metadata.get("entities", {})
        if isinstance(entities, dict):
            for entity_type, values in entities.items():
                if not isinstance(values, list):
                    continue
                for value in values:
                    metadata[EpisodicMemoryStore._entity_filter_key(entity_type, str(value))] = True

        return metadata

    @staticmethod
    def _deserialize_metadata(document: str, meta: dict) -> MemoryEntry:
        """Reconstruct a MemoryEntry from stored metadata.

        Restores the original timestamp so retrieved memories keep
        their creation time instead of getting the current time.
        """
        ts_str = meta.get("timestamp")
        if ts_str:
            try:
                timestamp = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        metadata: dict[str, Any] = {}
        metadata_json = meta.get("metadata_json")
        if metadata_json:
            try:
                parsed = json.loads(metadata_json)
                if isinstance(parsed, dict):
                    metadata = parsed
            except (TypeError, ValueError):
                metadata = {}

        if not metadata:
            metadata = EpisodicMemoryStore._extract_metadata_from_flat_fields(meta)

        return MemoryEntry(
            id=meta["id"],
            content=document,
            memory_type=meta.get("memory_type", "general"),
            tags=json.loads(meta.get("tags", "[]")),
            files=json.loads(meta.get("files", "[]")),
            timestamp=timestamp,
            metadata=metadata,
        )

    def _invalidate_caches(self) -> None:
        self._cache_token += 1
        self._entries_cache = None
        self._entries_cache_token = -1
        self._entity_index_cache = None
        self._entity_index_cache_token = -1

    def _search_by_entity_where(self, entity_type: str, entity_value: str) -> list[EpisodicHit]:
        entity_key = self._entity_filter_key(entity_type, entity_value)
        try:
            results = self._collection.get(
                where={entity_key: True},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.debug("Entity filter lookup failed for %s=%s: %s", entity_type, entity_value, exc)
            return []

        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []
        return [
            EpisodicHit(
                entry=entry,
                score=self._entity_match_score(entry, entity_type, entity_value),
            )
            for entry in (
                self._deserialize_metadata(doc, meta)
                for doc, meta in zip(documents, metadatas)
            )
        ]

    def _search_by_entity_legacy(self, entity_type: str, entity_value: str) -> list[EpisodicHit]:
        normalized_type = entity_type.strip().lower()
        normalized_value = entity_value.strip().lower()
        entity_index = self._entity_index()
        matches = entity_index.get(normalized_type, {}).get(normalized_value, [])
        return [
            EpisodicHit(
                entry=entry,
                score=self._entity_match_score(entry, entity_type, entity_value),
            )
            for entry in matches
        ]

    def _entity_index(self) -> dict[str, dict[str, list[MemoryEntry]]]:
        if self._entity_index_cache is not None and self._entity_index_cache_token == self._cache_token:
            return self._entity_index_cache

        entity_index: dict[str, dict[str, list[MemoryEntry]]] = {}
        for entry in self.list_entries():
            entities = entry.metadata.get("entities", {})
            if not isinstance(entities, dict):
                continue
            for entity_type, values in entities.items():
                if not isinstance(values, list):
                    continue
                normalized_type = str(entity_type).strip().lower()
                bucket = entity_index.setdefault(normalized_type, {})
                for value in values:
                    normalized_value = str(value).strip().lower()
                    if not normalized_value:
                        continue
                    bucket.setdefault(normalized_value, []).append(entry)

        self._entity_index_cache = entity_index
        self._entity_index_cache_token = self._cache_token
        return entity_index

    @staticmethod
    def _entity_match_score(entry: MemoryEntry, entity_type: str, entity_value: str) -> float:
        entities = entry.metadata.get("entities", {})
        values = entities.get(entity_type, []) if isinstance(entities, dict) else []
        if not isinstance(values, list):
            values = []

        normalized_target = entity_value.strip().lower()
        entity_count = sum(
            1 for value in values
            if str(value).strip().lower() == normalized_target
        )
        frequency_boost = min(0.3, max(entity_count - 1, 0) * 0.1)

        try:
            now = datetime.now(timezone.utc)
            timestamp = entry.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            hours_old = (now - timestamp).total_seconds() / 3600
            if hours_old < 24:
                recency_boost = 0.2
            elif hours_old > 168:
                recency_boost = -0.1
            else:
                recency_boost = 0.0
        except Exception:
            recency_boost = 0.0

        return min(1.0, 1.0 + frequency_boost + recency_boost)

    @staticmethod
    def _entity_filter_key(entity_type: str, entity_value: str) -> str:
        normalized_type = re.sub(r"[^a-z0-9_]+", "_", entity_type.strip().lower())
        normalized_value = re.sub(r"[^a-z0-9_]+", "_", entity_value.strip().lower())
        return f"entity_{normalized_type}_{normalized_value}".strip("_")

    @staticmethod
    def _extract_metadata_from_flat_fields(meta: dict[str, Any]) -> dict[str, Any]:
        entities: dict[str, list[str]] = {}
        prefix = "entity_"
        for key, value in meta.items():
            if not key.startswith(prefix) or value is not True:
                continue
            raw = key[len(prefix):]
            parts = raw.split("_", 1)
            if len(parts) != 2:
                continue
            entity_type, entity_value = parts
            entities.setdefault(entity_type, []).append(entity_value)

        return {"entities": entities} if entities else {}
