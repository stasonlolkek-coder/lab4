# Лабораторная работа №4

REST API на FastAPI с автоматической генерацией документации OpenAPI через Swagger UI. Проект включает JWT-аутентификацию через HttpOnly cookies, OAuth 2.0 через Yandex ID, Soft Delete, пагинацию и защиту ресурсов по принципу владения. Документация доступна только в режиме разработки и автоматически скрывается в production.

## Технологии

| Слой | Инструмент |
|---|---|
| Язык | Python 3.11 |
| Фреймворк | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Миграции | Alembic |
| СУБД | PostgreSQL 16 |
| Хеширование паролей | bcrypt с автоматической солью |
| JWT | PyJWT с ручной реализацией |
| OAuth 2.0 | httpx и Yandex ID |
| Документация | OpenAPI через встроенные средства FastAPI |
| Контейнеризация | Docker и Docker Compose |

## Структура проекта

```
app/
├── api/v1/endpoints/   # Контроллеры auth.py и items.py
├── services/           # Бизнес-логика auth.py, oauth.py, item.py
├── repositories/       # Работа с БД user.py, refresh_token.py, item.py
├── models/             # SQLAlchemy модели user.py, item.py, refresh_token.py
├── schemas/            # Pydantic DTO с описаниями и примерами
├── database/           # Подключение к БД
├── core/               # Конфигурация, security, dependencies
alembic/versions/       # Файлы миграций
```

## Переменные окружения

Создай файл `.env` на основе `.env.example`:

```env
DB_USER=student
DB_PASSWORD=student_secure_password
DB_NAME=wp_labs
DB_HOST=localhost
DB_PORT=5432
PORT=4200

JWT_ACCESS_SECRET=change_me_access_super_secret_key_123
JWT_REFRESH_SECRET=change_me_refresh_super_secret_key_456
JWT_ACCESS_EXPIRATION_MINUTES=15
JWT_REFRESH_EXPIRATION_DAYS=7

YANDEX_CLIENT_ID=your_yandex_client_id
YANDEX_CLIENT_SECRET=your_yandex_client_secret
YANDEX_REDIRECT_URI=http://localhost:4200/auth/oauth/yandex/callback

FRONTEND_URL=http://localhost:3000

APP_ENV=development
```

Переменная `APP_ENV` управляет доступом к документации. В режиме `development` Swagger UI доступен, в режиме `production` все эндпоинты документации возвращают 404.

## Запуск через Docker Compose

```bash
docker-compose up --build
```

Миграции применяются автоматически при старте контейнера.

## Локальный запуск

Установи зависимости:

```bash
pip install -r requirements.txt
```

Примени миграции:

```bash
alembic upgrade head
```

Запусти сервер:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 4200 --reload
```

## Документация API

Документация генерируется автоматически из кода через FastAPI и Pydantic. Ручные YAML или JSON файлы спецификации не используются.

### Доступ к документации

| URL | Описание | Режим |
|---|---|---|
| `/api/docs` | Интерактивный Swagger UI | development |
| `/api/redoc` | Альтернативный интерфейс ReDoc | development |
| `/openapi.json` | Сырая OpenAPI-спецификация | development |

В режиме production все три URL возвращают 404 Not Found.

### Тестирование защищённых эндпоинтов

1. Выполни `POST /auth/login` через curl с флагом `-v` или через Postman, чтобы увидеть cookies.
2. Скопируй значение cookie `access_token`.
3. В Swagger UI нажми кнопку Authorize в правом верхнем углу.
4. Вставь токен и подтверди.
5. Эндпоинты, отмеченные значком замка, станут доступны для тестирования.

## API Endpoints

### Аутентификация

| Метод | URL | Описание | Доступ |
|---|---|---|---|
| POST | `/auth/register` | Регистрация по email и паролю | Public |
| POST | `/auth/login` | Вход с установкой cookies | Public |
| POST | `/auth/refresh` | Обновление пары токенов | Public с refresh cookie |
| GET | `/auth/whoami` | Профиль текущего пользователя | Private |
| POST | `/auth/logout` | Завершение текущей сессии | Private |
| POST | `/auth/logout-all` | Завершение всех сессий | Private |
| GET | `/auth/oauth/yandex` | Начало OAuth входа | Public |
| GET | `/auth/oauth/yandex/callback` | Callback от Yandex | Public |
| POST | `/auth/forgot-password` | Запрос сброса пароля | Public |
| POST | `/auth/reset-password` | Установка нового пароля | Public |

### Ресурсы Items

| Метод | URL | Описание | Доступ |
|---|---|---|---|
| GET | `/items?page=1&limit=10` | Список с пагинацией | Private |
| GET | `/items/{id}` | Получить по ID | Private |
| POST | `/items` | Создать с привязкой к владельцу | Private |
| PUT | `/items/{id}` | Полное обновление | Private, только владелец |
| PATCH | `/items/{id}` | Частичное обновление | Private, только владелец |
| DELETE | `/items/{id}` | Soft Delete | Private, только владелец |

## Примеры запросов через cURL

Регистрация:

```bash
curl -X POST http://localhost:4200/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"test@example.com\", \"password\": \"securepass123\"}"
```

Вход с сохранением cookies:

```bash
curl -X POST http://localhost:4200/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"test@example.com\", \"password\": \"securepass123\"}" \
  -c cookies.txt
```

Получение профиля:

```bash
curl http://localhost:4200/auth/whoami -b cookies.txt
```

Создание ресурса:

```bash
curl -X POST http://localhost:4200/items \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d "{\"name\": \"My Item\", \"description\": \"Test\"}"
```

## Проверка production-режима

Замени в `.env` строку `APP_ENV=development` на `APP_ENV=production` и перезапусти сервер. Убедись, что:

- `http://localhost:4200/api/docs` возвращает 404
- `http://localhost:4200/api/redoc` возвращает 404
- `http://localhost:4200/openapi.json` возвращает 404
- Эндпоинты `/auth/login`, `/items` и другие продолжают работать

После проверки верни `APP_ENV=development`.

## Особенности реализации

- Документация собирается автоматически из аннотаций контроллеров и Pydantic-схем.
- Для каждого эндпоинта указаны summary, description и коды ответов 200, 201, 400, 401, 403, 404, 422.
- DTO содержат примеры значений через `Field(..., examples=[...])`.
- Чувствительные поля (пароли, соли, хеши токенов) исключены из схем ответов.
- В OpenAPI-схеме описаны три схемы безопасности: CookieAuth, BearerAuth, OAuth2Yandex.
- Пароли хешируются bcrypt с уникальной солью для каждого пользователя.
- Access и Refresh токены передаются только через HttpOnly cookies.
- Refresh токены хранятся в БД в виде SHA-256 хеша.
- OAuth 2.0 использует параметр state для защиты от CSRF.
- Soft Delete помечает запись флагом `is_deleted = true` без физического удаления.
- Ресурсы защищены проверкой владельца через поле `owner_id`.