import uuid
from typing import Optional
from fastapi_users import schemas

class UserRead(schemas.BaseUser[uuid.UUID]):
    nickname: str
    is_superuser: bool

class UserCreate(schemas.BaseUserCreate):
    nickname: str = "FastVox User"

class UserUpdate(schemas.BaseUserUpdate):
    nickname: Optional[str] = None
    is_superuser: Optional[bool] = None
