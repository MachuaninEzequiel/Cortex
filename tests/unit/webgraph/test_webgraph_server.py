import pytest
from pathlib import Path
from cortex.webgraph.server import create_app

def test_webgraph_app_creation(tmp_path):
    # Setup minimal workspace
    (tmp_path / ".cortex").mkdir()
    (tmp_path / "vault").mkdir()
    (tmp_path / "config.yaml").write_text("semantic:\n  vault_path: vault")
    
    app = create_app(tmp_path)
    assert app is not None
    
    client = app.test_client()
    
    # Test index
    response = client.get("/")
    assert response.status_code == 200
    
    # Test API without header (should fail)
    response = client.get("/api/snapshot")
    assert response.status_code == 403
    
    # Test API with header
    headers = {"X-Cortex-WebGraph": "1"}
    response = client.get("/api/snapshot", headers=headers)
    assert response.status_code == 200
    assert "nodes" in response.get_json()

def test_webgraph_api_node_detail(tmp_path):
    (tmp_path / ".cortex").mkdir()
    (tmp_path / "vault").mkdir()
    app = create_app(tmp_path)
    client = app.test_client()
    headers = {"X-Cortex-WebGraph": "1"}
    
    # Test invalid node (should fail with 404 or handled by service)
    # Service throws KeyError if missing, but we should handle it in app
    app.config["PROPAGATE_EXCEPTIONS"] = True
    with pytest.raises(KeyError):
        client.get("/api/node/missing", headers=headers)
