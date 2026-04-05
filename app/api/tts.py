import uuid
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.engine import VoiceProfile, User, get_session
from app.auth.manager import fastapi_users, get_user_manager, UserManager, auth_backend
from app.core.slot_manager import SlotManager
from app.core.worker_pool import WorkerPool, InferenceTask
from app.core.audio_encoder import AudioEncoder
from app.inference.text_splitter import TextSplitter
from app.core.shm_manager import shm_manager

logger = logging.getLogger("FastVox")
router = APIRouter(prefix="/tts", tags=["TTS Synthesis"])

# 单例服务容器 (由 main.py 初始化)
class TTSServiceContainer:
    slot_manager: Optional[SlotManager] = None
    worker_pool: Optional[WorkerPool] = None

container = TTSServiceContainer()

@router.websocket("/stream")
async def tts_stream(
    websocket: WebSocket,
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
    user_manager: UserManager = Depends(get_user_manager)
):
    """
    WebSocket 实时流式合成接口
    """
    # 1. 认证
    strategy = auth_backend.get_strategy()
    user = await strategy.read_token(token, user_manager)
    if not user or not user.is_active:
        await websocket.close(code=4001, reason="身份认证失败")
        return

    await websocket.accept()
    
    request_id = uuid.uuid4().hex[:8]
    slot_id = -1
    
    # 优先从 FastAPI 状态获取
    app_slot_manager = websocket.app.state.slot_manager if hasattr(websocket.app, "state") else container.slot_manager
    
    try:
        # 接收参数
        data = await websocket.receive_json()
        target_text = data.get("text", "").strip()
        voice_id = data.get("voice_id")
        speed = float(data.get("speed", 1.0))
        
        if not target_text:
            await websocket.send_json({"error": "待合成文本不能为空"})
            return

        # 获取声纹上下文
        prompt_audio, prompt_text = None, None
        if voice_id:
            profile_id = uuid.UUID(voice_id)
            statement = select(VoiceProfile).where(VoiceProfile.id == profile_id, VoiceProfile.user_id == user.id)
            result = await session.execute(statement)
            profile = result.scalar_one_or_none()
            if profile:
                prompt_audio = profile.audio_path
                prompt_text = profile.prompt_text

        # 获取 Slot
        slot_id = await app_slot_manager.acquire(request_id)
        
        # 文本分片 (ZipVoice 模式下建议单次推理不超过 150 字)
        splitter = TextSplitter(max_length=150)
        segments = splitter.split(target_text)
        
        encoder = AudioEncoder()
        
        for i, segment in enumerate(segments):
            # ！！！关键：在开始该分片的推理排队前，重置 slot 的 ready 状态
            app_slot_manager.reset_event(slot_id)
            
            task = InferenceTask(
                task_id=f"{request_id}_{i}",
                slot_id=slot_id,
                text=segment,
                prompt_audio_path=prompt_audio,
                prompt_text=prompt_text,
                speed=speed
            )
            
            # 提交任务
            logger.info(f"Submitting task {task.task_id} to queue (Slot: {slot_id})")
            await app_slot_manager.submit_task(slot_id, task)
            
            # 等待推理就绪 (增加超时到 90s)
            ready = await app_slot_manager.wait_for_ready(slot_id, timeout=90.0)
            if not ready:
                await websocket.send_json({"error": "推理任务超时"})
                break
                
            # 从 SHM 读取推理 Worker 写入的真实 PCM 数据
            data_size = app_slot_manager.get_last_size(slot_id)
            if data_size <= 0:
                logger.warning(f"Inference produced no data for slot {slot_id}")
                continue

            pcm_data = shm_manager.read_from_slot(slot_id, offset_in_slot=0, size=data_size)
            
            # 编码 Ogg/Opus
            opus_chunks = encoder.encode_opus_streaming([pcm_data])
            for chunk in opus_chunks:
                await websocket.send_bytes(chunk)
                
        # 结束信号 (空分片)
        await websocket.send_bytes(b"")

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {request_id}")
    except Exception as e:
        logger.error(f"TTS Stream Error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        if slot_id != -1:
            app_slot_manager.release(slot_id)
        try:
            await websocket.close()
        except:
            pass
