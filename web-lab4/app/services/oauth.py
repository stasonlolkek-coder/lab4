import httpx
import secrets
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.user import UserRepository
from app.models.user import User

YANDEX_AUTHORIZE_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_USERINFO_URL = "https://login.yandex.ru/info"


class OAuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_yandex_authorization_url(self) -> tuple[str, str]:
        """Возвращает (url, state) для редиректа на Yandex"""
        state = secrets.token_urlsafe(32)
        params = {
            "response_type": "code",
            "client_id": settings.YANDEX_CLIENT_ID,
            "redirect_uri": settings.YANDEX_REDIRECT_URI,
            "state": state
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{YANDEX_AUTHORIZE_URL}?{query}", state

    async def exchange_code_for_user(self, code: str) -> dict:
        """Обменивает код авторизации на токен и получает данные пользователя"""
        async with httpx.AsyncClient() as client:
            # 1. Обмен кода на access_token провайдера
            token_response = await client.post(
                YANDEX_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.YANDEX_CLIENT_ID,
                    "client_secret": settings.YANDEX_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if token_response.status_code != 200:
                raise ValueError("Failed to exchange code for token")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # 2. Получение данных пользователя по access_token
            user_response = await client.get(
                YANDEX_USERINFO_URL,
                params={"oauth_token": access_token, "format": "json"}
            )
            if user_response.status_code != 200:
                raise ValueError("Failed to get user info")

            return user_response.json()

    def find_or_create_yandex_user(self, yandex_data: dict) -> User:
        """Ищет или создаёт локального пользователя по данным от Yandex"""
        yandex_id = str(yandex_data.get("id"))
        email = yandex_data.get("default_email")

        if not email:
            raise ValueError("Yandex account has no email")

        # Ищем по yandex_id
        user = self.user_repo.get_by_yandex_id(yandex_id)
        if user:
            return user

        # Ищем по email
        user = self.user_repo.get_by_email(email)
        if user:
            # Привязываем yandex_id к существующему пользователю
            user.yandex_id = yandex_id
            self.db.commit()
            self.db.refresh(user)
            return user

        # Создаём нового пользователя
        user = self.user_repo.create(
            email=email,
            yandex_id=yandex_id
        )
        return user