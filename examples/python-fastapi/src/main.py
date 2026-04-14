from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Mini FastAPI")

# In-memory items store
_items: list[dict] = [
    {"id": 1, "name": "Widget"},
    {"id": 2, "name": "Gadget"},
]

_MAX_ITEM_ID = 9999


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


def _validate_item_id(item_id: int) -> None:
    """Validate item ID is within acceptable range.

    Raises:
        HTTPException 400 if item_id < 1 (invalid)
        HTTPException 400 if item_id > _MAX_ITEM_ID (too large)
    """
    if item_id < 1:
        raise HTTPException(status_code=400, detail="Item ID must be a positive integer (>= 1)")
    if item_id > _MAX_ITEM_ID:
        raise HTTPException(
            status_code=400,
            detail=f"Item ID exceeds maximum allowed value ({_MAX_ITEM_ID})",
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return _items


@app.get("/items/{item_id}")
def get_item(item_id: int):
    _validate_item_id(item_id)
    item = next((i for i in _items if i["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items", status_code=201)
def create_item(payload: ItemCreate):
    """Create a new item via POST /items."""
    new_id = max(i["id"] for i in _items) + 1 if _items else 1
    new_item = {"id": new_id, "name": payload.name}
    _items.append(new_item)
    return new_item
