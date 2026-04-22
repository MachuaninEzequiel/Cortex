import os
import pytest
from cortex.embedders.factory import EmbedderFactory, EmbeddingConfig, UnsupportedBackendError
from cortex.embedders.base import EmbedderProtocol

@pytest.fixture(params=["onnx", "local", "openai"])
def embedder_backend(request):
    backend = request.param
    
    if backend == "local":
        pytest.importorskip("sentence_transformers")
    elif backend == "openai":
        # Mocking OpenAI for contract test to not require real API key
        # or skip if not mocked. We will skip if real key is not set.
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
            
    return backend

def test_embedder_conforms_to_protocol(embedder_backend):
    """
    Test de contrato: verifica estructuralmente que la instancia
    cumple con EmbedderProtocol y tiene los atributos esperados.
    """
    config = EmbeddingConfig(backend=embedder_backend)
    embedder = EmbedderFactory.create(config)
    
    assert isinstance(embedder, EmbedderProtocol)
    assert embedder.backend == embedder_backend
    assert isinstance(embedder.model_name, str)
    assert len(embedder.model_name) > 0

def test_embedder_single_embedding(embedder_backend):
    """
    Test de contrato: verifica que `embed` funciona y retorna un list[float].
    """
    config = EmbeddingConfig(backend=embedder_backend)
    embedder = EmbedderFactory.create(config)
    
    result = embedder.embed("Hello world")
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(x, float) for x in result)

def test_embedder_batch_embedding(embedder_backend):
    """
    Test de contrato: verifica que `embed_batch` funciona y retorna list[list[float]].
    """
    config = EmbeddingConfig(backend=embedder_backend)
    embedder = EmbedderFactory.create(config)
    
    texts = ["Hello world", "Testing embed batch", "Cortex memory"]
    result = embedder.embed_batch(texts)
    
    assert isinstance(result, list)
    assert len(result) == 3
    for vec in result:
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(x, float) for x in vec)

def test_embedder_factory_invalid_backend():
    config = EmbeddingConfig(backend="invalid_backend") # type: ignore
    with pytest.raises(UnsupportedBackendError):
        EmbedderFactory.create(config)
