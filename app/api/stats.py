import uuid
from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from datetime import datetime, timedelta

from app.db.engine import UsageLog, User, get_session
from app.auth.manager import current_active_user

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("/summary")
async def get_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """
    获取使用统计摘要 (管理员看全局，普通用户看个人)
    """
    # 基础查询语句
    total_chars_stmt = select(func.sum(UsageLog.text_length))
    avg_latency_stmt = select(func.avg(UsageLog.latency_ms))
    success_count_stmt = select(func.count(UsageLog.id)).where(UsageLog.status == "success")
    total_count_stmt = select(func.count(UsageLog.id))
    
    # 权限隔离：如果是非管理员，仅查询自己的数据
    if not user.is_superuser:
        total_chars_stmt = total_chars_stmt.where(UsageLog.user_id == user.id)
        avg_latency_stmt = avg_latency_stmt.where(UsageLog.user_id == user.id)
        success_count_stmt = success_count_stmt.where(UsageLog.user_id == user.id)
        total_count_stmt = total_count_stmt.where(UsageLog.user_id == user.id)
    
    total_chars = (await session.execute(total_chars_stmt)).scalar() or 0
    avg_latency = (await session.execute(avg_latency_stmt)).scalar() or 0
    success_count = (await session.execute(success_count_stmt)).scalar() or 0
    total_count = (await session.execute(total_count_stmt)).scalar() or 0
    
    # 获取今日数据
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count_stmt = select(func.count(UsageLog.id)).where(UsageLog.created_at >= today_start)
    if not user.is_superuser:
        today_count_stmt = today_count_stmt.where(UsageLog.user_id == user.id)
    
    today_count = (await session.execute(today_count_stmt)).scalar() or 0

    return {
        "is_global": user.is_superuser,
        "stats": [
            {"name": "累计合成字数" if user.is_superuser else "我的合成总字数", "value": f"{total_chars/1000:.1f}k", "change": "+0%", "icon": "Database"},
            {"name": "系统平均时延" if user.is_superuser else "我的平均时延", "value": f"{avg_latency/1000:.2f}s", "change": "-0%", "icon": "Clock"},
            {"name": "服务成功率", "value": f"{success_count/total_count*100 if total_count > 0 else 100:.1f}%", "change": "+0%", "icon": "Activity"},
            {"name": "今日实时请求", "value": f"{today_count}", "change": "+0%", "icon": "TrendingUp"},
        ]
    }

@router.get("/throughput")
async def get_throughput(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """
    获取最近 30 分钟的吞吐量 (Requests/min)
    管理员看到的是系统总吞吐，用户看到的是个人请求频率
    """
    now = datetime.utcnow()
    minutes_to_show = 30
    start_time = now - timedelta(minutes=minutes_to_show)
    
    stmt = select(UsageLog.created_at).where(
        UsageLog.created_at >= start_time,
        UsageLog.status == "success"
    )
    
    if not user.is_superuser:
        stmt = stmt.where(UsageLog.user_id == user.id)
        
    stmt = stmt.order_by(UsageLog.created_at.asc())
    
    result = await session.execute(stmt)
    logs = result.scalars().all()
    
    counts = [0] * minutes_to_show
    for log in logs:
        delta = log - start_time
        idx = int(delta.total_seconds() // 60)
        if 0 <= idx < minutes_to_show:
            counts[idx] += 1
            
    return {
        "data": counts
    }

@router.get("/admin/user-ranking")
async def get_user_ranking(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """
    [管理员专用] 获取用户消耗排行榜 (Top 10)
    """
    if not user.is_superuser:
        return {"error": "Unauthorized"}
        
    # 按用户分组统计总字数和平均时延
    # 注意：这里需要关联 User 表获取昵称
    stmt = select(
        User.nickname,
        User.email,
        func.sum(UsageLog.text_length).label("total_chars"),
        func.count(UsageLog.id).label("total_requests")
    ).join(UsageLog).group_by(User.id).order_by(func.sum(UsageLog.text_length).desc()).limit(10)
    
    result = await session.execute(stmt)
    ranking = []
    for row in result.all():
        ranking.append({
            "name": row[0],
            "email": row[1],
            "chars": row[2],
            "requests": row[3]
        })
        
    return {"ranking": ranking}
