from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.config import settings
from app.services.auth import AuthService
from app.services.oauth import OAuthService
from app.schemas.auth import (
    RegisterRequest, LoginRequest, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse
)
from app.models.user import User
from app.core.security import (
    create_access_token, create_refresh_token,
    hash_token, decode_refresh_token
)
from app.repositories.refresh_token import RefreshTokenRepository
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Auth"])


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Устанавливает HttpOnly cookies с токенами."""
    response.set_cookie(
        key="access_token", value=access_token,
        httponly=True, secure=False, samesite="lax",
        max_age=15 * 60
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=False, samesite="lax",
        max_age=7 * 24 * 60 * 60
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создаёт нового пользователя с указанным email и паролем. Пароль хешируется с использованием bcrypt и уникальной соли.",
    responses={
        201: {"description": "Пользователь успешно зарегистрирован"},
        400: {"description": "Пользователь с таким email уже существует или данные невалидны"},
        422: {"description": "Ошибка валидации входных данных"},
    },
    response_model=MessageResponse,
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        user = service.register(data)
        return {"message": f"User registered successfully with id {user.id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/login",
    summary="Вход в систему",
    description="Аутентифицирует пользователя по email и паролю. В случае успеха устанавливает HttpOnly cookies с access и refresh токенами.",
    responses={
        200: {"description": "Успешный вход, cookies установлены"},
        401: {"description": "Неверный email или пароль"},
        422: {"description": "Ошибка валидации входных данных"},
    },
    response_model=MessageResponse,
)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        access_token, refresh_token, user = service.login(data)
        set_auth_cookies(response, access_token, refresh_token)
        return {"message": "Login successful"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post(
    "/refresh",
    summary="Обновление токенов",
    description="Обновляет пару access/refresh токенов. Старый refresh токен отзывается, новый сохраняется в БД. Требует валидный refresh cookie.",
    responses={
        200: {"description": "Токены успешно обновлены"},
        401: {"description": "Refresh token отсутствует, истёк или отозван"},
    },
    response_model=MessageResponse,
)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    service = AuthService(db)
    try:
        new_access, new_refresh, user = service.refresh_tokens(refresh_token)
        set_auth_cookies(response, new_access, new_refresh)
        return {"message": "Tokens refreshed"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get(
    "/whoami",
    summary="Текущий пользователь",
    description="Возвращает профиль текущего авторизованного пользователя. Требует валидный access token в cookies.",
    responses={
        200: {"description": "Профиль пользователя"},
        401: {"description": "Пользователь не авторизован или токен истёк"},
    },
    response_model=UserResponse,
)
def whoami(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/logout",
    summary="Завершение текущей сессии",
    description="Отзывает текущий refresh token в БД и удаляет cookies.",
    responses={
        200: {"description": "Сессия завершена"},
        401: {"description": "Пользователь не авторизован"},
    },
    response_model=MessageResponse,
)
def logout(request: Request, response: Response, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        AuthService(db).logout(refresh_token)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.post(
    "/logout-all",
    summary="Завершение всех сессий",
    description="Отзывает все refresh токены пользователя во всех устройствах и удаляет cookies.",
    responses={
        200: {"description": "Все сессии завершены"},
        401: {"description": "Пользователь не авторизован"},
    },
    response_model=MessageResponse,
)
def logout_all(response: Response, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    AuthService(db).logout_all(current_user.id)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "All sessions terminated"}


@router.get(
    "/oauth/yandex",
    summary="Начало OAuth входа через Yandex",
    description="Перенаправляет пользователя на страницу авторизации Yandex. Сохраняет state в cookie для защиты от CSRF.",
    responses={
        302: {"description": "Редирект на Yandex OAuth"},
    },
    include_in_schema=True,
)
def oauth_yandex_init(response: Response, db: Session = Depends(get_db)):
    oauth_service = OAuthService(db)
    url, state = oauth_service.get_yandex_authorization_url()
    response = RedirectResponse(url=url)
    response.set_cookie(
        key="oauth_state", value=state,
        httponly=True, secure=False, samesite="lax",
        max_age=5 * 60
    )
    return response


@router.get(
    "/oauth/yandex/callback",
    summary="Callback от Yandex OAuth",
    description="Обрабатывает ответ от Yandex, проверяет state, создаёт или находит пользователя, устанавливает локальные JWT cookies и редиректит на фронтенд.",
    responses={
        302: {"description": "Редирект на фронтенд после успешной авторизации"},
        400: {"description": "Ошибка обмена кода или невалидный state"},
    },
    include_in_schema=True,
)
async def oauth_yandex_callback(request: Request, response: Response, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    stored_state = request.cookies.get("oauth_state")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    if state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid state (CSRF check failed)")

    oauth_service = OAuthService(db)
    try:
        yandex_data = await oauth_service.exchange_code_for_user(code)
        user = oauth_service.find_or_create_yandex_user(yandex_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    refresh_payload = decode_refresh_token(refresh_token)
    expires_at = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
    RefreshTokenRepository(db).create(user.id, hash_token(refresh_token), expires_at)

    redirect_response = RedirectResponse(url=settings.FRONTEND_URL)
    set_auth_cookies(redirect_response, access_token, refresh_token)
    redirect_response.delete_cookie("oauth_state")
    return redirect_response


@router.post(
    "/forgot-password",
    summary="Запрос сброса пароля",
    description="Генерирует токен сброса пароля. В production отправляет ссылку на email. В dev-режиме возвращает токен в ответе для удобства тестирования.",
    responses={
        200: {"description": "Если email существует, ссылка отправлена"},
        422: {"description": "Ошибка валидации email"},
    },
    response_model=dict,
)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    token = service.forgot_password(data.email)
    return {"message": "If the email exists, a reset link has been sent", "debug_token": token}


@router.post(
    "/reset-password",
    summary="Сброс пароля по токену",
    description="Устанавливает новый пароль по одноразовому токену. Токен действителен 1 час.",
    responses={
        200: {"description": "Пароль успешно изменён"},
        400: {"description": "Токен невалиден или истёк"},
    },
    response_model=MessageResponse,
)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        service.reset_password(data.token, data.new_password)
        return {"message": "Password reset successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))