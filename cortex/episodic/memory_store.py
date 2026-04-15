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
        metadata = extra_metadata or {}
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

    def search(self, query: str, top_k: int = 5) -> list[EpisodicHit]:
        """Return the top-k most relevant memories for a query."""
        if self._collection.count() == 0:
            return []

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
             
        # Get all memories and filter by entity
        all_results = self._collection.get(
            include=["documents", "metadatas"]
        )
        
        hits: list[EpisodicHit] = []
        for doc, meta in zip(
            all_results["documents"],
            all_results["metadatas"],
        ):
            entry = self._deserialize_metadata(doc, meta)
            # Check if this memory contains the entity
            entities = entry.metadata.get("entities", {})
            if entity_value in entities.get(entity_type, []):
                # Calculate relevance score based on entity match frequency and recency
                base_score = 1.0  # Base score for entity match
                
                # Boost for multiple occurrences of same entity in memory
                entity_count = entities.get(entity_type, []).count(entity_value)
                frequency_boost = min(0.3, (entity_count - 1) * 0.1)  # Max 0.3 boost
                
                # Recency boost (newer memories get slightly higher score)
                from datetime import datetime, timezone
                try:
                    mem_time = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    hours_old = (now - mem_time).total_seconds() / 3600
                    # Memories younger than 24h get boost, older than 7 days get penalty
                    if hours_old < 24:
                        recency_boost = 0.2
                    elif hours_old > 168:  # 7 days
                        recency_boost = -0.1
                    else:
                        recency_boost = 0.0
                except:
                    recency_boost = 0.0
                
                score = min(1.0, base_score + frequency_boost + recency_boost)
                hits.append(EpisodicHit(entry=entry, score=score))
                
        # Sort by score descending and limit
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
            return True
        except Exception:
            return False

    def count(self) -> int:
        return self._collection.count()

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_metadata(entry: MemoryEntry) -> dict:
        """Flatten MemoryEntry fields into ChromaDB-compatible metadata."""
        return {
            "id": entry.id,
            "memory_type": entry.memory_type,
            "tags": json.dumps(entry.tags),
            "files": json.dumps(entry.files),
            "timestamp": entry.timestamp.isoformat(),
        }

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

        return MemoryEntry(
            id=meta["id"],
            content=document,
            memory_type=meta.get("memory_type", "general"),
            tags=json.loads(meta.get("tags", "[]")),
            files=json.loads(meta.get("files", "[]")),
            timestamp=timestamp,
        )
