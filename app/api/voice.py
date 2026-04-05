import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
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
        raise HTTPException(status_code=400, detail="无效的音频文件类型")
    
    # 2. 读取音频进行校检 (使用临时文件提高 MP3/PyAV 协议兼容性)
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.tmp', delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        container = av.open(tmp_path)
        if not container.streams.audio:
             raise HTTPException(status_code=400, detail="未发现音频流")
        
        stream = container.streams.audio[0]
        # 启用多线程解码提高速度和稳定性
        stream.thread_type = 'AUTO'
        
        # 3. 初始化转换与保存 (24kHz, mono, s16)
        voice_id = uuid.uuid4()
        target_filename = f"{voice_id}.wav"
        target_path = os.path.join(VOICES_DIR, target_filename)
        
        resampler = av.AudioResampler(
            format='s16', 
            layout='mono', 
            rate=24000
        )
        
        output_container = av.open(target_path, mode='w', format='wav')
        output_stream = output_container.add_stream('pcm_s16le', rate=24000)
        output_stream.layout = 'mono'
        
        # 在处理过程中累加时长，因为 MP3 的头部时长往往不准
        total_samples = 0
        
        try:
            for frame in container.decode(audio=0):
                # 累加原始采样数以计算时长
                total_samples += frame.samples
                
                # 重采样并写入
                resampled_frames = resampler.resample(frame)
                for rf in resampled_frames:
                    for packet in output_stream.encode(rf):
                        output_container.mux(packet)
            
            # 刷出缓冲区
            for rf in resampler.resample(None):
                for packet in output_stream.encode(rf):
                    output_container.mux(packet)
            
            for packet in output_stream.encode(None):
                output_container.mux(packet)
                
        except Exception as decode_err:
            logger.warning(f"Partial decode failure (continuing): {decode_err}")
            
        output_container.close()
        container.close()

        # 4. 最终时长校验 (基于实际处理的采样点)
        # ZipVoice 后端推理要求采样率 24000
        # 此处的 stream.rate 是输入的采样率
        real_duration = total_samples / stream.rate
        if real_duration < 3.0 or real_duration > 32.0:
            if os.path.exists(target_path): os.remove(target_path)
            raise HTTPException(status_code=400, detail=f"音频时长必须在 3-30秒之间 (当前为: {real_duration:.1f}秒)")

        # 5. 存入数据库
        profile = VoiceProfile(
            id=voice_id,
            user_id=user.id,
            name=name,
            audio_path=target_path,
            prompt_text=prompt_text,
            sample_rate=24000,
            duration_ms=int(real_duration * 1000)
        )
        session.add(profile)
        await session.commit()
        
        return {"id": voice_id, "name": name, "duration_sec": round(real_duration, 2)}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Voice upload processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"音频处理失败: {str(e)}")
    finally:
        # 清理临时文件
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except:
            pass

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
        raise HTTPException(status_code=404, detail="未发现该声纹档案")
        
    # 删除本地文件
    try:
        if os.path.exists(profile.audio_path):
            os.remove(profile.audio_path)
    except:
        pass
        
    await session.delete(profile)
    await session.commit()
    
    return {"status": "deleted"}

@router.get("/{voice_id}/audio")
async def get_voice_audio(
    voice_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """获取原音频文件进行试听"""
    statement = select(VoiceProfile).where(
        VoiceProfile.id == voice_id, 
        VoiceProfile.user_id == user.id
    )
    result = await session.execute(statement)
    profile = result.scalar_one_or_none()
    
    if not profile or not os.path.exists(profile.audio_path):
        raise HTTPException(status_code=404, detail="音频文件不存在")
        
    return FileResponse(
        profile.audio_path, 
        media_type="audio/wav", 
        filename=os.path.basename(profile.audio_path)
    )
