from threading import Lock

from models import Item


class ItemStore:
    def __init__(self) -> None:
        self._items: dict[str, Item] = {}
        self._lock = Lock()

    def add_item(self, item: Item) -> Item:
        with self._lock:
            self._items[item.id] = item

        print(f'Total users {self._items}')
        return item

    def list_items(self) -> list[Item]:
        return list(self._items.values())

    def get_item(self, item_id: str) -> Item | None:
        return self._items.get(item_id)


store = ItemStore()
