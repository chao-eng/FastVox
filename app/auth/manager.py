import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.engine import User, get_session
from config.settings import get_settings

settings = get_settings()

# --- 数据库适配器 ---

async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)

# --- 用户管理器 ---

class UserManager(BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.jwt_secret
    verification_token_secret = settings.jwt_secret

    def parse_id(self, value: str) -> uuid.UUID:
        try:
            return uuid.UUID(value)
        except ValueError:
            return None

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

# --- 认证策略 ---

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.jwt_secret, lifetime_seconds=settings.jwt_lifetime_seconds)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# --- FastAPI Users 导出 ---

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
