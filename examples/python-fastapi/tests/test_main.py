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
    assert len(data) == 2
    assert data[0]["name"] == "Widget"


def test_get_item():
    resp = client.get("/items/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


def test_get_item_invalid():
    resp = client.get("/items/0")
    assert resp.status_code == 400
