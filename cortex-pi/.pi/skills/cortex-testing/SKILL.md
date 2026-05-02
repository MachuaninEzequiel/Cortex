---
name: cortex-testing
description: "Patrones de testing del proyecto Cortex. Cargalo cuando escribas, ejecutes o corrijas tests: fixtures de pytest, mocks de ChromaDB/ONNX, cobertura por modulo, y convenciones de assert."
---

# Skill: Cortex Testing — Patrones de Testing del Proyecto

## Objetivo de Cobertura

| Módulo | Mínimo |
|--------|--------|
| `cortex/core.py` | 90% |
| `cortex/retrieval/` | 90% |
| `cortex/episodic/` | 85% |
| `cortex/semantic/` | 85% |
| `cortex/enricher/` | 80% |
| `cortex/mcp_server.py` | 75% |
| `cortex/cli/` | 70% |
| **Total** | **85%** |

## Fixtures Base (conftest.py)

```python
# tests/conftest.py
import pytest
from pathlib import Path
import chromadb
from unittest.mock import MagicMock, patch


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Vault temporal con notas de ejemplo."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "arch-decisions.md").write_text(
        "# Architecture Decisions\n\nUsamos ONNX por performance.\n"
    )
    (vault / "patterns.md").write_text(
        "# Patterns\n\n## RRF Fusion\nFusion de resultados con pesos.\n"
    )
    return vault


@pytest.fixture
def tmp_chroma(tmp_path: Path) -> chromadb.Client:
    """ChromaDB aislado para tests."""
    return chromadb.PersistentClient(path=str(tmp_path / "chroma"))


@pytest.fixture
def mock_onnx_embedder():
    """Mock del embedder ONNX — evita cargar el modelo en tests."""
    with patch("cortex.episodic.memory_store.ONNXEmbedder") as mock_cls:
        instance = MagicMock()
        instance.embed.return_value = [[0.1] * 384]  # vector 384-dim
        mock_cls.return_value = instance
        yield instance


@pytest.fixture
def mock_llm():
    """Mock del cliente LLM para summarization."""
    with patch("cortex.core.get_llm_client") as mock:
        client = MagicMock()
        client.complete.return_value = "Summarized content"
        mock.return_value = client
        yield client


@pytest.fixture
def agent_memory(tmp_vault, tmp_chroma, mock_onnx_embedder):
    """AgentMemory completamente aislada para tests de integración."""
    from cortex.core import AgentMemory
    from cortex.models import CortexConfig
    
    config = CortexConfig.model_validate({
        "episodic": {"persist_dir": str(tmp_chroma._path)},
        "semantic": {"vault_path": str(tmp_vault)},
    })
    return AgentMemory(config=config)
```

## Patrones de Test por Capa

### Tests Unitarios (aislados, rápidos)

```python
# tests/test_retrieval.py
import pytest
from cortex.retrieval.hybrid_search import rrf_fuse


class TestRRFFusion:
    def test_higher_score_ranks_first(self):
        """RRF debe ordenar por score descendente."""
        results = rrf_fuse(
            episodic=[("a", 0.9), ("b", 0.5)],
            semantic=[("c", 0.7)],
        )
        assert results[0].score >= results[1].score

    def test_episodic_weight_boosts_episodic(self):
        """Peso episódico > 1 debe priorizar resultados episódicos."""
        results = rrf_fuse(
            episodic=[("ep1", 0.8)],
            semantic=[("sm1", 0.8)],
            episodic_weight=2.0,
        )
        assert results[0].source == "episodic"

    def test_empty_inputs_returns_empty(self):
        results = rrf_fuse(episodic=[], semantic=[])
        assert results == []

    def test_single_source_works(self):
        results = rrf_fuse(episodic=[("a", 0.9)], semantic=[])
        assert len(results) == 1
        assert results[0].source == "episodic"
```

### Tests de Integración

```python
# tests/test_agent_memory.py
class TestAgentMemorySearch:
    def test_remember_then_search_finds_result(self, agent_memory):
        """Almacenar un evento y luego buscarlo debe retornar resultado."""
        agent_memory.remember("JWT authentication bug fixed in middleware")
        
        results = agent_memory.search("authentication")
        
        assert len(results) > 0
        assert any("auth" in r.content.lower() for r in results)

    def test_search_empty_query_raises(self, agent_memory):
        with pytest.raises(ValueError, match="Query cannot be empty"):
            agent_memory.search("")

    def test_search_no_results_returns_empty_list(self, agent_memory):
        results = agent_memory.search("xyznonexistentterm123456")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_rrf_fusion_uses_both_sources(self, agent_memory, tmp_vault):
        """Búsqueda debe combinar fuentes episódica y semántica."""
        agent_memory.remember("Test event about ONNX embeddings")
        
        results = agent_memory.search("ONNX")
        
        sources = {r.source for r in results}
        # Al menos una fuente debe estar presente
        assert len(sources) >= 1
```

### Tests de Edge Cases

```python
# Siempre testear:
# 1. Input vacío
# 2. Input muy largo
# 3. Caracteres especiales
# 4. Valores None/0/False
# 5. Listas vacías
# 6. Concurrencia (si aplica)

def test_collection_name_special_chars_rejected():
    from cortex.models import CollectionName
    with pytest.raises(ValueError):
        CollectionName(name="my collection!")  # espacio y ! prohibidos

def test_collection_name_too_long_rejected():
    from cortex.models import CollectionName
    with pytest.raises(ValueError):
        CollectionName(name="a" * 64)  # max 63 chars

def test_collection_name_valid_chars_accepted():
    from cortex.models import CollectionName
    cn = CollectionName(name="cortex_episodic-v2")
    assert cn.name == "cortex_episodic-v2"
```

## Comandos de Testing

```bash
# Rápido (falla al primer error)
pytest -x -q

# Con cobertura completa
pytest --cov=cortex --cov-report=term-missing --cov-fail-under=85

# Un módulo específico
pytest tests/test_retrieval.py -v

# Tests que matchean un nombre
pytest -k "test_rrf" -v

# Con output detallado en fallos
pytest --tb=short

# Generar reporte HTML
pytest --cov=cortex --cov-report=html
# → abre htmlcov/index.html
```

## Mocking de ChromaDB

```python
# Para tests que no deben tocar ChromaDB real
from unittest.mock import MagicMock, patch

def test_search_handles_chroma_error():
    with patch("cortex.episodic.memory_store.chromadb") as mock_chroma:
        mock_chroma.PersistentClient.side_effect = Exception("DB error")
        
        # El código debe manejar el error gracefully
        from cortex.core import AgentMemory
        # ... test que el sistema falla apropiadamente
```
