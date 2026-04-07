import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """全局配置，支持环境变量覆盖 (FASTVOX_ 前缀)"""
    
    # 基础信息
    app_name: str = "FastVox"
    debug: bool = os.environ.get("DEBUG", "False").lower() == "true"
    host: str = "0.0.0.0"
    port: int = 8047
    
    # 推理参数 (ZipVoice Specific)
    model_dir: str = "./models/zipvoice"
    num_workers: int = 2
    intra_op_threads: int = 1
    zipvoice_num_steps: int = 4
    
    # 共享内存 (Ring Buffer)
    shm_name: str = "fastvox_shm_v8mb"
    slot_count: int = 5
    slot_size_mb: int = 8
    
    # 文本与限流
    max_text_length: int = 150
    rate_limit_per_minute: int = 30
    
    # 数据库 (使用 SQLite + aiosqlite)
    database_url: str = "sqlite+aiosqlite:///./data/fastvox.db"
    
    # 身份认证
    jwt_secret: str = "change-me-in-production"
    jwt_lifetime_seconds: int = 604800 # 7 天 (7 * 24 * 3600)
    
    # 微信登录适配
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    
    # 系统与平台
    uds_gateway_addr: str = "" # 留空由 platform_compat.platform.get_uds_path 生成
    
    model_config = SettingsConfigDict(
        env_prefix="FASTVOX_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=()
    )

@lru_cache()
def get_settings():
    return Settings()

# 全局实例初始化一些默认生成的属性
settings = get_settings()
if not settings.uds_gateway_addr:
    from app.core.platform_compat import platform
    settings.uds_gateway_addr = platform.get_uds_path("gateway")
