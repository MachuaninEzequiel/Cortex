from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mini FastAPI")

# In-memory items store
_items: list[dict] = [
    {"id": 1, "name": "Widget"},
    {"id": 2, "name": "Gadget"},
]


class ItemCreate(BaseModel):
    name: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return _items


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id < 1:
        raise HTTPException(status_code=400, detail="Invalid ID")
    item = next((i for i in _items if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", status_code=201)
def create_item(payload: ItemCreate):
    """HU-003: Create a new item via POST /items."""
    new_id = max(i["id"] for i in _items) + 1 if _items else 1
    new_item = {"id": new_id, "name": payload.name}
    _items.append(new_item)
    return new_item
