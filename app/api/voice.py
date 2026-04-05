import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.engine import VoiceProfile, User, get_session
from app.auth.manager import current_active_user
from config.settings import get_settings
import av
import io

logger = logging.getLogger("FastVox")
settings = get_settings()

router = APIRouter(prefix="/voice", tags=["Voice Management"])

# 确保声音目录存在
VOICES_DIR = os.path.join("./data", "voices")
os.makedirs(VOICES_DIR, exist_ok=True)

@router.post("/upload")
async def upload_voice(
    file: UploadFile = File(...),
    name: str = Form(...),
    prompt_text: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    上传参考音频并保存上下文 (ZipVoice 模式)
    """
    # 1. 验证文件格式 (限常见音频)
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid audio file type")
    
    # 2. 读取音频进行校检 (使用 PyAV)
    content = await file.read()
    try:
        container = av.open(io.BytesIO(content))
        stream = container.streams.audio[0]
        
        # 检查时长 (3s - 30s)
        duration_sec = float(stream.duration * stream.time_base)
        if duration_sec < 3.0 or duration_sec > 30.0:
            raise HTTPException(status_code=400, detail=f"Audio duration must be 3-30s (current: {duration_sec:.1f}s)")
        
        # 3. 统一转换并保存为 wav (24kHz, mono, s16)
        voice_id = uuid.uuid4()
        target_filename = f"{voice_id}.wav"
        target_path = os.path.join(VOICES_DIR, target_filename)
        
        # --- 使用 AudioResampler 进行高质量重采样 ---
        # 强制输出格式: 24000Hz, Mono, s16 (wav 16bit)
        resampler = av.AudioResampler(
            format='s16', 
            layout='mono', 
            rate=24000
        )
        
        output_container = av.open(target_path, mode='w', format='wav')
        output_stream = output_container.add_stream('pcm_s16le', rate=24000)
        output_stream.layout = 'mono' # 设置 layout 会自动配置 channels
        
        # 记录已提取总时间 (防止过短或过长)
        processed_duration = 0.0
        
        for frame in container.decode(audio=0):
            # 将输入帧重采样为输出所需格式
            resampled_frames = resampler.resample(frame)
            for rf in resampled_frames:
                # 编码并写入
                for packet in output_stream.encode(rf):
                    output_container.mux(packet)
                    
        # 刷出重采样器缓冲区
        for rf in resampler.resample(None):
            for packet in output_stream.encode(rf):
                output_container.mux(packet)
                    
        # 刷出编码缓冲区
        for packet in output_stream.encode(None):
            output_container.mux(packet)
            
        output_container.close()
        container.close()

        # 4. 存入数据库
        # 注意: audio_path 存储的是绝对路径或基于 data 的相对路径
        profile = VoiceProfile(
            id=voice_id,
            user_id=user.id,
            name=name,
            audio_path=target_path,
            prompt_text=prompt_text,
            sample_rate=24000,
            duration_ms=int(duration_sec * 1000)
        )
        session.add(profile)
        await session.commit()
        
        return {"id": voice_id, "name": name, "duration_sec": duration_sec}
        
    except Exception as e:
        logger.error(f"Voice upload processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")

@router.get("/list")
async def list_voices(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """获取当前用户的声纹上下文列表"""
    statement = select(VoiceProfile).where(VoiceProfile.user_id == user.id)
    result = await session.execute(statement)
    profiles = result.scalars().all()
    
    return [
        {
            "id": p.id, 
            "name": p.name, 
            "duration_sec": p.duration_ms / 1000, 
            "created_at": p.created_at
        } for p in profiles
    ]

@router.delete("/{voice_id}")
async def delete_voice(
    voice_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """删除声纹档案及本地文件"""
    statement = select(VoiceProfile).where(
        VoiceProfile.id == voice_id, 
        VoiceProfile.user_id == user.id
    )
    result = await session.execute(statement)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
        
    # 删除本地文件
    try:
        if os.path.exists(profile.audio_path):
            os.remove(profile.audio_path)
    except:
        pass
        
    await session.delete(profile)
    await session.commit()
    
    return {"status": "deleted"}
