import os
import uuid
from typing import Optional
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, or_
from app.db.engine import VoiceProfile, User, get_session
from app.auth.manager import current_active_user, auth_backend, get_user_manager, UserManager, fastapi_users
from config.settings import get_settings
from app.core.voice_utils import process_voice_audio
import av
import io
import zipfile
import json
import tempfile
import shutil

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
    单个上传参考音频 (ZipVoice 模式)
    """
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="无效的音频文件类型")
    
    with tempfile.NamedTemporaryFile(suffix='.tmp', delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        voice_id = uuid.uuid4()
        target_filename = f"{voice_id}.wav"
        target_path = os.path.join(VOICES_DIR, target_filename)
        
        duration, _ = process_voice_audio(tmp_path, target_path)

        if duration < 3.0 or duration > 32.0:
            if os.path.exists(target_path): os.remove(target_path)
            raise HTTPException(status_code=400, detail=f"音频时长必须在 3-32秒之间 (当前为: {duration:.1f}秒)")

        profile = VoiceProfile(
            id=voice_id,
            user_id=user.id,
            name=name,
            audio_path=target_path,
            prompt_text=prompt_text,
            sample_rate=24000,
            duration_ms=int(duration * 1000)
        )
        session.add(profile)
        await session.commit()
        
        return {"id": voice_id, "name": name, "duration_sec": round(duration, 2)}
        
    except Exception as e:
        logger.error(f"Voice upload failed: {e}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"音频处理失败: {str(e)}")
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

@router.post("/batch")
async def batch_upload_zip(
    file: UploadFile = File(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """
    批量从 ZIP 压缩包导入声纹。
    结构要求:
    - metadata.json: [{"filename": "xxx.wav", "name": "张三", "prompt_text": "参考文本"}, ...]
    - 对应的音频文件
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持 ZIP 压缩包")

    # 创建临时解压目录
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "upload.zip")
    
    try:
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 解压
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        metadata_path = os.path.join(temp_dir, "metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=400, detail="压缩包内缺少 metadata.json")
            
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        if not isinstance(metadata, list):
            raise HTTPException(status_code=400, detail="metadata.json 格式应为列表")

        results = []
        errors = []
        
        for idx, entry in enumerate(metadata):
            filename = entry.get("filename")
            name = entry.get("name")
            prompt_text = entry.get("prompt_text")
            
            if not all([filename, name, prompt_text]):
                errors.append({"index": idx, "error": "字段不全"})
                continue
                
            audio_file_path = os.path.join(temp_dir, filename)
            if not os.path.exists(audio_file_path):
                errors.append({"index": idx, "filename": filename, "error": "文件不存在"})
                continue
            
            try:
                voice_id = uuid.uuid4()
                target_filename = f"{voice_id}.wav"
                target_path = os.path.join(VOICES_DIR, target_filename)
                
                duration, _ = process_voice_audio(audio_file_path, target_path)
                
                profile = VoiceProfile(
                    id=voice_id,
                    user_id=user.id,
                    name=name,
                    audio_path=target_path,
                    prompt_text=prompt_text,
                    sample_rate=24000,
                    duration_ms=int(duration * 1000)
                )
                session.add(profile)
                results.append({"id": voice_id, "name": name, "filename": filename})
                
            except Exception as e:
                errors.append({"index": idx, "filename": filename, "error": str(e)})

        await session.commit()
        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="metadata.json 解析失败，请确保是标准的 JSON 格式")
    except Exception as e:
        logger.error(f"Batch import failed: {e}")
        raise HTTPException(status_code=500, detail=f"批量处理失败: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@router.get("/list")
async def list_voices(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """获取声纹列表 (包含自己上传的 + 系统公开的)"""
    # 查询条件：(user_id == current_user.id) OR (is_public == True)
    statement = select(VoiceProfile).where(
        or_(VoiceProfile.user_id == user.id, VoiceProfile.is_public == True)
    )
    result = await session.execute(statement)
    profiles = result.scalars().all()
    
    return [
        {
            "id": p.id, 
            "name": p.name, 
            "prompt_text": p.prompt_text,
            "duration_sec": p.duration_ms / 1000, 
            "is_public": p.is_public,
            "is_owner": p.user_id == user.id,
            "created_at": p.created_at
        } for p in profiles
    ]

@router.patch("/{voice_id}")
async def update_voice(
    voice_id: uuid.UUID,
    is_public: Optional[bool] = None,
    name: Optional[str] = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """更新声纹信息 (仅管理员可执行)"""
    if not user.is_superuser:
         raise HTTPException(status_code=403, detail="只有管理员可以修改声纹属性")
         
    statement = select(VoiceProfile).where(VoiceProfile.id == voice_id)
    result = await session.execute(statement)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="未发现该声纹档案")
        
    if is_public is not None:
        profile.is_public = is_public
    if name is not None:
        profile.name = name
        
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    
    return {"status": "success", "is_public": profile.is_public}

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
    token: str = None,
    user: User = Depends(fastapi_users.current_user(optional=True)),
    user_manager: UserManager = Depends(get_user_manager),
    session: AsyncSession = Depends(get_session)
):
    """获取原音频文件进行试听 (支持 Query Token 鉴权)"""
    # 如果 header 中没有 user，尝试从 token query param 解析
    if not user and token:
        strategy = auth_backend.get_strategy()
        user = await strategy.read_token(token, user_manager)

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="未授权访问，请登录")
    statement = select(VoiceProfile).where(
        VoiceProfile.id == voice_id, 
        or_(VoiceProfile.user_id == user.id, VoiceProfile.is_public == True)
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
