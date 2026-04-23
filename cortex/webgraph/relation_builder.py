from __future__ import annotations

import math
import re
from collections import defaultdict

from cortex.webgraph.config import WebGraphConfig
from cortex.webgraph.contracts import EpisodicRecord, SemanticRecord, WebGraphEdge

_GENERIC_TAGS = {"release-2", "general", "memory", "setup"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())}


def _identifier_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
        if token.lower() not in {"session", "specification", "changes", "files", "requirements"}
    }


def _cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class RelationBuilder:
    """Builds explainable relationships for the hybrid webgraph."""

    def __init__(self, config: WebGraphConfig) -> None:
        self.config = config

    def build_edges(
        self,
        semantic_records: list[SemanticRecord],
        episodic_records: list[EpisodicRecord],
    ) -> list[WebGraphEdge]:
        edges: dict[tuple[str, str, str], WebGraphEdge] = {}
        self._add_semantic_wikilinks(edges, semantic_records)
        self._add_semantic_spec_links(edges, semantic_records)
        self._add_cross_source_edges(edges, semantic_records, episodic_records)
        if self.config.enable_semantic_neighbors:
            self._add_semantic_neighbors(edges, semantic_records, episodic_records)
        return list(edges.values())

    def _add_edge(
        self,
        edges: dict[tuple[str, str, str], WebGraphEdge],
        *,
        source: str,
        target: str,
        edge_type: str,
        evidence: list[str],
        weight: float = 1.0,
    ) -> None:
        if source == target:
            return
        key = (edge_type, source, target) if edge_type == "wikilink" else (
            edge_type,
            min(source, target),
            max(source, target),
        )
        existing = edges.get(key)
        if existing is None:
            edges[key] = WebGraphEdge(
                id=f"{edge_type}:{source}:{target}",
                source=source,
                target=target,
                edge_type=edge_type,
                weight=weight,
                evidence=list(dict.fromkeys(evidence)),
            )
            return
        merged = list(dict.fromkeys(existing.evidence + evidence))
        edges[key] = existing.model_copy(update={"evidence": merged, "weight": max(existing.weight, weight)})

    def _add_semantic_wikilinks(
        self,
        edges: dict[tuple[str, str, str], WebGraphEdge],
        semantic_records: list[SemanticRecord],
    ) -> None:
        alias_index: dict[str, str] = {}
        for record in semantic_records:
            rel_path = record.rel_path
            stem = rel_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            alias_index[rel_path.lower()] = record.node_id
            alias_index[stem.lower()] = record.node_id
            alias_index[_slug(record.title)] = record.node_id

        for record in semantic_records:
            for link in record.links:
                target = link.split("|", 1)[0].split("#", 1)[0].strip().lower()
                target_id = alias_index.get(target) or alias_index.get(_slug(target))
                if target_id:
                    self._add_edge(
                        edges,
                        source=record.node_id,
                        target=target_id,
                        edge_type="wikilink",
                        evidence=[link],
                    )

    def _add_semantic_spec_links(
        self,
        edges: dict[tuple[str, str, str], WebGraphEdge],
        semantic_records: list[SemanticRecord],
    ) -> None:
        specs = [record for record in semantic_records if record.node_type == "semantic_spec"]
        sessions = [record for record in semantic_records if record.node_type == "semantic_session"]
        for session in sessions:
            session_tokens = _tokenize(session.content)
            for spec in specs:
                spec_tokens = _tokenize(spec.title) | _tokenize(spec.summary)
                overlap = session_tokens & spec_tokens
                if len(overlap) >= 3:
                    self._add_edge(
                        edges,
                        source=session.node_id,
                        target=spec.node_id,
                        edge_type="same_spec_reference",
                        evidence=[f"shared tokens: {', '.join(sorted(list(overlap))[:4])}"],
                        weight=1.2,
                    )

    def _add_cross_source_edges(
        self,
        edges: dict[tuple[str, str, str], WebGraphEdge],
        semantic_records: list[SemanticRecord],
        episodic_records: list[EpisodicRecord],
    ) -> None:
        semantic_by_path = {record.rel_path.lower(): record for record in semantic_records}
        ignored_tags = {tag.lower() for tag in self.config.ignored_tags} | _GENERIC_TAGS

        for episodic in episodic_records:
            episodic_tags = {tag.lower() for tag in episodic.tags if tag.lower() not in ignored_tags}
            episodic_entities = self._entities_from_metadata(episodic)
            episodic_tokens = _tokenize(episodic.content)

            for file_ref in episodic.files:
                semantic = semantic_by_path.get(file_ref.lower())
                if semantic:
                    self._add_edge(
                        edges,
                        source=episodic.node_id,
                        target=semantic.node_id,
                        edge_type="same_file_reference",
                        evidence=[file_ref],
                        weight=1.3,
                    )

            for semantic in semantic_records:
                semantic_tags = {tag.lower() for tag in semantic.tags if tag.lower() not in ignored_tags}
                shared_tags = sorted(episodic_tags & semantic_tags)
                if shared_tags:
                    self._add_edge(
                        edges,
                        source=episodic.node_id,
                        target=semantic.node_id,
                        edge_type="shared_tag",
                        evidence=shared_tags[:3],
                    )

                semantic_entities = _identifier_tokens(f"{semantic.title} {semantic.content}")
                shared_entities = sorted(episodic_entities & semantic_entities)
                if shared_entities:
                    self._add_edge(
                        edges,
                        source=episodic.node_id,
                        target=semantic.node_id,
                        edge_type="shared_entity",
                        evidence=shared_entities[:4],
                        weight=1.1,
                    )

                spec_tokens = _tokenize(semantic.title) | _tokenize(semantic.summary)
                overlap = episodic_tokens & spec_tokens
                if semantic.node_type == "semantic_spec" and len(overlap) >= 3:
                    self._add_edge(
                        edges,
                        source=episodic.node_id,
                        target=semantic.node_id,
                        edge_type="same_spec_reference",
                        evidence=[f"shared tokens: {', '.join(sorted(list(overlap))[:4])}"],
                        weight=1.2,
                    )

    def _add_semantic_neighbors(
        self,
        edges: dict[tuple[str, str, str], WebGraphEdge],
        semantic_records: list[SemanticRecord],
        episodic_records: list[EpisodicRecord],
    ) -> None:
        hybrid_records = semantic_records + episodic_records
        if len(hybrid_records) > self.config.semantic_neighbor_max_nodes:
            return

        neighbors_by_node: dict[str, list[tuple[float, str]]] = defaultdict(list)
        for idx, left in enumerate(hybrid_records):
            for right in hybrid_records[idx + 1 :]:
                score = _cosine_similarity(left.embedding, right.embedding)
                if score < self.config.semantic_neighbor_threshold:
                    continue
                neighbors_by_node[left.node_id].append((score, right.node_id))
                neighbors_by_node[right.node_id].append((score, left.node_id))

        allowed_pairs: set[tuple[str, str]] = set()
        for node_id, neighbors in neighbors_by_node.items():
            ranked = sorted(neighbors, reverse=True)[: self.config.semantic_neighbor_max_edges_per_node]
            for _, other_id in ranked:
                allowed_pairs.add((min(node_id, other_id), max(node_id, other_id)))

        for left in hybrid_records:
            for right in hybrid_records:
                if left.node_id >= right.node_id:
                    continue
                pair = (left.node_id, right.node_id)
                if pair not in allowed_pairs:
                    continue
                score = _cosine_similarity(left.embedding, right.embedding)
                if score < self.config.semantic_neighbor_threshold:
                    continue
                self._add_edge(
                    edges,
                    source=left.node_id,
                    target=right.node_id,
                    edge_type="semantic_neighbor",
                    evidence=[f"cosine={score:.3f}"],
                    weight=score,
                )

    @staticmethod
    def _entities_from_metadata(record: EpisodicRecord) -> set[str]:
        entities = record.metadata.get("entities", {})
        if not isinstance(entities, dict):
            return set()
        found: set[str] = set()
        for values in entities.values():
            if not isinstance(values, list):
                continue
            for value in values:
                text = str(value).strip().lower()
                if text:
                    found.add(text)
        return found

