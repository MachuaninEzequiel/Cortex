from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_items():
    resp = client.get("/items")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["name"] == "Widget"


def test_get_item():
    resp = client.get("/items/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_item_invalid():
    resp = client.get("/items/0")
    assert resp.status_code == 400


def test_create_item():
    """HU-003: Test POST /items creates a new item."""
    resp = client.post("/items", json={"name": "Sprocket"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Sprocket"
    assert "id" in data


def test_create_item_appears_in_list():
    """HU-003: Created item should be retrievable via GET /items."""
    resp = client.post("/items", json={"name": "Doohickey"})
    assert resp.status_code == 201
    new_id = resp.json()["id"]
    # Now fetch it
    resp2 = client.get(f"/items/{new_id}")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Doohickey"
