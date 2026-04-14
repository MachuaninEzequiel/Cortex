import pytest
from fastapi.testclient import TestClient
from src.main import app, _validate_item_id

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


# ── Validation tests ───────────────────────────────────────────

def test_get_item_invalid_zero():
    """ID = 0 must return 400."""
    resp = client.get("/items/0")
    assert resp.status_code == 400
    assert "positive integer" in resp.json()["detail"]


def test_get_item_invalid_negative():
    """Negative IDs must return 400."""
    resp = client.get("/items/-5")
    assert resp.status_code == 400


def test_get_item_exceeds_max():
    """ID > 9999 must return 400."""
    resp = client.get("/items/10000")
    assert resp.status_code == 400
    assert "maximum" in resp.json()["detail"]


def test_get_item_not_found():
    """Valid ID that doesn't exist must return 404."""
    resp = client.get("/items/9999")
    assert resp.status_code == 404


def test_create_item():
    """POST /items creates a new item."""
    resp = client.post("/items", json={"name": "Sprocket"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Sprocket"
    assert "id" in data


def test_create_item_empty_name():
    """POST /items with empty name must return 422 (Pydantic validation)."""
    resp = client.post("/items", json={"name": ""})
    assert resp.status_code == 422


def test_create_item_appears_in_list():
    """Created item must be retrievable via GET /items/{id}."""
    resp = client.post("/items", json={"name": "Doohickey"})
    assert resp.status_code == 201
    new_id = resp.json()["id"]
    resp2 = client.get(f"/items/{new_id}")
    assert resp2.status_code == 200
    assert resp2.json()["name"] == "Doohickey"
