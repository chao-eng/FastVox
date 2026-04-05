import time
import logging
from fastapi import Request, HTTPException, Depends
from config.settings import get_settings

logger = logging.getLogger("FastVox")
settings = get_settings()

class RateLimiter:
    """令牌桶算法 (简单内存版)"""
    def __init__(self, requests_per_minute: int = 30):
        self.rate = requests_per_minute
        self.bucket: Dict[str, Tuple[float, float]] = {} # ip -> (tokens, last_refill)

    async def check(self, request: Request):
        if not settings.rate_limit_per_minute:
            return
            
        ip = request.client.host
        now = time.time()
        
        # 获取或初始化桶
        tokens, last_refill = self.bucket.get(ip, (self.rate, now))
        
        # 补充令牌 (按秒补充)
        elapsed = now - last_refill
        refill_count = elapsed * (self.rate / 60.0)
        tokens = min(self.rate, tokens + refill_count)
        
        if tokens < 1:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            raise HTTPException(status_code=429, detail="Too Many Requests")
        
        # 扣减一个令牌
        self.bucket[ip] = (tokens - 1, now)

limiter = RateLimiter(settings.rate_limit_per_minute)

async def check_text_length(text: str):
    """文本长度校验"""
    if len(text) > settings.max_text_length:
        raise HTTPException(status_code=422, detail=f"Text exceeds limit of {settings.max_text_length} chars")
    return text
