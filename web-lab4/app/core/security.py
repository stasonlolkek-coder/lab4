import jwt
import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import settings

# Хеширование паролей
def hash_password(password: str) -> tuple[str, str]:
    """Возвращает (hash, salt)"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8'), salt.decode('utf-8')

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Проверяет пароль"""
    return bcrypt.checkpw(
        password.encode('utf-8'),
        password_hash.encode('utf-8')
    )

# Хеширование токенов для хранения в БД
def hash_token(token: str) -> str:
    """Хеширует токен для безопасного хранения"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

# JWT
def create_access_token(user_id: str) -> str:
    """Создаёт Access Token"""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRATION_MINUTES),
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm="HS256")

def create_refresh_token(user_id: str) -> str:
    """Создаёт Refresh Token"""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
        "jti": secrets.token_hex(16)  # Уникальный ID токена
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET, algorithm="HS256")

def decode_access_token(token: str) -> Optional[dict]:
    """Декодирует и проверяет Access Token"""
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def decode_refresh_token(token: str) -> Optional[dict]:
    """Декодирует и проверяет Refresh Token"""
    try:
        payload = jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None