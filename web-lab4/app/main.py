from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.v1.endpoints.items import router as items_router
from app.api.v1.endpoints.auth import router as auth_router
from app.core.config import settings

# Swagger доступен только в режиме разработки
openapi_url = "/openapi.json" if settings.is_development else None

app = FastAPI(
    title="Lab Project API",
    description="REST API для лабораторных работ №2–№4. Включает CRUD ресурсов, JWT-аутентификацию через HttpOnly cookies, OAuth 2.0 (Yandex ID), Soft Delete и пагинацию.",
    version="1.0.0",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
    openapi_url=openapi_url,
)

app.include_router(auth_router)
app.include_router(items_router)


def custom_openapi():
    """Кастомная OpenAPI-схема с описанием схем безопасности."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Схема безопасности для cookies
    openapi_schema["components"]["securitySchemes"] = {
        "CookieAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": "JWT Access Token, передаваемый через HttpOnly cookie. Swagger UI не может автоматически отправлять HttpOnly cookies, поэтому для тестирования защищённых эндпоинтов используйте curl/Postman или временно уберите флаг HttpOnly в dev-режиме.",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Альтернативный способ авторизации через заголовок Authorization: Bearer <token>. Используйте кнопку 'Authorize' выше, чтобы протестировать защищённые эндпоинты в Swagger UI.",
        },
        "OAuth2Yandex": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://oauth.yandex.ru/authorize",
                    "tokenUrl": "https://oauth.yandex.ru/token",
                    "scopes": {
                        "login:email": "Доступ к email пользователя",
                        "login:info": "Доступ к информации о пользователе",
                    },
                }
            },
        },
    }

    # Применяем BearerAuth ко всем операциям по умолчанию (для удобства тестирования в UI)
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            if isinstance(operation, dict) and "security" not in operation:
                operation["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", tags=["Root"])
def root():
    """Корневой эндпоинт. Возвращает приветственное сообщение."""
    return {"message": "Lab 4: OpenAPI Documentation"}