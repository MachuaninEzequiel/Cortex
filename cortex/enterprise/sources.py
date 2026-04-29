from __future__ import annotations

from dataclasses import dataclass

from cortex.episodic.memory_store import EpisodicMemoryStore
from cortex.models import EpisodicHit, SemanticDocument
from cortex.semantic.vault_reader import VaultReader


@dataclass(frozen=True)
class VaultSource:
    path: str
    scope: str
    project_id: str


@dataclass(frozen=True)
class EpisodicSource:
    persist_dir: str
    scope: str
    project_id: str
    collection_name: str


class MultiVaultReader:
    def __init__(self, *, sources: list[VaultSource], embedding_model: str, embedding_backend: str) -> None:
        self.sources = sources
        self._readers: list[tuple[VaultSource, VaultReader]] = [
            (
                source,
                VaultReader(
                    vault_path=source.path,
                    embedding_model=embedding_model,
                    embedding_backend=embedding_backend,
                ),
            )
            for source in sources
        ]

    def search(self, query: str, top_k: int, use_embeddings: bool = True) -> list[SemanticDocument]:
        hits: list[SemanticDocument] = []
        for source, reader in self._readers:
            source_hits = reader.search(query, top_k=top_k, use_embeddings=use_embeddings)
            for doc in source_hits:
                hits.append(
                    doc.model_copy(
                        update={
                            "origin_scope": source.scope,
                            "origin_project_id": source.project_id,
                            "origin_vault": source.path,
                            "origin_persist_dir": "",
                        }
                    )
                )
        return hits


class MultiEpisodicReader:
    def __init__(self, *, sources: list[EpisodicSource], embedding_model: str, embedding_backend: str) -> None:
        self.sources = sources
        self._stores: list[tuple[EpisodicSource, EpisodicMemoryStore]] = [
            (
                source,
                EpisodicMemoryStore(
                    persist_dir=source.persist_dir,
                    embedding_model=embedding_model,
                    embedding_backend=embedding_backend,
                    collection_name=source.collection_name,
                ),
            )
            for source in sources
        ]

    def search(self, query: str, top_k: int, use_embeddings: bool = True) -> list[EpisodicHit]:
        hits: list[EpisodicHit] = []
        for source, store in self._stores:
            source_hits = store.search(query, top_k=top_k, use_embeddings=use_embeddings)
            for hit in source_hits:
                metadata = dict(hit.entry.metadata)
                metadata.update(
                    {
                        "scope": source.scope,
                        "project_id": source.project_id,
                        "origin_vault": "",
                        "origin_persist_dir": source.persist_dir,
                    }
                )
                entry = hit.entry.model_copy(update={"metadata": metadata})
                hits.append(
                    hit.model_copy(
                        update={
                            "entry": entry,
                            "origin_scope": source.scope,
                            "origin_project_id": source.project_id,
                            "origin_vault": "",
                            "origin_persist_dir": source.persist_dir,
                        }
                    )
                )
        return hits
