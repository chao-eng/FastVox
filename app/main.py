import asyncio
import logging
import psutil
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import select, Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr

from config.settings import get_settings
from app.db.engine import init_db, engine, User, VoiceProfile
from app.auth.manager import fastapi_users, auth_backend, current_superuser, UserManager, get_user_db
from app.auth.schemas import UserCreate, UserRead, UserUpdate
from app.core.shm_manager import shm_manager
from app.core.worker_pool import WorkerPool
from app.core.slot_manager import SlotManager
from app.core.uds_protocol import UDSServer

# 导入 API 路由器
from app.api.voice import router as voice_router
from app.api.tts import router as tts_router, container
from app.api.stats import router as stats_router

settings = get_settings()
logger = logging.getLogger("FastVox")

# 初始化后端服务单例
worker_pool = WorkerPool()
slot_manager = SlotManager(worker_pool)
uds_server = UDSServer(settings.uds_gateway_addr)

# --- 定义初始化专用输入模型 ---
class InitialSetupRequest(BaseModel):
    email: EmailStr
    password: str

# --- 生命周期管理 ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing FastVox Services...")
    await init_db()
    shm_manager.create()
    
    sock = uds_server.start()
    async def uds_reader():
        loop = asyncio.get_event_loop()
        while True:
            try:
                data = await loop.sock_recv(sock, 16)
                import struct
                slot_id, offset, size, status = struct.unpack('IIII', data)
                if status == 2: # READY
                    slot_manager.mark_ready(slot_id, size)
                elif status == 3: # ERROR
                    slot_manager.mark_ready(slot_id, 0)
            except: 
                break

    worker_pool.start()
    asyncio.create_task(uds_reader())
    asyncio.create_task(slot_manager.watchdog())
    # 4. 设置组件到 App 状态 (确保接口层可访问)
    app.state.slot_manager = slot_manager
    app.state.worker_pool = worker_pool
    # 同时保留对 tts.py 代码的兼容性支持 (如果还需要)
    container.slot_manager = slot_manager
    container.worker_pool = worker_pool
    logger.info("FastVox is ready.")
    yield
    worker_pool.stop()
    uds_server.stop()
    shm_manager.destroy()

# --- 实例化 App ---

app = FastAPI(
    title=settings.app_name, 
    version="0.1.0", 
    lifespan=lifespan,
    debug=settings.debug
)

# --- 初始化引导接口 (Setup Wizard) ---

@app.get("/api/v1/auth/setup-status", tags=["Auth"])
async def get_setup_status():
    from sqlmodel.ext.asyncio.session import AsyncSession
    async with AsyncSession(engine) as session:
        # 使用推荐的 exec() 语法
        result = await session.exec(select(User))
        exists = result.first() is not None
        return {"need_setup": not exists}

@app.post("/api/v1/auth/initial-setup", tags=["Auth"])
async def initial_setup(req: InitialSetupRequest):
    from sqlmodel.ext.asyncio.session import AsyncSession
    async with AsyncSession(engine) as session:
        # 1. 确认是否已有用户
        result = await session.exec(select(User))
        if result.first() is not None:
            raise HTTPException(status_code=400, detail="系统已初始化，请勿重复操作")
        
        # 2. 手动创建数据库适配器和管理器 (因为我们已经有了 session)
        from fastapi_users.db import SQLAlchemyUserDatabase
        user_db = SQLAlchemyUserDatabase(session, User)
        user_manager = UserManager(user_db)
        
        user_create = UserCreate(
            email=req.email,
            password=req.password,
            is_active=True,
            is_superuser=True,
            is_verified=True
        )
        user = await user_manager.create(user_create)
        return {"status": "success", "user_id": str(user.id)}

# --- 挂载业务路由 ---

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/api/v1/auth/jwt", tags=["Auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/api/v1/auth", tags=["Auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/api/v1/users", tags=["Users"])
app.include_router(voice_router, prefix="/api/v1")
app.include_router(tts_router, prefix="/api/v1")
app.include_router(stats_router, prefix="/api/v1")

@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "ok", "workers": worker_pool.health_check()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
