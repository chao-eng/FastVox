import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings

settings = get_settings()

# --- 数据库模型 ---

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: Optional[str] = Field(default=None, unique=True, index=True)
    hashed_password: str
    wechat_openid: Optional[str] = Field(default=None, unique=True, index=True)
    wechat_unionid: Optional[str] = Field(default=None, unique=True, index=True)
    nickname: str = "FastVox User"
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class VoiceProfile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    name: str
    audio_path: str # 相对于 data/voices/ 的本地文件路径
    prompt_text: str # 参考文本
    sample_rate: int = 24000
    duration_ms: int = 0
    is_public: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UsageLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    text_length: int
    voice_id: Optional[uuid.UUID] = Field(default=None, foreign_key="voiceprofile.id")
    duration_ms: int = 0
    latency_ms: int = 0
    status: str = "success" # success/error/timeout
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- 引擎与会话 ---

engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    # 自动创建表 (SQLite 常用方案)
    async with engine.begin() as conn:
        # 在真实迁移中应使用 Alembic，但初始化阶段可以使用 SQLModel 自动建表
        await conn.run_sync(SQLModel.metadata.create_all)
