from app.repositories.item import ItemRepository
from app.schemas.item import ItemCreate, ItemUpdate, PaginatedResponse
from math import ceil

class ItemService:
    def __init__(self, repo: ItemRepository):
        self.repo = repo

    def get_paginated(self, page: int = 1, limit: int = 10):
        if page < 1 or limit < 1 or limit > 100:
            raise ValueError("Invalid pagination params")
        skip = (page - 1) * limit
        items = self.repo.get_active_items(skip, limit)
        total = self.repo.count_active_items()
        return PaginatedResponse(
            data=items,
            meta={
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": ceil(total / limit) if total else 1
            }
        )

    def get_by_id(self, item_id: str):
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Item not found")
        return item

    def create(self, item_in: ItemCreate, owner_id: str):
        return self.repo.create(item_in, owner_id)

    def update(self, item_id: str, item_in: ItemUpdate, current_user_id: str):
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Item not found")
        if item.owner_id != current_user_id:
            raise PermissionError("You don't own this item")
        return self.repo.update(item, item_in)

    def delete(self, item_id: str, current_user_id: str):
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError("Item not found")
        if item.owner_id != current_user_id:
            raise PermissionError("You don't own this item")
        self.repo.soft_delete(item)