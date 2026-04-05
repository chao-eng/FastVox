import asyncio
import logging
import psutil
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlmodel import select
from sqlalchemy import func

from config.settings import get_settings
from app.db.engine import init_db, UsageLog, User, VoiceProfile
from app.auth.manager import fastapi_users, auth_backend, current_superuser
from app.core.shm_manager import shm_manager
from app.core.worker_pool import WorkerPool
from app.core.slot_manager import SlotManager
from app.core.uds_protocol import UDSServer

# 导入 API 路由器
from app.api.voice import router as voice_router
from app.api.tts import router as tts_router, container

settings = get_settings()
logger = logging.getLogger("FastVox")

# 初始化后端服务单例
worker_pool = WorkerPool()
slot_manager = SlotManager(worker_pool)
uds_server = UDSServer(settings.uds_gateway_addr)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 启动阶段 ---
    logger.info("Initializing FastVox Services...")
    
    # 1. 初始化数据库
    await init_db()
    
    # 2. 初始化共享内存
    shm_manager.create()
    
    # 3. 启动 UDSServer 并将 SlotManager 与之绑定
    # 当 UDS 接收到 Ready 信号时，调用 SlotManager.mark_ready 唤醒等待协程
    sock = uds_server.start()
    
    # 定义异步 UDS 阅读器
    async def uds_reader():
        loop = asyncio.get_event_loop()
        while True:
            try:
                # 获取定长信令 (16字节)
                data = await loop.sock_recv(sock, 16)
                import struct
                slot_id, offset, size, status = struct.unpack('IIII', data)
                # 状态处理
                if status == 2: # READY
                    slot_manager.mark_ready(slot_id)
                elif status == 3: # ERROR
                    slot_manager.mark_ready(slot_id) # 唤醒以显示错误
            except Exception as e:
                logger.debug(f"UDS reader loop stop or error: {e}")
                break

    # 4. 启动 Worker 进程池
    worker_pool.start()
    
    # 5. 启动后台任务 (UDS 阅读器 + Slot 看门狗)
    asyncio.create_task(uds_reader())
    asyncio.create_task(slot_manager.watchdog())

    # 关联单例到 API 容器
    container.slot_manager = slot_manager
    container.worker_pool = worker_pool

    logger.info("FastVox is ready for inference.")

    yield
    
    # --- 关闭阶段 ---
    logger.info("Shutdown initiated. Cleaning up...")
    worker_pool.stop()
    uds_server.stop()
    shm_manager.destroy()

app = FastAPI(
    title=settings.app_name, 
    version="0.1.0", 
    lifespan=lifespan,
    debug=settings.debug
)

# 挂载核心路由
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["Auth"]
)
app.include_router(
    fastapi_users.get_register_router(User, User), prefix="/auth", tags=["Auth"]
)
app.include_router(voice_router, prefix="/api/v1")
app.include_router(tts_router, prefix="/api/v1")

# --- 监控与健康检查 T17 ---

@app.get("/health", tags=["Monitoring"])
async def health_check():
    return {"status": "ok", "workers": worker_pool.health_check()}

@app.get("/api/v1/health/detail", tags=["Monitoring"])
async def health_detail(user: User = Depends(current_superuser)):
    """详细系统指标 (仅限管理员)"""
    process = psutil.Process(os.getpid())
    
    return {
        "status": "healthy",
        "platform": os.name,
        "uptime_seconds": time.time() - process.create_time(),
        "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
        "workers": worker_pool.health_check(),
        "slots": {
            "total": settings.slot_count,
            "in_use": settings.slot_count - len(slot_manager._free_slots)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
