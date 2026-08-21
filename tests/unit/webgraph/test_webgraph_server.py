
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
    
    # Unknown node must map to a clean 404 (service returns None).
    response = client.get("/api/node/missing", headers=headers)
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_webgraph_api_rejects_invalid_mode(tmp_path):
    (tmp_path / ".cortex").mkdir()
    (tmp_path / "vault").mkdir()
    app = create_app(tmp_path)
    client = app.test_client()
    headers = {"X-Cortex-WebGraph": "1"}

    response = client.get("/api/snapshot?mode=bogus", headers=headers)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_webgraph_api_node_detail_missing_returns_404(tmp_path):
    (tmp_path / ".cortex").mkdir()
    (tmp_path / "vault").mkdir()
    app = create_app(tmp_path)
    client = app.test_client()
    headers = {"X-Cortex-WebGraph": "1"}

    response = client.get("/api/node/missing-node", headers=headers)
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_webgraph_api_snapshot_includes_legend(tmp_path):
    (tmp_path / ".cortex").mkdir()
    (tmp_path / "vault").mkdir()
    app = create_app(tmp_path)
    client = app.test_client()
    headers = {"X-Cortex-WebGraph": "1"}

    response = client.get("/api/snapshot", headers=headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload.get("legend"), dict)
