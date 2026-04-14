from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mini FastAPI")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return [
        {"id": 1, "name": "Widget"},
        {"id": 2, "name": "Gadget"},
    ]


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id < 1:
        raise HTTPException(status_code=400, detail="Invalid ID")
    return {"id": item_id, "name": f"Item {item_id}"}
