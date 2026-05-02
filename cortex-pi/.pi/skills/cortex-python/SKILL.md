---
name: cortex-python
description: "Convenciones, patrones y stack tecnico del proyecto Cortex. Cargalo cuando trabajes con codigo Python del proyecto: type hints, Pydantic v2, Typer CLI, ChromaDB, ONNX, Ruff, Mypy o cualquier patron de imports/estructura de modulos."
---

# Skill: Cortex Python — Convenciones y Patrones del Proyecto

## Stack

- Python 3.10+ con type hints estrictos
- Pydantic v2 para validación y modelos
- Typer para CLI
- ChromaDB para vector storage
- ONNX Runtime para embeddings (all-MiniLM-L6-v2)
- Pytest para testing
- Ruff para linting y formateo (NO black, NO flake8)
- Mypy para type checking

## Estructura de Imports

```python
# 1. stdlib
import os
import logging
from pathlib import Path
from typing import Optional, Any

# 2. third-party (blank line separator)
import chromadb
from pydantic import BaseModel, field_validator
from onnxruntime import InferenceSession

# 3. local (blank line separator)
from cortex.models import CortexConfig, MemoryResult
from cortex.episodic.memory_store import EpisodicMemory
```

## Modelos Pydantic (siempre primero)

```python
from pydantic import BaseModel, field_validator
import re

class MemoryResult(BaseModel):
    score: float
    content: str
    source: str  # "episodic" | "semantic"
    metadata: dict[str, Any] = {}
    timestamp: str | None = None

    @field_validator("score")
    @classmethod
    def score_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Score must be between 0 and 1, got {v}")
        return v

class CollectionName(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(f"Invalid collection name: {v}")
        if len(v) > 63:
            raise ValueError(f"Collection name too long: {v}")
        return v
```

## Logging (NO print)

```python
import logging

logger = logging.getLogger(__name__)

# Uso correcto
logger.debug("Searching with query: %s", query)
logger.info("Found %d results", len(results))
logger.warning("Score below threshold: %.2f", score)
logger.error("ChromaDB query failed: %s", str(e))
```

## Manejo de Errores

```python
from cortex.models import CortexSearchError, CortexMemoryError

# Excepciones específicas, siempre con contexto
try:
    results = collection.query(query_embeddings=[embedding])
except chromadb.errors.NotFoundError as e:
    raise CortexMemoryError(f"Collection not found: {collection_name}") from e
except Exception as e:
    logger.error("Unexpected ChromaDB error: %s", str(e))
    raise CortexSearchError(f"Search failed for query: {query[:50]}") from e
```

## Paths (siempre Path, nunca os.path)

```python
from pathlib import Path

# Correcto
vault_path = Path(config.semantic.vault_path)
spec_file = vault_path / "specs" / f"{date}-{name}.md"
spec_file.parent.mkdir(parents=True, exist_ok=True)
spec_file.write_text(content, encoding="utf-8")

# Incorrecto ❌
vault_path = config.semantic.vault_path
spec_file = vault_path + "/specs/" + date + "-" + name + ".md"
```

## Subprocess (siempre lista, nunca shell=True)

```python
import subprocess

# Correcto
result = subprocess.run(
    ["git", "log", "--oneline", "-10"],
    capture_output=True,
    text=True,
    cwd=project_root,
    check=False,  # no lanzar excepción automática, manejar manualmente
)
if result.returncode != 0:
    logger.warning("git log failed: %s", result.stderr)

# Incorrecto ❌
os.system("git log --oneline -10")
subprocess.run("git log --oneline -10", shell=True)
```

## Docstrings (Google style)

```python
def hybrid_search(
    query: str,
    top_k: int = 5,
    episodic_weight: float = 1.0,
    semantic_weight: float = 1.0,
) -> list[MemoryResult]:
    """Search across both memory layers using RRF fusion.

    Performs parallel queries on episodic (ChromaDB) and semantic (Vault)
    layers, then fuses results using Reciprocal Rank Fusion.

    Args:
        query: Search query string. Cannot be empty.
        top_k: Number of results to retrieve from each source before fusion.
        episodic_weight: RRF weight multiplier for episodic results.
        semantic_weight: RRF weight multiplier for semantic results.

    Returns:
        List of MemoryResult sorted by fused RRF score (descending).
        Empty list if no results found in either layer.

    Raises:
        ValueError: If query is empty or top_k < 1.
        CortexSearchError: If both memory backends fail.

    Example:
        >>> results = hybrid_search("JWT authentication", top_k=5)
        >>> print(results[0].source)  # "episodic" or "semantic"
    """
    if not query.strip():
        raise ValueError("Query cannot be empty")
    if top_k < 1:
        raise ValueError(f"top_k must be >= 1, got {top_k}")
    ...
```

## Anti-Patrones Prohibidos

```python
# ❌ eval/exec
result = eval(user_input)

# ❌ except bare
try:
    ...
except:
    pass

# ❌ magic numbers
if score > 0.75:  # ← qué significa 0.75?
    ...
# ✅ usar constante
DEFAULT_SCORE_THRESHOLD = 0.75
if score > DEFAULT_SCORE_THRESHOLD:
    ...

# ❌ string format inseguro en YAML
frontmatter = f"---\ntitle: {user_title}\n---"  # puede romper YAML
# ✅ usar yaml.dump
import yaml
frontmatter = yaml.dump({"title": user_title}, default_flow_style=False)
```
