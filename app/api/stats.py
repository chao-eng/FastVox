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
    user: User = Depends(current_active_user) # 允许普通用户查看
):
    """
    获取全局使用统计摘要
    """
    # 累计合成字数
    total_chars_stmt = select(func.sum(UsageLog.text_length))
    # 平均时延
    avg_latency_stmt = select(func.avg(UsageLog.latency_ms))
    # 成功率
    success_count_stmt = select(func.count(UsageLog.id)).where(UsageLog.status == "success")
    total_count_stmt = select(func.count(UsageLog.id))
    
    total_chars = (await session.execute(total_chars_stmt)).scalar() or 0
    avg_latency = (await session.execute(avg_latency_stmt)).scalar() or 0
    success_count = (await session.execute(success_count_stmt)).scalar() or 0
    total_count = (await session.execute(total_count_stmt)).scalar() or 0
    
    # 获取今日数据用于计算变化率 (模拟逻辑，实际应对比昨日)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count_stmt = select(func.count(UsageLog.id)).where(UsageLog.created_at >= today_start)
    today_count = (await session.execute(today_count_stmt)).scalar() or 0

    return {
        "stats": [
            {"name": "累计合成字数", "value": f"{total_chars/1000:.1f}k", "change": "+0%", "icon": "Database"},
            {"name": "平均推理时延", "value": f"{avg_latency/1000:.2f}s", "change": "-0%", "icon": "Clock"},
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
    获取最近 20 分钟的每分钟吞吐量 (Requests/min)
    """
    now = datetime.utcnow()
    minutes_to_show = 20
    start_time = now - timedelta(minutes=minutes_to_show)
    
    # 查询最近 20 分钟的所有成功记录
    stmt = select(UsageLog.created_at).where(
        UsageLog.created_at >= start_time,
        UsageLog.status == "success"
    ).order_by(UsageLog.created_at.asc())
    
    result = await session.execute(stmt)
    logs = result.scalars().all()
    
    # 按分钟统计
    counts = [0] * minutes_to_show
    for log in logs:
        # 计算该记录属于第几分钟 (0-19)
        delta = log - start_time
        idx = int(delta.total_seconds() // 60)
        if 0 <= idx < minutes_to_show:
            counts[idx] += 1
            
    return {
        "data": counts
    }
