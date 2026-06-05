from sqlalchemy.orm import Session
from app.models.user import User
from uuid import uuid4

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> User:
        return self.db.query(User).filter(User.id == user_id, User.is_deleted == False).first()

    def get_by_email(self, email: str) -> User:
        return self.db.query(User).filter(User.email == email, User.is_deleted == False).first()

    def get_by_yandex_id(self, yandex_id: str) -> User:
        return self.db.query(User).filter(User.yandex_id == yandex_id, User.is_deleted == False).first()

    def create(self, email: str, password_hash: str = None, salt: str = None, yandex_id: str = None) -> User:
        user = User(
            id=str(uuid4()),
            email=email,
            password_hash=password_hash,
            salt=salt,
            yandex_id=yandex_id
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user