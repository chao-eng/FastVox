import httpx
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from config.settings import get_settings
from app.db.engine import User, get_session, AppConfig
from app.auth.manager import get_user_manager, UserManager, auth_backend

logger = logging.getLogger("FastVox")
settings = get_settings()

router = APIRouter(prefix="/auth/wechat", tags=["Auth"])

class WeChatLoginRequest(BaseModel):
    code: str
    appid: Optional[str] = None # 支持前端透传 appid，若无则使用 server 端默认配置

@router.post("/login")
async def wechat_login(
    req: WeChatLoginRequest,
    session: AsyncSession = Depends(get_session),
    user_manager: UserManager = Depends(get_user_manager)
):
    """
    微信小程序登录逻辑
    1. 调用微信接口换取 openid (Secret 从数据库动态获取)
    2. 查找或创建用户
    3. 返回 JWT Token
    """
    appid = req.appid or settings.wechat_app_id
    
    # 从数据库动态获取 AppSecret
    statement = select(AppConfig).where(AppConfig.appid == appid, AppConfig.is_active == True)
    result = await session.execute(statement)
    config = result.scalar_one_or_none()
    
    if not config:
        # 如果数据库没有，尝试回退到环境变量 (可选，为了兼容性)
        secret = settings.wechat_app_secret
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration for AppID {appid} not found"
            )
    else:
        secret = config.appsecret
    
    if not appid or not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WeChat AppID or Secret not configured"
        )

    # 1. 请求微信服务器
    url = f"https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={req.code}&grant_type=authorization_code"
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            resp_data = resp.json()
        except Exception as e:
            logger.error(f"Failed to call WeChat API: {e}")
            raise HTTPException(status_code=502, detail="WeChat API Communication Error")

    if "errcode" in resp_data and resp_data["errcode"] != 0:
        logger.warning(f"WeChat login error: {resp_data}")
        raise HTTPException(
            status_code=400, 
            detail=f"WeChat Login Failed: {resp_data.get('errmsg', 'Unknown Error')}"
        )

    openid = resp_data["openid"]
    unionid = resp_data.get("unionid")

    # 2. 数据库检索/创建用户 (确保 openid 和 appid 同时匹配)
    statement = select(User).where(User.wechat_openid == openid, User.appid == appid)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        # 创建新用户
        # 对于小程序用户，我们随机生成一个密码，因为他们主要通过 openid 登录
        import secrets
        import string
        random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        from app.auth.schemas import UserCreate
        user_create = UserCreate(
            email=f"{openid}@wechat.fastvox", # 生成占位 email 以满足 fastapi-users 约束
            password=random_password,
            nickname="WeChat User",
            appid=appid
        )
        
        # 使用 user_manager 创建用户，会自动处理 hashed_password
        user = await user_manager.create(user_create, safe=True)
        
        # 手动补全 openid 和 unionid (UserCreate schema 中通常不包含这些敏感/平台特定字段)
        user.wechat_openid = openid
        user.wechat_unionid = unionid
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new WeChat user: {user.id}")
    else:
        # 更新现有用户的信息 (可选)
        if unionid and user.wechat_unionid != unionid:
            user.wechat_unionid = unionid
            session.add(user)
            await session.commit()
            await session.refresh(user)

    # 3. 生成 JWT Token
    strategy = auth_backend.get_strategy()
    token = await strategy.write_token(user)
    
    return {
        "access_token": token,
        "token_type": "bearer"
    }
