import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.engine import User, get_session
from app.auth.manager import current_superuser, UserManager, get_user_manager
from app.auth.schemas import UserRead, UserCreate

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])

@router.get("/", response_model=List[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(current_superuser)
):
    """管理员列出所有用户"""
    statement = select(User)
    result = await session.execute(statement)
    return result.scalars().all()

@router.post("/", response_model=UserRead)
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

@router.delete("/{user_id}")
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
