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
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    USES = "uses"
    REFERENCES = "references"
    CONFIGURES = "configures"
    DEFINES = "defines"


# Relationship strength (for scoring)
RELATIONSHIP_WEIGHTS: dict[str, float] = {
    RelationshipType.IMPORTED_BY: 1.0,    # Strongest - explicit dependency
    RelationshipType.TESTED_BY: 0.9,       # Strong - test coverage
    RelationshipType.EXTENDS: 0.8,         # Class inheritance
    RelationshipType.IMPLEMENTS: 0.8,      # Interface implementation
    RelationshipType.USES: 0.7,          # Function usage
    RelationshipType.REFERENCES: 0.5,        # General reference
    RelationshipType.CONFIGURES: 0.6,       # Configuration
    RelationshipType.DEFINES: 0.7,          # Defines/contains
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
        
        # Query relationships
        relationships = graph.get_related("src/auth.py", min_strength=0.5)
        for rel in relationships:
            print(f"{rel.from_file} --{rel.relation_type}--> {rel.to_file}")
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
        files_extractor: callable | None = None,
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
            if files_extractor:
                files = files_extractor(memory)
            else:
                files = getattr(memory, "files", [])
            
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

    def build_from_ast(
        self,
        file_paths: list[str],
        language: str | None = None,
    ) -> None:
        """
        Build relationships by parsing files with AST.
        
        Args:
            file_paths: List of file paths to analyze
            language: Programming language (for parser selection)
        """
        for file_path in file_paths:
            self._add_node(file_path)
            relationships = self._extract_relationships(file_path, language)
            for rel in relationships:
                self._add_relationship(
                    rel.from_file,
                    rel.to_file,
                    rel.relation_type,
                    evidence=rel.evidence,
                    count=rel.count,
                )
        
        logger.info(
            "Built AST graph with %d relationships from %d files",
            len(self.relationships),
            len(file_paths)
        )

    # --------------------------------------------------------------------------
    # Query API
    # --------------------------------------------------------------------------

    def get_related(
        self,
        file_path: str,
        relation_types: list[str] | None = None,
        min_strength: float = 0.0,
        direction: str = "both",
    ) -> list[Relationship]:
        """
        Get all files related to the given file.
        
        Args:
            file_path: Source file to query
            relation_types: Filter by specific relationship types
            min_strength: Minimum relationship strength
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            List of relevant Relationships
        """
        results: list[Relationship] = []
        
        if direction in ("outgoing", "both"):
            for rel_type, rels in self._outgoing.get(file_path, {}).items():
                if relation_types and rel_type not in relation_types:
                    continue
                results.extend(rels)
        
        if direction in ("incoming", "both"):
            for rel_type, rels in self._incoming.get(file_path, {}).items():
                if relation_types and rel_type not in relation_types:
                    continue
                results.extend(rels)
        
        # Filter by strength
        results = [r for r in results if r.strength >= min_strength]
        
        # Sort by strength descending
        results.sort(key=lambda r: r.strength, reverse=True)
        
        return results

    def get_path(
        self,
        from_file: str,
        to_file: str,
        max_depth: int = 3,
    ) -> list[Relationship] | None:
        """
        Find a path between two files (if it exists).
        
        Uses BFS to find the shortest path.
        
        Args:
            from_file: Start file
            to_file: Target file
            max_depth: Maximum path length
            
        Returns:
            List of relationships forming the path, or None if no path
        """
        from collections import deque
        
        queue = deque([(from_file, [])])
        visited: set[str] = {from_file}
        
        while queue:
            current, path = queue.popleft()
            
            if len(path) >= max_depth:
                continue
            
            if current == to_file:
                return path
            
            # Explore outgoing relationships
            for rel in self._get_all_outgoing(current):
                next_file = rel.to_file
                if next_file not in visited:
                    visited.add(next_file)
                    queue.append((next_file, path + [rel]))
        
        return None

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

    def get_files_by_type(self, relation_type: str) -> list[str]:
        """Get all files involved in a specific relationship type."""
        rels = self._by_type.get(relation_type, [])
        files = set()
        for rel in rels:
            files.add(rel.from_file)
            files.add(rel.to_file)
        return sorted(files)

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

    def _extract_relationships(
        self,
        file_path: str,
        language: str | None,
    ) -> list[Relationship]:
        """Extract relationships using AST parsing."""
        relationships: list[Relationship] = []
        
        path = Path(file_path)
        if not path.exists():
            return relationships
        
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return relationships
        
        # Language-specific extraction
        if language == "python" or path.suffix == ".py":
            relationships.extend(self._extract_python_relationships(file_path, content))
        elif language in ("javascript", "typescript") or path.suffix in (".js", ".ts", ".jsx", ".tsx"):
            relationships.extend(self._extract_js_relationships(file_path, content))
        
        return relationships

    def _extract_python_relationships(
        self,
        file_path: str,
        content: str,
    ) -> list[Relationship]:
        """Extract Python relationships using AST."""
        import ast
        import re
        
        relationships: list[Relationship] = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return relationships
        
        current_file = file_path
        filepath_stem = Path(file_path).stem
        
        # Collect imports
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
        
        # Collect class definitions and their bases
        class_bases: dict[str, list[str]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [
                    base.id if isinstance(base, ast.Name) else base.attr
                    for base in node.bases
                    if isinstance(base, ast.Name)
                ]
                if bases:
                    class_bases[node.name] = bases
        
        # Generate relationships from imports
        for imp in imports:
            # Try to find corresponding file
            related_file = self._find_related_file(imp, ["models", "services", "utils", "schemas"])
            if related_file and related_file != current_file:
                relationships.append(Relationship(
                    from_file=current_file,
                    to_file=related_file,
                    relation_type=RelationshipType.IMPORTED_BY,
                    evidence=f"import {imp}",
                ))
        
        # Generate extends relationships
        for class_name, bases in class_bases.items():
            for base in bases:
                related_file = self._find_related_file(base, ["models", "schemas"])
                if related_file and related_file != current_file:
                    relationships.append(Relationship(
                        from_file=current_file,
                        to_file=related_file,
                        relation_type=RelationshipType.EXTENDS,
                        evidence=f"class {class_name}({base})",
                    ))
        
        return relationships

    def _extract_js_relationships(
        self,
        file_path: str,
        content: str,
    ) -> list[Relationship]:
        """Extract JavaScript/TypeScript relationships."""
        import re
        
        relationships: list[Relationship] = []
        current_file = file_path
        
        # Extract imports
        import_pattern = re.compile(
            r"import\s+(?:{[^}]+}|\w+)\s+from\s+['\"]([^'\"]+)['\"]"
        )
        require_pattern = re.compile(
            r"const\s+{?\s*([^}=]+) }?\s*=\s*require\(['\"]([^'\"]+)['\"]\)"
        )
        
        for match in import_pattern.finditer(content):
            module = match.group(1)
            related = self._find_related_file(module, ["components", "hooks", "services", "utils"])
            if related:
                relationships.append(Relationship(
                    from_file=current_file,
                    to_file=related,
                    relation_type=RelationshipType.IMPORTED_BY,
                    evidence=f"import from {module}",
                ))
        
        return relationships

    def _find_related_file(
        self,
        module: str,
        search_dirs: list[str],
    ) -> str | None:
        """Find a related file given a module name."""
        # Try common extensions
        for ext in [".py", ".ts", ".tsx", ".js", ".jsx"]:
            for search_dir in search_dirs:
                candidate = self.project_root / search_dir / f"{module}{ext}"
                if candidate.exists():
                    return str(candidate.relative_to(self.project_root))
        
        return None

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

    def _get_all_outgoing(self, file_path: str) -> list[Relationship]:
        """Get all outgoing relationships from a file."""
        return [
            rel for rels in self._outgoing.get(file_path, {}).values()
            for rel in rels
        ]

    def clear(self) -> None:
        """Clear all graph data."""
        self.nodes.clear()
        self.relationships.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._by_type.clear()

    # --------------------------------------------------------------------------
    # Properties
    # --------------------------------------------------------------------------

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return (
            f"TypedCooccurrenceGraph("
            f"nodes={len(self.nodes)}, "
            f"relationships={len(self.relationships)})"
        )