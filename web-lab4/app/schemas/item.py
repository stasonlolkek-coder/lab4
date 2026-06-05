from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ItemCreate(BaseModel):
    """DTO для создания нового элемента."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "My first item",
                    "description": "Detailed description of the item"
                }
            ]
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Название элемента",
        examples=["My first item"]
    )
    description: Optional[str] = Field(
        None,
        description="Описание элемента (необязательно)",
        examples=["Detailed description of the item"]
    )


class ItemUpdate(BaseModel):
    """DTO для обновления элемента."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Updated item",
                    "description": "Updated description"
                }
            ]
        }
    )

    name: str = Field(..., min_length=1, max_length=255, description="Новое название", examples=["Updated item"])
    description: Optional[str] = Field(None, description="Новое описание", examples=["Updated description"])


class ItemResponse(BaseModel):
    """Публичное представление элемента."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Уникальный идентификатор элемента (UUID)", examples=["550e8400-e29b-41d4-a716-446655440000"])
    name: str = Field(..., description="Название элемента", examples=["My first item"])
    description: Optional[str] = Field(None, description="Описание элемента", examples=["Detailed description"])
    owner_id: str = Field(..., description="ID владельца элемента", examples=["550e8400-e29b-41d4-a716-446655440001"])
    created_at: datetime = Field(..., description="Дата создания", examples=["2026-06-05T10:00:00Z"])
    updated_at: datetime = Field(..., description="Дата последнего обновления", examples=["2026-06-05T10:00:00Z"])


class PaginationMeta(BaseModel):
    """Мета-информация о пагинации."""

    total: int = Field(..., description="Общее количество элементов", examples=[42])
    page: int = Field(..., description="Текущая страница", examples=[1])
    limit: int = Field(..., description="Элементов на странице", examples=[10])
    totalPages: int = Field(..., description="Всего страниц", examples=[5])


class PaginatedResponse(BaseModel):
    """Ответ со списком элементов и мета-информацией."""

    data: list[ItemResponse] = Field(..., description="Массив элементов текущей страницы")
    meta: PaginationMeta = Field(..., description="Мета-информация о пагинации")