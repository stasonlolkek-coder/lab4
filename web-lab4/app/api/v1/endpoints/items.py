from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.item import ItemService
from app.repositories.item import ItemRepository
from app.schemas.item import ItemCreate, ItemUpdate, PaginatedResponse, ItemResponse
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/items", tags=["Items"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/",
    summary="Список элементов с пагинацией",
    description="Возвращает список активных (не удалённых) элементов текущего пользователя. Поддерживает пагинацию через параметры page и limit.",
    responses={
        200: {"description": "Список элементов с мета-информацией"},
        400: {"description": "Невалидные параметры пагинации"},
        401: {"description": "Пользователь не авторизован"},
    },
    response_model=PaginatedResponse,
)
def read_items(
    page: int = Query(1, ge=1, description="Номер страницы (начинается с 1)"),
    limit: int = Query(10, ge=1, le=100, description="Количество элементов на странице (1–100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ItemService(ItemRepository(db))
    try:
        return service.get_paginated(page, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{item_id}",
    summary="Получить элемент по ID",
    description="Возвращает активный элемент по его UUID. Не возвращает удалённые элементы.",
    responses={
        200: {"description": "Элемент найден"},
        401: {"description": "Пользователь не авторизован"},
        404: {"description": "Элемент не найден или удалён"},
    },
    response_model=ItemResponse,
)
def read_item(item_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ItemService(ItemRepository(db))
    try:
        return service.get_by_id(item_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Item not found")


@router.post(
    "/",
    summary="Создать новый элемент",
    description="Создаёт новый элемент. Текущий пользователь автоматически становится владельцем.",
    responses={
        201: {"description": "Элемент успешно создан"},
        401: {"description": "Пользователь не авторизован"},
        422: {"description": "Ошибка валидации данных"},
    },
    response_model=ItemResponse,
    status_code=201,
)
def create_item(item_in: ItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ItemService(ItemRepository(db))
    return service.create(item_in, current_user.id)


@router.put(
    "/{item_id}",
    summary="Полное обновление элемента",
    description="Полностью заменяет данные элемента. Доступно только владельцу.",
    responses={
        200: {"description": "Элемент обновлён"},
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Пользователь не является владельцем"},
        404: {"description": "Элемент не найден"},
    },
    response_model=ItemResponse,
)
def update_item(item_id: str, item_in: ItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ItemService(ItemRepository(db))
    try:
        return service.update(item_id, item_in, current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Item not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You don't own this item")


@router.patch(
    "/{item_id}",
    summary="Частичное обновление элемента",
    description="Обновляет только указанные поля элемента. Доступно только владельцу.",
    responses={
        200: {"description": "Элемент обновлён"},
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Пользователь не является владельцем"},
        404: {"description": "Элемент не найден"},
    },
    response_model=ItemResponse,
)
def patch_item(item_id: str, item_in: ItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ItemService(ItemRepository(db))
    try:
        return service.update(item_id, item_in, current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Item not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You don't own this item")


@router.delete(
    "/{item_id}",
    summary="Мягкое удаление элемента",
    description="Помечает элемент как удалённый (is_deleted = true). Физическое удаление не происходит. Доступно только владельцу.",
    responses={
        204: {"description": "Элемент успешно удалён"},
        401: {"description": "Пользователь не авторизован"},
        403: {"description": "Пользователь не является владельцем"},
        404: {"description": "Элемент не найден"},
    },
    status_code=204,
)
def delete_item(item_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = ItemService(ItemRepository(db))
    try:
        service.delete(item_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Item not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You don't own this item")