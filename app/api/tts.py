import uuid
import logging
import asyncio
import time
import numpy as np
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, or_
from app.db.engine import VoiceProfile, User, UsageLog, get_session
from app.auth.manager import fastapi_users, get_user_manager, UserManager, auth_backend
from app.core.slot_manager import SlotManager
from app.core.worker_pool import WorkerPool, InferenceTask
from app.core.audio_encoder import AudioEncoder, StreamingEncoder, PcmTempoProcessor
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
    start_time = time.time()  # 记录开始时间以计算时延
    total_pcm_bytes = 0      # 记录总 PCM 字节量以计算音频时长
    
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
            statement = select(VoiceProfile).where(
                VoiceProfile.id == profile_id, 
                or_(VoiceProfile.user_id == user.id, VoiceProfile.is_public == True)
            )
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
        
        # 初始化有状态的流式编码器 (纯编码，不含变速)
        encoder = StreamingEncoder(sample_rate=24000)
        
        # 初始化变速处理器 (独立于编码器，在 PCM 层面进行无音高扭曲变速)
        tempo_processor = None
        if abs(speed - 1.0) > 0.01:
            tempo_processor = PcmTempoProcessor(sample_rate=24000, speed=speed)
        
        # 初始化语境变量 (用于多分片间的平滑衔接)
        # 第一段默认使用用户上传的静态声纹配置
        current_prompt_audio_path = prompt_audio
        current_prompt_text = prompt_text
        current_prompt_audio_samples = None

        for i, segment in enumerate(segments):
            # ！！！关键：在开始该分片的推理排队前，重置 slot 的 ready 状态
            app_slot_manager.reset_event(slot_id)
            
            task = InferenceTask(
                task_id=f"{request_id}_{i}",
                slot_id=slot_id,
                text=segment,
                prompt_audio_path=current_prompt_audio_path,
                prompt_text=current_prompt_text,
                prompt_audio_samples=current_prompt_audio_samples,
                speed=1.0 # 强制模型推理层保持 1.0 倍速，以保证最高的稳定性
            )
            
            # 提交任务
            logger.info(f"Submitting task {task.task_id} to queue (Slot: {slot_id})")
            await app_slot_manager.submit_task(slot_id, task)
            
            # 等待推理就绪 (增加超时到 120s)
            ready = await app_slot_manager.wait_for_ready(slot_id, timeout=120.0)
            if not ready:
                await websocket.send_json({"error": "推理任务超时"})
                break
                
            # 从 SHM 读取推理 Worker 写入的真实 PCM 数据
            data_size = app_slot_manager.get_last_size(slot_id)
            if data_size <= 0:
                logger.warning(f"Inference produced no data for slot {slot_id}")
                continue

            pcm_data = shm_manager.read_from_slot(slot_id, offset_in_slot=0, size=data_size)
            total_pcm_bytes += len(pcm_data) # 累加数据量
            
            # 如果存在变速处理器，先在 PCM 层面进行无损变速
            if tempo_processor:
                pcm_data = tempo_processor.process(pcm_data)
            
            # 关键：计算本段音频的时长 (ms) 并提前通过 JSON 发送给前端
            segment_duration_ms = int(len(pcm_data) / 2 / 24000 * 1000)
            await websocket.send_json({
                "type": "metadata",
                "segment_duration_ms": segment_duration_ms
            })
            
            # 使用有状态编码器进行 Opus 编码 (持续追加到同一个 Ogg 容器)
            chunk = encoder.encode_chunk(pcm_data)
            if chunk:
                await websocket.send_bytes(chunk)
                
            # --- 语境更新逻辑 (上下文衔接的核心) ---
            # 先进行音频质量检测，防止乱码音频污染后续分段
            ctx_samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
            rms_energy = np.sqrt(np.mean(ctx_samples ** 2)) if len(ctx_samples) > 0 else 0
            peak = np.max(np.abs(ctx_samples)) if len(ctx_samples) > 0 else 0
            
            # 异常判定：静音 (RMS < 50) 或严重削波 (峰值持续顶满 ≈ 32767)
            is_corrupted = rms_energy < 50 or (peak > 32700 and rms_energy > 20000)
            
            if is_corrupted:
                logger.warning(
                    f"Segment {i} audio quality check FAILED (RMS={rms_energy:.0f}, Peak={peak:.0f}). "
                    f"Falling back to original voice profile to prevent context pollution."
                )
                # 回退到用户上传的原始声纹
                current_prompt_text = prompt_text
                current_prompt_audio_path = prompt_audio
                current_prompt_audio_samples = None
            else:
                # 正常情况：下一段使用当前段的输出作为语境
                current_prompt_text = segment
                current_prompt_audio_samples = pcm_data
                current_prompt_audio_path = None
                
        # 刷出变速处理器中残留的 PCM 数据
        if tempo_processor:
            residual_pcm = tempo_processor.flush()
            if residual_pcm:
                chunk = encoder.encode_chunk(residual_pcm)
                if chunk:
                    await websocket.send_bytes(chunk)

        # 结束编码并发送 Ogg Footer
        footer = encoder.close()
        if footer:
            await websocket.send_bytes(footer)

        # 结束信号 (空分片)
        await websocket.send_bytes(b"")

        # 4. 记录使用统计 (非阻塞写入)
        try:
            # 计算时长 (ms): bytes / 2 (16bit) / 24000 (rate) * 1000
            audio_duration_ms = int(total_pcm_bytes / 2 / 24000 * 1000)
            inference_latency_ms = int((time.time() - start_time) * 1000)

            usage = UsageLog(
                user_id=user.id,
                text_length=len(target_text),
                voice_id=uuid.UUID(voice_id) if voice_id else None,
                duration_ms=audio_duration_ms,
                latency_ms=inference_latency_ms,
                status="success"
            )
            session.add(usage)
            await session.commit()
        except Exception as e:
            logger.warning(f"Failed to log usage: {e}")

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
