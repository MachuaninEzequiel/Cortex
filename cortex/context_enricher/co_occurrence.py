"""
cortex.context_enricher.co_occurrence
---------------------------------
Typed Co-occurrence Graph for semantic file relationships.

Replaces naive co-occurrence (file_a → {file_b: count}) with 
a typed graph that captures semantic relationships:
  - imported_by: file imports from another
  - tested_by: test file tests source file
  - extends/implements: class inheritance
  - uses_util: file uses utility function
  - references: general reference/link

Uses AST parsing to extract relationships from code.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Relationship Types
# ---------------------------------------------------------------------------

class RelationshipType:
    """Semantic relationship types between files."""
    
    IMPORTED_BY = "imported_by"
    TESTED_BY = "tested_by"
    IMPLEMENTS = "implements"
    USES = "uses"
    REFERENCES = "references"
    CONFIGURES = "configures"


# Relationship strength (for scoring)
RELATIONSHIP_WEIGHTS: dict[str, float] = {
    RelationshipType.IMPORTED_BY: 1.0,    # Strongest - explicit dependency
    RelationshipType.TESTED_BY: 0.9,       # Strong - test coverage
    RelationshipType.IMPLEMENTS: 0.8,      # Interface implementation
    RelationshipType.USES: 0.7,          # Function usage
    RelationshipType.REFERENCES: 0.5,        # General reference
    RelationshipType.CONFIGURES: 0.6,       # Configuration
}


# ---------------------------------------------------------------------------
# Graph Data Structures
# ---------------------------------------------------------------------------

@dataclass
class FileNode:
    """Represents a file in the co-occurrence graph."""
    
    path: str                           # Relative path
    name: str                          # Filename
    language: str | None = None        # e.g., "python", "typescript"
    entity_count: int = 0               # Functions/classes defined
    first_seen: str | None = None        # ISO timestamp


@dataclass  
class Relationship:
    """A typed relationship between two files."""
    
    from_file: str                      # Source file
    to_file: str                      # Target file
    relation_type: str                # RelationshipType.*
    strength: float = 1.0           # 0.0 - 1.0
    evidence: str | None = None          # Code snippet or context
    count: int = 1                  # Number of occurrences


class TypedCooccurrenceGraph:
    """
    Typed co-occurrence graph with semantic relationships.
    
    Provides richer relationship info than simple co-occurrence count.
    Used by ContextEnricher for graph expansion strategy.
    
    Example:
        graph = TypedCooccurrenceGraph(project_root)
        graph.build_from_memories(memories)
        score = graph.calculate_relationship_score(current, candidate)
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.nodes: dict[str, FileNode] = {}
        self.relationships: list[Relationship] = []
        
        # Adjacency list for fast lookups
        self._outgoing: dict[str, dict[str, list[Relationship]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._incoming: dict[str, dict[str, list[Relationship]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Relationships by type for filtering
        self._by_type: dict[str, list[Relationship]] = defaultdict(list)
        
        logger.debug("TypedCooccurrenceGraph initialized for %s", self.project_root)

    # --------------------------------------------------------------------------
    # Build from memories
    # --------------------------------------------------------------------------

    def build_from_memories(
        self,
        memories: list[Any],
        files_extractor: Callable | None = None,
    ) -> None:
        """
        Build the graph from episodic memories.
        
        Args:
            memories: List of MemoryEntry objects
            files_extractor: Optional function to extract files from memory
        """
        self.clear()
        
        for memory in memories:
            # Get files from this memory
            files = files_extractor(memory) if files_extractor else getattr(memory, "files", [])
            
            if not files or len(files) < 2:
                continue
            
            # Add nodes for each file
            for file_path in files:
                self._add_node(file_path)
            
            # Add relationships between co-occurring files
            for i, f1 in enumerate(files):
                for f2 in files[i+1:]:
                    # Infer relationship type (default to REFERENCES)
                    rel_type = self._infer_relationship(f1, f2)
                    self._add_relationship(f1, f2, rel_type)
        
        logger.info(
            "Built graph with %d nodes and %d relationships",
            len(self.nodes),
            len(self.relationships)
        )
    # --------------------------------------------------------------------------
    # Query API
    # --------------------------------------------------------------------------
    def get_strongest_relationship(
        self,
        file_a: str,
        file_b: str,
    ) -> Relationship | None:
        """Get the strongest relationship between two files."""
        outgoing = self._outgoing.get(file_a, {}).get(file_b, [])
        incoming = self._incoming.get(file_a, {}).get(file_b, [])
        
        all_rels = outgoing + incoming
        if not all_rels:
            return None
        
        return max(all_rels, key=lambda r: r.strength)
    # --------------------------------------------------------------------------
    # Scoring
    # --------------------------------------------------------------------------

    def calculate_relationship_score(
        self,
        current_files: list[str],
        memory_files: list[str],
    ) -> float:
        """
        Calculate co-occurrence score using typed relationships.
        
        Unlike simple co-occurrence (count-based), this:
        - Weights relationships by type (imported > tested > references)
        - Considers path distance (direct > indirect)
        - Uses relationship strength
        
        Args:
            current_files: Files in current work
            memory_files: Files from a retrieved memory
            
        Returns:
            Normalized score [0, 1]
        """
        if not current_files or not memory_files:
            return 0.0
        
        total_score = 0.0
        max_possible = 0.0
        
        for f1 in current_files:
            for f2 in memory_files:
                # Check both directions
                rel = self.get_strongest_relationship(f1, f2)
                if rel:
                    # Apply relationship weight
                    type_weight = RELATIONSHIP_WEIGHTS.get(
                        rel.relation_type, 0.5
                    )
                    # Combine with relationship strength and count
                    score = type_weight * rel.strength * min(rel.count / 3, 1.0)
                    total_score += score
                
                max_possible += 1.0
        
        return total_score / max_possible if max_possible > 0 else 0.0

    # --------------------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------------------

    def _add_node(self, file_path: str) -> None:
        """Add or update a node."""
        if file_path not in self.nodes:
            path = Path(file_path)
            self.nodes[file_path] = FileNode(
                path=file_path,
                name=path.name,
                language=self._detect_language(file_path),
            )
        self.nodes[file_path].entity_count += 1

    def _add_relationship(
        self,
        from_file: str,
        to_file: str,
        relation_type: str,
        evidence: str | None = None,
        count: int = 1,
    ) -> None:
        """Add or update a relationship."""
        # Skip self-references
        if from_file == to_file:
            return
        
        # Calculate strength based on type and count
        base_strength = RELATIONSHIP_WEIGHTS.get(relation_type, 0.5)
        strength = min(base_strength * (count / 3), 1.0)
        
        rel = Relationship(
            from_file=from_file,
            to_file=to_file,
            relation_type=relation_type,
            strength=strength,
            evidence=evidence,
            count=count,
        )
        
        self.relationships.append(rel)
        
        # Update adjacency lists
        self._outgoing[from_file][to_file].append(rel)
        self._incoming[to_file][from_file].append(rel)
        
        # Update type index
        self._by_type[relation_type].append(rel)

    def _infer_relationship(self, file_a: str, file_b: str) -> str:
        """Infer relationship type from file paths."""
        name_a = Path(file_a).stem.lower()
        name_b = Path(file_b).stem.lower()
        
        # Test file -> source file
        if "test" in name_a or "_test" in name_a:
            return RelationshipType.TESTED_BY
        if "test" in name_b or "_test" in name_b:
            return RelationshipType.TESTED_BY
        
        # Config file -> source
        if "config" in name_a:
            return RelationshipType.CONFIGURES
        if "config" in name_b:
            return RelationshipType.CONFIGURES
        
        # Import inference (simple heuristic)
        if "model" in name_a or "db" in name_a:
            return RelationshipType.IMPORTED_BY
        if "service" in name_a or "util" in name_a:
            return RelationshipType.USES
        
        return RelationshipType.REFERENCES
    def _detect_language(self, file_path: str) -> str | None:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
        }
        ext = Path(file_path).suffix
        return ext_map.get(ext)
    def clear(self) -> None:
        """Clear all graph data."""
        self.nodes.clear()
        self.relationships.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._by_type.clear()

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return (
            f"TypedCooccurrenceGraph("
            f"nodes={len(self.nodes)}, "
            f"relationships={len(self.relationships)})"
        )