import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime
from app.db.engine import User, get_session, AppConfig
from app.auth.manager import current_superuser, UserManager, get_user_manager
from app.auth.schemas import UserRead, UserCreate

logger = logging.getLogger("FastVox")
router = APIRouter(prefix="/admin", tags=["Admin Management"])

# --- 用户管理 ---

@router.get("/users", response_model=List[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(current_superuser)
):
    """管理员列出所有用户"""
    statement = select(User)
    result = await session.execute(statement)
    users = result.scalars().all()
    logger.info(f"Admin {admin.email} is listing {len(users)} users. Admin status: {admin.is_superuser}")
    return users

@router.post("/users", response_model=UserRead)
async def create_user_by_admin(
    user_create: UserCreate,
    user_manager: UserManager = Depends(get_user_manager),
    admin: User = Depends(current_superuser)
):
    """管理员创建新用户"""
    try:
        user = await user_manager.create(user_create, safe=False)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(current_superuser)
):
    """管理员删除用户"""
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
        
    await session.delete(user)
    await session.commit()
    return {"status": "deleted"}

# --- 微信小程序配置管理 ---

@router.get("/config", response_model=List[AppConfig])
async def list_app_configs(
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(current_superuser)
):
    """获取所有小程序配置"""
    result = await session.execute(select(AppConfig))
    return result.scalars().all()

@router.post("/config")
async def save_app_config(
    config: AppConfig,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(current_superuser)
):
    """保存或更新小程序配置 (根据 appid)"""
    statement = select(AppConfig).where(AppConfig.appid == config.appid)
    result = await session.execute(statement)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.appsecret = config.appsecret
        existing.app_name = config.app_name
        existing.updated_at = datetime.utcnow()
        session.add(existing)
    else:
        # 确保新创建时有 ID (SQLModel 默认会处理，但这里显式一点)
        if not config.id:
            config.id = uuid.uuid4()
        session.add(config)
    
    await session.commit()
    return {"status": "success"}

@router.delete("/config/{config_id}")
async def delete_app_config(
    config_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(current_superuser)
):
    """删除小程序配置"""
    statement = select(AppConfig).where(AppConfig.id == config_id)
    result = await session.execute(statement)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
        
    await session.delete(config)
    await session.commit()
    return {"status": "deleted"}
