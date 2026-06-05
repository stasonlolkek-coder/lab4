from sqlalchemy.orm import Session
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate
from uuid import uuid4

class ItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_items(self, skip: int, limit: int):
        return self.db.query(Item).filter(Item.is_deleted == False).offset(skip).limit(limit).all()

    def count_active_items(self):
        return self.db.query(Item).filter(Item.is_deleted == False).count()

    def get_by_id(self, item_id: str):
        return self.db.query(Item).filter(Item.id == item_id, Item.is_deleted == False).first()

    def create(self, item_in: ItemCreate, owner_id: str):
        db_item = Item(
            id=str(uuid4()),
            name=item_in.name,
            description=item_in.description,
            owner_id=owner_id
        )
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def update(self, db_item: Item, item_in: ItemUpdate):
        db_item.name = item_in.name
        db_item.description = item_in.description
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def soft_delete(self, db_item: Item):
        db_item.soft_delete()
        self.db.commit()