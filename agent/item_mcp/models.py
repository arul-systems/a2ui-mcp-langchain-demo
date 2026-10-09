import uuid

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """Fields required to add a new item to the catalog."""

    name: str = Field(description="Display name of the item.", examples=["Widget"])
    description: str | None = Field(default=None, description="Optional free-text description of the item.")
    price: float = Field(ge=0, description="Unit price of the item.")
    quantity: int = Field(default=0, ge=0, description="Number of units currently in stock.")


class Item(BaseModel):
    """An item stored in the catalog."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique item ID, server-generated.")
    name: str = Field(description="Display name of the item.")
    description: str | None = Field(default=None, description="Optional free-text description of the item.")
    price: float = Field(description="Unit price of the item.")
    quantity: int = Field(default=0, description="Number of units currently in stock.")
