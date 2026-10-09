from fastapi import FastAPI, HTTPException, status

from models import Item, ItemCreate
from store import store

app = FastAPI(
    title="Item API",
    description=(
        "A simple REST API for managing an item catalog: add new items, "
        "list all items, and look up a single item by ID. Catalog state is "
        "held in memory for the lifetime of the server process (nothing is "
        "persisted to disk) and is not shared across server restarts."
    ),
    version="1.0.0",
)


@app.post(
    "/items",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new item",
    tags=["items"],
)
def add_item(payload: ItemCreate) -> Item:
    """Add a new item to the catalog and return it, including its unique, server-generated ID."""
    item = Item(**payload.model_dump())
    return store.add_item(item)


@app.get(
    "/items",
    response_model=list[Item],
    summary="List all items",
    tags=["items"],
)
def list_items() -> list[Item]:
    """List every item currently in the catalog."""
    return store.list_items()


@app.get(
    "/items/{item_id}",
    response_model=Item,
    summary="Get a single item",
    tags=["items"],
)
def get_item(item_id: str) -> Item:
    """Fetch one item by ID. Returns 404 if no item with this ID exists."""
    item = store.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
